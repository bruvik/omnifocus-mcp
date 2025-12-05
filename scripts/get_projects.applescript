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
	tell application "OmniFocus"
		tell default document
			set projectList to every flattened project
			
			set jsonText to "{\"projects\":["
			repeat with i from 1 to count of projectList
				set p to item i of projectList
				
				set projectId to my json_escape(id of p as text)
				set projectName to my json_escape(name of p as text)
				
				set itemJson to "{\"id\":\"" & projectId & "\",\"name\":\"" & projectName & "\"}"
				
				if i is 1 then
					set jsonText to jsonText & itemJson
				else
					set jsonText to jsonText & "," & itemJson
				end if
			end repeat
			set jsonText to jsonText & "]}"
			
			return jsonText
		end tell
	end tell
end run
