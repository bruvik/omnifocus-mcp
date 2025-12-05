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
	if (count of argv) is 0 then
		return "{\"error\":\"Missing task title\"}"
	end if

	set taskTitle to item 1 of argv
	set targetProjectName to ""
	if (count of argv) is greater than 1 then
		set targetProjectName to item 2 of argv
	end if

	tell application "OmniFocus"
		tell default document
			set newTask to missing value

			if targetProjectName is not "" then
				try
					set targetProject to first project whose name is targetProjectName
					set newTask to make new task with properties {name:taskTitle} at end of tasks of targetProject
				on error
					set targetProjectName to ""
				end try
			end if

			if newTask is missing value then
				set newTask to make new inbox task with properties {name:taskTitle}
			end if

			set taskId to my json_escape(id of newTask as text)
			set taskTitleEscaped to my json_escape(name of newTask as text)
			set projectEscaped to my json_escape(targetProjectName)

			set noteText to ""
			try
				set noteText to note of newTask as text
			end try
			set noteEscaped to my json_escape(noteText)

			set dueDateStr to ""
			try
				set dueDateVal to due date of newTask
				if dueDateVal is not missing value then
					set dueDateStr to my json_escape(my iso_date_string(dueDateVal))
				end if
			end try

			if dueDateStr is "" then
				set dueJson to "\"\""
			else
				set dueJson to "\"" & dueDateStr & "\""
			end if

			set flaggedVal to flagged of newTask
			set completedVal to completed of newTask

			return "{\"name\":\"" & taskTitleEscaped & "\",\"id\":\"" & taskId & "\",\"project\":\"" & projectEscaped & "\",\"due\":" & dueJson & ",\"flagged\":" & (flaggedVal as string) & ",\"completed\":" & (completedVal as string) & ",\"note\":\"" & noteEscaped & "\"}"
		end tell
	end tell
end run
