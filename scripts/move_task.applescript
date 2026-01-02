-- Move a task to a different project or inbox in OmniFocus
-- Usage: osascript move_task.applescript <task_id> <target>
-- target: project name, project ID, or "inbox" to move to inbox

on run argv
	if (count of argv) < 2 then
		return "{\"error\":\"Usage: move_task <task_id> <target_project_or_inbox>\"}"
	end if

	set taskId to item 1 of argv
	set targetName to item 2 of argv

	tell application "OmniFocus"
		set jsCode to "
			const taskId = '" & taskId & "';
			const targetName = '" & targetName & "';

			try {
				// Find the task
				const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
				if (!task) {
					throw new Error('Task not found: ' + taskId);
				}

				let destination;
				let destinationName;

				if (targetName.toLowerCase() === 'inbox') {
					destination = inbox.ending;
					destinationName = 'inbox';
				} else {
					// Try to find project by name first, then by ID
					let project = flattenedProjects.find(p => p.name === targetName);
					if (!project) {
						project = flattenedProjects.find(p => p.id.primaryKey === targetName);
					}
					if (!project) {
						throw new Error('Project not found: ' + targetName);
					}
					destination = project.ending;
					destinationName = project.name;
				}

				// Move the task
				moveTasks([task], destination);

				JSON.stringify({
					status: 'ok',
					action: 'move',
					id: task.id.primaryKey,
					name: task.name,
					destination: destinationName
				});
			} catch (e) {
				JSON.stringify({error: e.message});
			}
		"
		return evaluate javascript jsCode
	end tell
end run
