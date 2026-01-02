-- OmniFocus Task Listing Script using Omni Automation
-- Uses evaluate javascript for better performance and accurate status filtering

on run argv
	set filterKey to ""
	if (count of argv) is greater than 0 then
		set filterKey to item 1 of argv
	end if

	tell application "OmniFocus"
		if filterKey is "flagged" then
			return my listFlaggedTasks()
		else if filterKey is "due_soon" then
			return my listDueSoonTasks()
		else if filterKey is "inbox" then
			return my listInboxTasks()
		else if filterKey is "completed" then
			return my listCompletedTasks()
		else if filterKey is "deferred" then
			return my listDeferredTasks()
		else if filterKey is "all" then
			return my listAllTasks()
		else
			return my listAvailableTasks()
		end if
	end tell
end run

on listFlaggedTasks()
	tell application "OmniFocus"
		set jsCode to "
			const availableStatuses = [Task.Status.Available, Task.Status.Next, Task.Status.DueSoon, Task.Status.Overdue];
			const flaggedParents = flattenedTasks.filter(t => t.flagged);
			const result = new Set();

			for (const parent of flaggedParents) {
				if (availableStatuses.includes(parent.taskStatus)) {
					result.add(parent.id.primaryKey);
				}
				for (const child of parent.flattenedTasks) {
					if (availableStatuses.includes(child.taskStatus)) {
						result.add(child.id.primaryKey);
					}
				}
			}

			const taskMap = new Map(flattenedTasks.map(t => [t.id.primaryKey, t]));
			const tasks = Array.from(result).map(id => {
				const t = taskMap.get(id);
				return formatTask(t);
			});

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listFlaggedTasks

on listDueSoonTasks()
	tell application "OmniFocus"
		set jsCode to "
			const tasks = flattenedTasks.filter(t =>
				t.taskStatus === Task.Status.DueSoon || t.taskStatus === Task.Status.Overdue
			).map(t => formatTask(t));

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listDueSoonTasks

on listInboxTasks()
	tell application "OmniFocus"
		set jsCode to "
			const tasks = inbox.filter(t =>
				t.taskStatus !== Task.Status.Completed && t.taskStatus !== Task.Status.Dropped
			).map(t => formatTask(t));

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listInboxTasks

on listCompletedTasks()
	tell application "OmniFocus"
		set jsCode to "
			const tasks = flattenedTasks.filter(t =>
				t.taskStatus === Task.Status.Completed
			).slice(0, 100).map(t => formatTask(t, true));

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listCompletedTasks

on listDeferredTasks()
	tell application "OmniFocus"
		set jsCode to "
			const tasks = flattenedTasks.filter(t =>
				t.taskStatus === Task.Status.Blocked && t.deferDate && t.deferDate > new Date()
			).map(t => formatTask(t));

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listDeferredTasks

on listAllTasks()
	tell application "OmniFocus"
		set jsCode to "
			const tasks = flattenedTasks.filter(t =>
				t.taskStatus !== Task.Status.Completed && t.taskStatus !== Task.Status.Dropped
			).map(t => formatTask(t));

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listAllTasks

on listAvailableTasks()
	tell application "OmniFocus"
		set jsCode to "
			const availableStatuses = [Task.Status.Available, Task.Status.Next, Task.Status.DueSoon, Task.Status.Overdue];
			const tasks = flattenedTasks.filter(t =>
				availableStatuses.includes(t.taskStatus)
			).map(t => formatTask(t));

			" & my formatTaskFunction() & "

			JSON.stringify({tasks: tasks})
		"
		return evaluate javascript jsCode
	end tell
end listAvailableTasks

on formatTaskFunction()
	return "
			function formatTask(t, isCompleted) {
				// Parse repetition rule if present
				let repetition = null;
				if (t.repetitionRule) {
					const ruleStr = String(t.repetitionRule);
					// Extract the RRULE part (e.g., 'FREQ=WEEKLY;BYDAY=MO')
					const match = ruleStr.match(/\\[object Task\\.RepetitionRule: ([^\\]]+)/);
					if (match) {
						const parts = match[1].split(' ');
						repetition = {
							rule: parts[0],  // e.g., 'FREQ=WEEKLY;BYDAY=MO'
							method: parts[1] || 'DueDate'  // e.g., 'DueDate' or 'DeferUntilDate'
						};
					}
				}

				return {
					id: t.id.primaryKey,
					name: t.name,
					project: t.containingProject ? t.containingProject.name : '',
					due: t.dueDate ? t.dueDate.toISOString().slice(0, 19) : '',
					defer: t.deferDate ? t.deferDate.toISOString().slice(0, 19) : '',
					flagged: t.flagged,
					completed: isCompleted || false,
					note: t.note || '',
					repetition: repetition
				};
			}
	"
end formatTaskFunction
