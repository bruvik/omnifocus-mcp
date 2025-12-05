on run argv
	if (count of argv) is 0 then
		return "Missing task name"
	end if

	set taskName to item 1 of argv
	set taskNote to ""
	if (count of argv) is greater than 1 then
		set taskNote to item 2 of argv
	end if

	tell application "OmniFocus"
		tell default document
			set newTask to make new inbox task with properties {name:taskName, note:taskNote}
			return id of newTask
		end tell
	end tell
end run
