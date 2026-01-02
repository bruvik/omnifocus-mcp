-- Manage tags on a task in OmniFocus
-- Usage: osascript manage_tags.applescript <task_id> <action> [tag_names_json]
-- Actions: get, add, remove, set
-- tag_names_json: JSON array of tag names/paths, e.g. '["Work", "Folk : Asbjørn"]'

on run argv
	if (count of argv) < 2 then
		return "{\"error\":\"Usage: manage_tags <task_id> <action> [tag_names_json]\"}"
	end if

	set taskId to item 1 of argv
	set actionName to item 2 of argv
	set tagNamesJson to "[]"
	if (count of argv) > 2 then
		set tagNamesJson to item 3 of argv
	end if

	tell application "OmniFocus"
		set jsCode to "
			const taskId = '" & taskId & "';
			const action = '" & actionName & "';
			const tagNames = " & tagNamesJson & ";

			// Helper to get tag path
			function getTagPath(tag) {
				if (!tag.parent) return tag.name;
				return getTagPath(tag.parent) + ' : ' + tag.name;
			}

			// Find tag by name, path, or ID
			function findTag(identifier) {
				// Try exact path match first
				let tag = flattenedTags.find(t => getTagPath(t) === identifier);
				if (tag) return tag;

				// Try name match (returns first match if multiple)
				tag = flattenedTags.find(t => t.name === identifier);
				if (tag) return tag;

				// Try ID match
				tag = flattenedTags.find(t => t.id.primaryKey === identifier);
				return tag;
			}

			try {
				// Find the task
				const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
				if (!task) {
					throw new Error('Task not found: ' + taskId);
				}

				if (action === 'get') {
					// Return current tags
					const tags = task.tags.map(t => ({
						id: t.id.primaryKey,
						name: t.name,
						path: getTagPath(t)
					}));
					JSON.stringify({
						status: 'ok',
						task: {id: task.id.primaryKey, name: task.name},
						tags: tags
					});

				} else if (action === 'add') {
					// Add tags (don't remove existing)
					const added = [];
					const notFound = [];
					for (const name of tagNames) {
						const tag = findTag(name);
						if (tag) {
							if (!task.tags.includes(tag)) {
								task.addTag(tag);
								added.push({name: tag.name, path: getTagPath(tag)});
							}
						} else {
							notFound.push(name);
						}
					}
					const result = {
						status: 'ok',
						action: 'add',
						task: {id: task.id.primaryKey, name: task.name},
						added: added,
						currentTags: task.tags.map(t => getTagPath(t))
					};
					if (notFound.length > 0) {
						result.notFound = notFound;
					}
					JSON.stringify(result);

				} else if (action === 'remove') {
					// Remove specified tags
					const removed = [];
					const notFound = [];
					for (const name of tagNames) {
						const tag = findTag(name);
						if (tag) {
							if (task.tags.includes(tag)) {
								task.removeTag(tag);
								removed.push({name: tag.name, path: getTagPath(tag)});
							}
						} else {
							notFound.push(name);
						}
					}
					const result = {
						status: 'ok',
						action: 'remove',
						task: {id: task.id.primaryKey, name: task.name},
						removed: removed,
						currentTags: task.tags.map(t => getTagPath(t))
					};
					if (notFound.length > 0) {
						result.notFound = notFound;
					}
					JSON.stringify(result);

				} else if (action === 'set') {
					// Replace all tags with specified ones
					// First remove all existing tags
					while (task.tags.length > 0) {
						task.removeTag(task.tags[0]);
					}
					// Then add new tags
					const added = [];
					const notFound = [];
					for (const name of tagNames) {
						const tag = findTag(name);
						if (tag) {
							task.addTag(tag);
							added.push({name: tag.name, path: getTagPath(tag)});
						} else {
							notFound.push(name);
						}
					}
					const result = {
						status: 'ok',
						action: 'set',
						task: {id: task.id.primaryKey, name: task.name},
						tags: added
					};
					if (notFound.length > 0) {
						result.notFound = notFound;
					}
					JSON.stringify(result);

				} else {
					throw new Error('Unknown action: ' + action + '. Valid: get, add, remove, set');
				}

			} catch (e) {
				JSON.stringify({error: e.message});
			}
		"
		return evaluate javascript jsCode
	end tell
end run
