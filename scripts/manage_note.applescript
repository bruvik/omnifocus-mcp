-- Manage notes on a task in OmniFocus
-- Usage: osascript manage_note.applescript <task_id> <action> [note_text]
-- Actions: get, set, clear, append

on run argv
	if (count of argv) < 2 then
		return "{\"error\":\"Usage: manage_note <task_id> <action> [note_text]\"}"
	end if

	set taskId to item 1 of argv
	set actionName to item 2 of argv
	set noteText to ""
	if (count of argv) > 2 then
		set noteText to item 3 of argv
	end if

	tell application "OmniFocus"
		-- Use Omni Automation for better Unicode/special character handling
		set jsCode to "
			const taskId = '" & taskId & "';
			const action = '" & actionName & "';

			try {
				const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
				if (!task) {
					throw new Error('Task not found: ' + taskId);
				}

				if (action === 'get') {
					JSON.stringify({
						status: 'ok',
						task: {id: task.id.primaryKey, name: task.name},
						note: task.note || ''
					});
				} else if (action === 'clear') {
					task.note = '';
					JSON.stringify({
						status: 'ok',
						action: 'clear',
						task: {id: task.id.primaryKey, name: task.name}
					});
				} else {
					throw new Error('Unknown action: ' + action + '. Valid: get, clear (use set/append via stdin)');
				}
			} catch (e) {
				JSON.stringify({error: e.message});
			}
		"

		if actionName is "get" or actionName is "clear" then
			return evaluate javascript jsCode
		else if actionName is "set" then
			-- For set, we pass the note text directly
			set jsSetCode to "
				const taskId = '" & taskId & "';
				try {
					const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
					if (!task) {
						throw new Error('Task not found: ' + taskId);
					}
					task.note = " & my escapeForJS(noteText) & ";
					JSON.stringify({
						status: 'ok',
						action: 'set',
						task: {id: task.id.primaryKey, name: task.name},
						note: task.note
					});
				} catch (e) {
					JSON.stringify({error: e.message});
				}
			"
			return evaluate javascript jsSetCode
		else if actionName is "append" then
			-- For append, we add to existing note
			set jsAppendCode to "
				const taskId = '" & taskId & "';
				try {
					const task = flattenedTasks.find(t => t.id.primaryKey === taskId);
					if (!task) {
						throw new Error('Task not found: ' + taskId);
					}
					const newText = " & my escapeForJS(noteText) & ";
					if (task.note && task.note.length > 0) {
						task.note = task.note + '\\n' + newText;
					} else {
						task.note = newText;
					}
					JSON.stringify({
						status: 'ok',
						action: 'append',
						task: {id: task.id.primaryKey, name: task.name},
						note: task.note
					});
				} catch (e) {
					JSON.stringify({error: e.message});
				}
			"
			return evaluate javascript jsAppendCode
		else
			return "{\"error\":\"Unknown action: " & actionName & ". Valid: get, set, append, clear\"}"
		end if
	end tell
end run

on escapeForJS(theText)
	-- Escape text for JavaScript string literal
	set theText to my replaceText("\\", "\\\\", theText)
	set theText to my replaceText("\"", "\\\"", theText)
	set theText to my replaceText(return, "\\n", theText)
	set theText to my replaceText(linefeed, "\\n", theText)
	set theText to my replaceText(tab, "\\t", theText)
	return "\"" & theText & "\""
end escapeForJS

on replaceText(find, replace, subject)
	set AppleScript's text item delimiters to find
	set parts to text items of subject
	set AppleScript's text item delimiters to replace
	set subject to parts as text
	set AppleScript's text item delimiters to ""
	return subject
end replaceText
