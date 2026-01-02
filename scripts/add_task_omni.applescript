-- Add task to OmniFocus with full options using Omni Automation
-- Usage: osascript add_task_omni.applescript '<json>'
-- JSON format: {"title": "Task name", "project": "Project name", "due": "2025-01-15T17:00:00", "defer": "2025-01-10T09:00:00", "flagged": true, "note": "...", "rrule": "FREQ=WEEKLY", "repeat_method": "due"}

on run argv
	if (count of argv) is 0 then
		return "{\"error\":\"Missing JSON argument\"}"
	end if

	set jsonArg to item 1 of argv

	tell application "OmniFocus"
		set jsCode to "
			const input = " & jsonArg & ";

			try {
				// Validate required fields
				if (!input.title || input.title.trim() === '') {
					throw new Error('Task title is required');
				}

				// Find project if specified
				let project = null;
				if (input.project && input.project.trim() !== '') {
					project = flattenedProjects.find(p => p.name === input.project);
					if (!project) {
						throw new Error('Project not found: ' + input.project);
					}
				}

				// Create the task
				let task;
				if (project) {
					task = new Task(input.title, project.ending);
				} else {
					task = new Task(input.title, inbox.ending);
				}

				// Set optional properties
				if (input.due) {
					task.dueDate = new Date(input.due);
				}

				if (input.defer) {
					task.deferDate = new Date(input.defer);
				}

				if (input.flagged !== undefined) {
					task.flagged = !!input.flagged;
				}

				if (input.note) {
					task.note = input.note;
				}

				// Set repetition if specified
				if (input.rrule && input.rrule.trim() !== '') {
					let repMethod;
					switch ((input.repeat_method || 'due').toLowerCase()) {
						case 'defer':
							repMethod = Task.RepetitionMethod.DeferUntilDate;
							break;
						case 'fixed':
							repMethod = Task.RepetitionMethod.Fixed;
							break;
						case 'due':
						default:
							repMethod = Task.RepetitionMethod.DueDate;
							break;
					}
					task.repetitionRule = new Task.RepetitionRule(input.rrule, repMethod);
				}

				// Build response
				let repetition = null;
				if (task.repetitionRule) {
					const ruleStr = String(task.repetitionRule);
					const match = ruleStr.match(/\\[object Task\\.RepetitionRule: ([^\\]]+)/);
					if (match) {
						const parts = match[1].split(' ');
						repetition = {
							rule: parts[0],
							method: parts[1] || 'DueDate'
						};
					}
				}

				JSON.stringify({
					status: 'ok',
					task: {
						id: task.id.primaryKey,
						name: task.name,
						project: task.containingProject ? task.containingProject.name : '',
						due: task.dueDate ? task.dueDate.toISOString().slice(0, 19) : '',
						defer: task.deferDate ? task.deferDate.toISOString().slice(0, 19) : '',
						flagged: task.flagged,
						completed: false,
						note: task.note || '',
						repetition: repetition
					}
				});
			} catch (e) {
				JSON.stringify({error: e.message});
			}
		"
		return evaluate javascript jsCode
	end tell
end run
