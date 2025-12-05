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

on run argv
	if (count of argv) is 0 then
		return "{\"error\":\"Missing task ID\"}"
	end if

	set targetId to item 1 of argv
	tell application "OmniFocus"
		tell default document
			try
				set targetTask to first flattened task whose id is targetId
				set completed of targetTask to true

				set taskId to my json_escape(id of targetTask as text)
				set taskName to my json_escape(name of targetTask as text)

				return "{\"status\":\"ok\",\"id\":\"" & taskId & "\",\"name\":\"" & taskName & "\"}"
			on error errMsg
				set errEscaped to my json_escape(errMsg)
				return "{\"error\":\"" & errEscaped & "\"}"
			end try
		end tell
	end tell
end run
