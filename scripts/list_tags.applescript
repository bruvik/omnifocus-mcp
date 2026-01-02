-- List all tags from OmniFocus
-- Returns hierarchical tag information

on run argv
	tell application "OmniFocus"
		set jsCode to "
			function getTagPath(tag) {
				if (!tag.parent) return tag.name;
				return getTagPath(tag.parent) + ' : ' + tag.name;
			}

			const tags = flattenedTags.map(t => ({
				id: t.id.primaryKey,
				name: t.name,
				path: getTagPath(t),
				parent: t.parent ? t.parent.name : null,
				available: t.availableTaskCount,
				remaining: t.remainingTaskCount
			}));

			JSON.stringify({tags: tags});
		"
		return evaluate javascript jsCode
	end tell
end run
