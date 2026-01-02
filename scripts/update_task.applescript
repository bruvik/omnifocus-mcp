-- Update task properties in OmniFocus
-- Usage: osascript update_task.applescript <task_id> <action> [value]
-- Actions: drop, pause, resume, flag, unflag, defer, due, clear_defer, clear_due

on json_escape(theText)
	set theText to my replaceText("\\", "\\\\", theText)
	set theText to my replaceText("\"", "\\\"", theText)
	set theText to my replaceText(linefeed, "\\n", theText)
	set theText to my replaceText(return, "\\n", theText)
	return theText
end json_escape

on replaceText(find, replace, subject)
	set AppleScript's text item delimiters to find
	set parts to text items of subject
	set AppleScript's text item delimiters to replace
	set subject to parts as text
	set AppleScript's text item delimiters to ""
	return subject
end replaceText

on parseISODate(isoString)
	-- Parse ISO 8601 date string: YYYY-MM-DDTHH:MM:SS or YYYY-MM-DD
	set oldDelims to AppleScript's text item delimiters

	-- Split date and time
	set AppleScript's text item delimiters to "T"
	set parts to text items of isoString
	set datePart to item 1 of parts
	set timePart to ""
	if (count of parts) > 1 then
		set timePart to item 2 of parts
	end if

	-- Parse date
	set AppleScript's text item delimiters to "-"
	set dateParts to text items of datePart
	set theYear to item 1 of dateParts as integer
	set theMonth to item 2 of dateParts as integer
	set theDay to item 3 of dateParts as integer

	-- Parse time (default to midnight)
	set theHours to 0
	set theMinutes to 0
	set theSeconds to 0
	if timePart is not "" then
		set AppleScript's text item delimiters to ":"
		set timeParts to text items of timePart
		set theHours to item 1 of timeParts as integer
		if (count of timeParts) > 1 then
			set theMinutes to item 2 of timeParts as integer
		end if
		if (count of timeParts) > 2 then
			-- Handle seconds (may have timezone suffix)
			set secPart to item 3 of timeParts
			set AppleScript's text item delimiters to {"Z", "+", "-"}
			set secPart to first text item of secPart
			set theSeconds to secPart as integer
		end if
	end if

	set AppleScript's text item delimiters to oldDelims

	-- Create date object
	set theDate to current date
	set year of theDate to theYear
	set month of theDate to theMonth
	set day of theDate to theDay
	set hours of theDate to theHours
	set minutes of theDate to theMinutes
	set seconds of theDate to theSeconds

	return theDate
end parseISODate

on run argv
	if (count of argv) < 2 then
		return "{\"error\":\"Usage: update_task <task_id> <action> [value]\"}"
	end if

	set targetId to item 1 of argv
	set actionName to item 2 of argv
	set actionValue to ""
	if (count of argv) > 2 then
		set actionValue to item 3 of argv
	end if

	tell application "OmniFocus"
		tell default document
			try
				set targetTask to first flattened task whose id is targetId

				-- Get task info before any destructive action
				set taskId to my json_escape(id of targetTask as text)
				set taskName to my json_escape(name of targetTask as text)

				-- Perform the action
				if actionName is "drop" then
					-- Drop only works on projects, not individual tasks
					try
						set containingProj to containing project of targetTask
						if containingProj is not missing value then
							-- It's a task within a project - dropping not supported
							return "{\"error\":\"Cannot drop a task. Use 'delete' to remove the task, or 'complete' to mark it done.\"}"
						else
							-- Check if it's in the inbox
							try
								if (in inbox of targetTask) is true then
									return "{\"error\":\"Cannot drop an inbox item. Use 'delete' to remove it, or 'complete' to mark it done.\"}"
								end if
							end try
							-- It might be a project root task - try setting dropped
							set dropped of targetTask to true
						end if
					on error errMsg
						return "{\"error\":\"Cannot drop this item: \" & errMsg & \". Use 'delete' for tasks.\"}"
					end try

				else if actionName is "delete" then
					-- Delete the task permanently
					delete targetTask
					return "{\"status\":\"ok\",\"action\":\"delete\",\"id\":\"" & taskId & "\",\"name\":\"" & taskName & "\"}"

				else if actionName is "pause" then
					-- Pause = put project on hold (only works for project tasks)
					try
						set containingProj to containing project of targetTask
						if containingProj is not missing value then
							set status of containingProj to on hold status
						else
							return "{\"error\":\"Task is not in a project, cannot pause\"}"
						end if
					on error
						return "{\"error\":\"Cannot pause - task may not be a project\"}"
					end try

				else if actionName is "resume" then
					-- Resume = set project to active
					try
						set containingProj to containing project of targetTask
						if containingProj is not missing value then
							set status of containingProj to active status
						else
							return "{\"error\":\"Task is not in a project, cannot resume\"}"
						end if
					on error
						return "{\"error\":\"Cannot resume - task may not be a project\"}"
					end try

				else if actionName is "flag" then
					set flagged of targetTask to true

				else if actionName is "unflag" then
					set flagged of targetTask to false

				else if actionName is "defer" then
					if actionValue is "" then
						return "{\"error\":\"defer action requires a date value (ISO 8601)\"}"
					end if
					set defer date of targetTask to my parseISODate(actionValue)

				else if actionName is "due" then
					if actionValue is "" then
						return "{\"error\":\"due action requires a date value (ISO 8601)\"}"
					end if
					set due date of targetTask to my parseISODate(actionValue)

				else if actionName is "clear_defer" then
					set defer date of targetTask to missing value

				else if actionName is "clear_due" then
					set due date of targetTask to missing value

				else if actionName is "rename" then
					if actionValue is "" then
						return "{\"error\":\"rename action requires a new name value\"}"
					end if
					set name of targetTask to actionValue
					-- Update taskName for the response
					set taskName to my json_escape(actionValue)

				else
					return "{\"error\":\"Unknown action: " & actionName & ". Valid: drop, delete, pause, resume, flag, unflag, defer, due, clear_defer, clear_due, rename\"}"
				end if

				-- Return success with task info (taskId and taskName captured at start, or updated for rename)
				return "{\"status\":\"ok\",\"action\":\"" & actionName & "\",\"id\":\"" & taskId & "\",\"name\":\"" & taskName & "\"}"

			on error errMsg
				set errEscaped to my json_escape(errMsg)
				return "{\"error\":\"" & errEscaped & "\"}"
			end try
		end tell
	end tell
end run
