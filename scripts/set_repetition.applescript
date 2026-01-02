-- Set repetition rule for a task in OmniFocus
-- Usage: osascript set_repetition.applescript <task_id> <rrule> <method>
-- rrule: RRULE string (e.g., "FREQ=WEEKLY", "FREQ=MONTHLY;BYMONTHDAY=1") or "none" to clear
-- method: "due", "defer", or "fixed" (default: "due")

on run argv
	if (count of argv) < 2 then
		return "{\"error\":\"Usage: set_repetition <task_id> <rrule> [method]\"}"
	end if

	set taskId to item 1 of argv
	set rrule to item 2 of argv
	set repMethod to "due"
	if (count of argv) > 2 then
		set repMethod to item 3 of argv
	end if

	tell application "OmniFocus"
		-- Use Omni Automation to set repetition
		set jsCode to "
			const taskId = '" & taskId & "';
			const rrule = '" & rrule & "';
			const method = '" & repMethod & "';

			// Find the task
			const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
			if (!task) {
				JSON.stringify({error: 'Task not found: ' + taskId});
			} else {
				try {
					if (rrule === 'none' || rrule === '') {
						// Clear repetition
						task.repetitionRule = null;
						JSON.stringify({
							status: 'ok',
							action: 'clear_repetition',
							id: task.id.primaryKey,
							name: task.name
						});
					} else {
						// Determine repetition method
						let repMethodEnum;
						switch (method.toLowerCase()) {
							case 'defer':
								repMethodEnum = Task.RepetitionMethod.DeferUntilDate;
								break;
							case 'fixed':
								repMethodEnum = Task.RepetitionMethod.Fixed;
								break;
							case 'due':
							default:
								repMethodEnum = Task.RepetitionMethod.DueDate;
								break;
						}

						// Create and set the repetition rule
						const rule = new Task.RepetitionRule(rrule, repMethodEnum);
						task.repetitionRule = rule;

						JSON.stringify({
							status: 'ok',
							action: 'set_repetition',
							id: task.id.primaryKey,
							name: task.name,
							repetition: {
								rule: rrule,
								method: method
							}
						});
					}
				} catch (e) {
					JSON.stringify({error: 'Failed to set repetition: ' + e.message});
				}
			}
		"
		return evaluate javascript jsCode
	end tell
end run
