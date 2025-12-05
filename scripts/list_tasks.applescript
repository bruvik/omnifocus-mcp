on run argv
	tell application "OmniFocus"
		tell default document
			set taskList to every inbox task
			set output to {}
			repeat with t in taskList
				set end of output to (id of t & tab & name of t & tab & (completed of t as string))
			end repeat
			set AppleScript's text item delimiters to linefeed
			return output as text
		end tell
	end tell
end run
