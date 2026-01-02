-- Complete a task in OmniFocus using Omni Automation
-- Usage: osascript complete_task.applescript <task_id>

on run argv
	if (count of argv) is 0 then
		return "{\"error\":\"Missing task ID\"}"
	end if

	set targetId to item 1 of argv

	tell application "OmniFocus"
		set jsCode to "
			const taskId = '" & targetId & "';

			try {
				const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
				if (!task) {
					throw new Error('Task not found: ' + taskId);
				}

				// Use markComplete() which works for all task types including inbox
				task.markComplete();

				JSON.stringify({
					status: 'ok',
					id: task.id.primaryKey,
					name: task.name
				});
			} catch (e) {
				JSON.stringify({error: e.message});
			}
		"
		return evaluate javascript jsCode
	end tell
end run
