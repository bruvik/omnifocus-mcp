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

				set includeTask to true

				set projectName to ""
				try
					set projectName to name of containing project of t as text
				end try
				set projectEscaped to my json_escape(projectName)

				set noteText to ""
				try
					set noteText to note of t as text
				end try
				set noteEscaped to my json_escape(noteText)

				set dueDateStr to ""
				set dueDateVal to missing value
				try
					set dueDateVal to due date of t
					if dueDateVal is not missing value then
						set dueDateStr to my json_escape(my iso_date_string(dueDateVal))
					end if
				end try

				if filterKey is "flagged" then
					if taskFlagged is false then set includeTask to false
				else if filterKey is "due_soon" then
					set includeTask to false
					if dueDateVal is not missing value then
						if dueDateVal is less than or equal to soonThreshold then set includeTask to true
					end if
				else if filterKey is "inbox" then
					set includeTask to false
					try
						if (in inbox of t) is true then set includeTask to true
					end try
				end if

				if includeTask is false then
					-- skip task not matching filter
				else
					if dueDateStr is "" then
						set dueJson to "\"\""
					else
						set dueJson to "\"" & dueDateStr & "\""
					end if

					set itemJson to "{\"name\":\"" & taskName & "\",\"id\":\"" & taskId & "\",\"project\":\"" & projectEscaped & "\",\"due\":" & dueJson & ",\"flagged\":" & (taskFlagged as string) & ",\"completed\":" & (taskCompleted as string) & ",\"note\":\"" & noteEscaped & "\"}"

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
