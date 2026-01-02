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

on zero_pad(num)
	if num is less than 10 then
		return "0" & num
	else
		return num as text
	end if
end zero_pad

on iso_date_string(d)
	set y to year of d as text
	set m to my zero_pad(month of d as integer)
	set dd to my zero_pad(day of d)
	set hh to my zero_pad(hours of d)
	set mm to my zero_pad(minutes of d)
	set ss to my zero_pad(seconds of d as integer)
	return y & "-" & m & "-" & dd & "T" & hh & ":" & mm & ":" & ss
end iso_date_string

on run argv
	set filterKey to ""
	if (count of argv) is greater than 0 then
		set filterKey to item 1 of argv
	end if

	set soonThreshold to (current date) + (1 * days)
	set nowDate to current date

	tell application "OmniFocus"
		tell default document
			set taskList to every flattened task

			set jsonText to "{\"tasks\":["
			set isFirst to true
			repeat with i from 1 to count of taskList
				set t to item i of taskList

				set taskId to my json_escape(id of t as text)
				set taskName to my json_escape(name of t as text)
				set taskCompleted to (completed of t)
				set taskFlagged to (flagged of t)

				-- Check if effectively flagged (task or any ancestor is flagged)
				set isEffectivelyFlagged to taskFlagged
				if not isEffectivelyFlagged then
					try
						set currentTask to t
						repeat
							set pTask to parent task of currentTask
							if pTask is missing value then exit repeat
							if flagged of pTask then
								set isEffectivelyFlagged to true
								exit repeat
							end if
							set currentTask to pTask
						end repeat
					end try
				end if

				-- Check if effectively completed (includes "completed with container")
				set isEffectivelyCompleted to false
				try
					set isEffectivelyCompleted to (effectively completed of t)
				on error
					set isEffectivelyCompleted to taskCompleted
				end try

				-- Check if task itself is dropped (independent of project)
				set taskDropped to false
				try
					set taskDropped to (dropped of t)
				end try

				-- Get project name and status
				set projectName to ""
				set projectStatus to "active"
				try
					set containingProj to containing project of t
					if containingProj is not missing value then
						set projectName to name of containingProj as text
						set projStatus to status of containingProj
						if projStatus is on hold status then
							set projectStatus to "on_hold"
						else if projStatus is dropped status then
							set projectStatus to "dropped"
						else
							set projectStatus to "active"
						end if
					end if
				end try
				set projectEscaped to my json_escape(projectName)

				set noteText to ""
				try
					set noteText to note of t as text
				end try
				set noteEscaped to my json_escape(noteText)

				-- Get due date
				set dueDateStr to ""
				set dueDateVal to missing value
				try
					set dueDateVal to due date of t
					if dueDateVal is not missing value then
						set dueDateStr to my json_escape(my iso_date_string(dueDateVal))
					end if
				end try

				-- Get defer date
				set deferDateStr to ""
				set deferDateVal to missing value
				try
					set deferDateVal to defer date of t
					if deferDateVal is not missing value then
						set deferDateStr to my json_escape(my iso_date_string(deferDateVal))
					end if
				end try

				-- Determine if task is "available" (not effectively completed, not dropped, not deferred, not in dropped/on-hold project)
				set isAvailable to true
				if isEffectivelyCompleted then set isAvailable to false
				if taskDropped then set isAvailable to false
				if projectStatus is "dropped" then set isAvailable to false
				if projectStatus is "on_hold" then set isAvailable to false
				if deferDateVal is not missing value then
					if deferDateVal is greater than nowDate then set isAvailable to false
				end if

				-- Determine if task is deferred (has future defer date, not effectively completed, not dropped)
				set isDeferred to false
				if isEffectivelyCompleted is false and taskDropped is false and projectStatus is not "dropped" then
					if deferDateVal is not missing value then
						if deferDateVal is greater than nowDate then set isDeferred to true
					end if
				end if

				-- Apply filter logic
				set includeTask to false

				if filterKey is "" then
					-- Default: only available tasks
					if isAvailable then set includeTask to true
				else if filterKey is "all" then
					-- All incomplete tasks (including deferred, excluding effectively completed and dropped)
					if isEffectivelyCompleted is false and taskDropped is false and projectStatus is not "dropped" then set includeTask to true
				else if filterKey is "completed" then
					-- Only effectively completed tasks
					if isEffectivelyCompleted then set includeTask to true
				else if filterKey is "deferred" then
					-- Only deferred tasks
					if isDeferred then set includeTask to true
				else if filterKey is "flagged" then
					-- Available + effectively flagged (includes inherited from parent)
					if isAvailable and isEffectivelyFlagged then set includeTask to true
				else if filterKey is "due_soon" then
					-- Available + due within 24 hours
					if isAvailable then
						if dueDateVal is not missing value then
							if dueDateVal is less than or equal to soonThreshold then set includeTask to true
						end if
					end if
				else if filterKey is "inbox" then
					-- Inbox items only
					try
						if (in inbox of t) is true then set includeTask to true
					end try
				end if

				if includeTask then
					if dueDateStr is "" then
						set dueJson to "\"\""
					else
						set dueJson to "\"" & dueDateStr & "\""
					end if

					if deferDateStr is "" then
						set deferJson to "\"\""
					else
						set deferJson to "\"" & deferDateStr & "\""
					end if

					set itemJson to "{\"name\":\"" & taskName & "\",\"id\":\"" & taskId & "\",\"project\":\"" & projectEscaped & "\",\"due\":" & dueJson & ",\"defer\":" & deferJson & ",\"flagged\":" & (taskFlagged as string) & ",\"completed\":" & (taskCompleted as string) & ",\"note\":\"" & noteEscaped & "\"}"

					if isFirst then
						set jsonText to jsonText & itemJson
						set isFirst to false
					else
						set jsonText to jsonText & "," & itemJson
					end if
				end if
			end repeat
			set jsonText to jsonText & "]}"

			return jsonText
		end tell
	end tell
end run
