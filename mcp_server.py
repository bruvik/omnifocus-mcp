"""
OmniFocus MCP Server

Exposes OmniFocus task management functionality to Claude Code and other
MCP-compatible AI assistants via the Model Context Protocol.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP

from utils.applescript import AppleScriptError, run_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

mcp = FastMCP(
    "OmniFocus",
    instructions="Manage OmniFocus tasks, projects, and inbox items on macOS",
)


FilterType = Literal["due_soon", "flagged", "inbox", "all", "completed", "deferred"] | None
RepetitionMethod = Literal["due", "defer", "fixed"] | None


@mcp.tool()
def list_tasks(filter: FilterType = None) -> dict:
    """
    List tasks from OmniFocus.

    Args:
        filter: Optional filter to apply:
            - (none): Available tasks only (not completed, not deferred, not in dropped/on-hold projects)
            - "all": All incomplete tasks including deferred (excludes completed and dropped)
            - "flagged": Available tasks that are flagged
            - "due_soon": Available tasks due within 24 hours
            - "inbox": Only inbox items
            - "completed": Only completed tasks
            - "deferred": Only deferred tasks (future defer date)

    Returns:
        Dictionary with "tasks" key containing list of task objects.
        Each task has: id, name, project, due, defer, flagged, completed, note
    """
    # Use Omni Automation script for better performance
    script_path = SCRIPTS_DIR / "list_tasks_omni.applescript"
    logger.info("list_tasks called with filter=%s", filter)

    valid_filters = ("due_soon", "flagged", "inbox", "all", "completed", "deferred")
    args: list[str] = []
    if filter:
        if filter not in valid_filters:
            return {"error": f"Invalid filter: {filter}. Use: {', '.join(valid_filters)}"}
        args.append(filter)

    try:
        output = run_script(script_path, *args)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from list_tasks")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in list_tasks")
        return {"error": str(exc)}


@mcp.tool()
def summarize_tasks(filter: FilterType = None) -> dict:
    """
    Get a summary of tasks grouped by project.

    Args:
        filter: Optional filter (same as list_tasks)

    Returns:
        Dictionary with "projects" key containing list of project summaries.
        Each summary has: project, active, flagged, due_today, overdue counts
    """
    logger.info("summarize_tasks called with filter=%s", filter)

    tasks_result = list_tasks(filter)
    if "error" in tasks_result:
        return tasks_result

    tasks_data = tasks_result.get("tasks", [])
    now = datetime.now(timezone.utc)
    today_date = now.date()

    def parse_due(due_str: str) -> datetime | None:
        if not due_str:
            return None
        try:
            return datetime.fromisoformat(due_str)
        except ValueError:
            return None

    summary: dict[str, dict] = {}

    for task in tasks_data:
        project = task.get("project", "") or ""
        if project not in summary:
            summary[project] = {
                "project": project,
                "active": 0,
                "flagged": 0,
                "due_today": 0,
                "overdue": 0,
            }

        entry = summary[project]

        if not task.get("completed", False):
            entry["active"] += 1

        if task.get("flagged", False):
            entry["flagged"] += 1

        due_str = task.get("due", "")
        due_dt = parse_due(due_str)
        if due_dt:
            if due_dt.date() == today_date:
                entry["due_today"] += 1
            if due_dt < now:
                entry["overdue"] += 1

    return {"projects": list(summary.values())}


@mcp.tool()
def add_task(
    title: str,
    project: str | None = None,
    due: str | None = None,
    defer: str | None = None,
    flagged: bool = False,
    note: str | None = None,
    rrule: str | None = None,
    repeat_method: RepetitionMethod = None,
) -> dict:
    """
    Add a new task to OmniFocus.

    Args:
        title: The task title/name (required)
        project: Optional project name to add the task to
        due: Optional due date in ISO 8601 format (e.g., "2025-01-15" or "2025-01-15T17:00:00")
        defer: Optional defer date in ISO 8601 format
        flagged: Whether to flag the task (default: False)
        note: Optional note text for the task
        rrule: Optional iCalendar RRULE string for repetition. Examples:
               - "FREQ=DAILY" - repeats every day
               - "FREQ=WEEKLY" - repeats every week
               - "FREQ=WEEKLY;BYDAY=MO,WE,FR" - repeats Mon, Wed, Fri
               - "FREQ=MONTHLY;BYMONTHDAY=1" - repeats 1st of each month
        repeat_method: How to calculate next occurrence (if rrule set):
               - "due": Based on due date (default)
               - "defer": Based on defer date
               - "fixed": Fixed schedule

    Returns:
        Dictionary with status and the created task details
    """
    if not title or not title.strip():
        return {"error": "Task title is required"}

    script_path = SCRIPTS_DIR / "add_task_omni.applescript"
    logger.info("add_task called: title=%r project=%r due=%r defer=%r", title, project, due, defer)

    # Build JSON input
    task_data = {"title": title}
    if project:
        task_data["project"] = project
    if due:
        task_data["due"] = due
    if defer:
        task_data["defer"] = defer
    if flagged:
        task_data["flagged"] = flagged
    if note:
        task_data["note"] = note
    if rrule:
        task_data["rrule"] = rrule
        if repeat_method:
            task_data["repeat_method"] = repeat_method

    try:
        output = run_script(script_path, json.dumps(task_data))
        logger.info("add_task output: %s", output)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from add_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in add_task")
        return {"error": str(exc)}


@mcp.tool()
def get_projects() -> dict:
    """
    List all projects in OmniFocus.

    Returns:
        Dictionary with "projects" key containing list of project objects.
        Each project has: id, name, status
    """
    script_path = SCRIPTS_DIR / "get_projects.applescript"
    logger.info("get_projects called")

    try:
        output = run_script(script_path)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from get_projects")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in get_projects")
        return {"error": str(exc)}


@mcp.tool()
def complete_task(task_id: str) -> dict:
    """
    Mark a task as completed in OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "complete_task.applescript"
    logger.info("complete_task called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from complete_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in complete_task")
        return {"error": str(exc)}


@mcp.tool()
def rename_task(task_id: str, new_name: str) -> dict:
    """
    Rename a task in OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        new_name: The new name for the task

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}
    if not new_name or not new_name.strip():
        return {"error": "new_name is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("rename_task called: task_id=%r new_name=%r", task_id, new_name)

    try:
        output = run_script(script_path, task_id, "rename", new_name)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from rename_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in rename_task")
        return {"error": str(exc)}


@mcp.tool()
def move_task(task_id: str, destination: str) -> dict:
    """
    Move a task to a different project or to the inbox.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        destination: Target location - either a project name, project ID, or "inbox"

    Returns:
        Dictionary with status of the operation including the destination name
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}
    if not destination or not destination.strip():
        return {"error": "destination is required"}

    script_path = SCRIPTS_DIR / "move_task.applescript"
    logger.info("move_task called: task_id=%r destination=%r", task_id, destination)

    try:
        output = run_script(script_path, task_id, destination)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from move_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in move_task")
        return {"error": str(exc)}


@mcp.tool()
def drop_project(task_id: str) -> dict:
    """
    Drop a project in OmniFocus (mark as dropped/abandoned).

    Note: This only works for projects, not individual tasks.
    For tasks, use delete_task or complete_task instead.

    Args:
        task_id: The OmniFocus task ID of any task in the project

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("drop_project called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "drop")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from drop_project")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in drop_project")
        return {"error": str(exc)}


@mcp.tool()
def delete_task(task_id: str) -> dict:
    """
    Permanently delete a task from OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("delete_task called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "delete")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from delete_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in delete_task")
        return {"error": str(exc)}


@mcp.tool()
def flag_task(task_id: str, flagged: bool = True) -> dict:
    """
    Flag or unflag a task in OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        flagged: True to flag, False to unflag (default: True)

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    action = "flag" if flagged else "unflag"
    logger.info("flag_task called: task_id=%r flagged=%r", task_id, flagged)

    try:
        output = run_script(script_path, task_id, action)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from flag_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in flag_task")
        return {"error": str(exc)}


@mcp.tool()
def defer_task(task_id: str, defer_date: str | None = None) -> dict:
    """
    Set or clear the defer date of a task in OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        defer_date: ISO 8601 date string (e.g., "2025-01-15" or "2025-01-15T09:00:00").
                   If None or empty, clears the defer date.

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("defer_task called: task_id=%r defer_date=%r", task_id, defer_date)

    try:
        if defer_date:
            output = run_script(script_path, task_id, "defer", defer_date)
        else:
            output = run_script(script_path, task_id, "clear_defer")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from defer_task")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in defer_task")
        return {"error": str(exc)}


@mcp.tool()
def set_due_date(task_id: str, due_date: str | None = None) -> dict:
    """
    Set or clear the due date of a task in OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        due_date: ISO 8601 date string (e.g., "2025-01-15" or "2025-01-15T17:00:00").
                 If None or empty, clears the due date.

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("set_due_date called: task_id=%r due_date=%r", task_id, due_date)

    try:
        if due_date:
            output = run_script(script_path, task_id, "due", due_date)
        else:
            output = run_script(script_path, task_id, "clear_due")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from set_due_date")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in set_due_date")
        return {"error": str(exc)}


@mcp.tool()
def pause_project(task_id: str) -> dict:
    """
    Pause (put on hold) a project in OmniFocus.

    Args:
        task_id: The OmniFocus task ID of a task within the project

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("pause_project called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "pause")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from pause_project")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in pause_project")
        return {"error": str(exc)}


@mcp.tool()
def resume_project(task_id: str) -> dict:
    """
    Resume (reactivate) a paused project in OmniFocus.

    Args:
        task_id: The OmniFocus task ID of a task within the project

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "update_task.applescript"
    logger.info("resume_project called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "resume")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from resume_project")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in resume_project")
        return {"error": str(exc)}


@mcp.tool()
def set_repetition(task_id: str, rrule: str | None = None, method: RepetitionMethod = "due") -> dict:
    """
    Set or clear the repetition rule for a task in OmniFocus.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        rrule: iCalendar RRULE string. Examples:
               - "FREQ=DAILY" - repeats every day
               - "FREQ=WEEKLY" - repeats every week
               - "FREQ=WEEKLY;BYDAY=MO,WE,FR" - repeats Mon, Wed, Fri
               - "FREQ=MONTHLY;BYMONTHDAY=1" - repeats 1st of each month
               - "FREQ=YEARLY" - repeats yearly
               - None or empty string - clears the repetition
        method: How to calculate the next occurrence:
               - "due": Next occurrence based on due date (default)
               - "defer": Next occurrence based on defer date
               - "fixed": Fixed schedule (not based on completion date)

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "set_repetition.applescript"
    logger.info("set_repetition called: task_id=%r rrule=%r method=%r", task_id, rrule, method)

    try:
        rule_arg = rrule if rrule else "none"
        method_arg = method if method else "due"
        output = run_script(script_path, task_id, rule_arg, method_arg)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from set_repetition")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in set_repetition")
        return {"error": str(exc)}


@mcp.tool()
def list_tags() -> dict:
    """
    List all tags in OmniFocus.

    Returns:
        Dictionary with "tags" key containing list of tag objects.
        Each tag has: id, name, path (full hierarchical path), parent, available, remaining counts.
        Tags can be hierarchical, e.g., "Folk : Asbjørn" means "Asbjørn" under "Folk".
    """
    script_path = SCRIPTS_DIR / "list_tags.applescript"
    logger.info("list_tags called")

    try:
        output = run_script(script_path)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from list_tags")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in list_tags")
        return {"error": str(exc)}


@mcp.tool()
def get_task_tags(task_id: str) -> dict:
    """
    Get the tags currently assigned to a task.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)

    Returns:
        Dictionary with task info and list of tags with their paths
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "manage_tags.applescript"
    logger.info("get_task_tags called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "get", "[]")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from get_task_tags")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in get_task_tags")
        return {"error": str(exc)}


@mcp.tool()
def add_task_tags(task_id: str, tags: list[str]) -> dict:
    """
    Add tags to a task (keeps existing tags).

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        tags: List of tag identifiers. Can be:
              - Tag name: "Work"
              - Full path for nested tags: "Folk : Asbjørn"
              - Tag ID: "abc123"

    Returns:
        Dictionary with status, added tags, and current tags list
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}
    if not tags:
        return {"error": "tags list is required"}

    script_path = SCRIPTS_DIR / "manage_tags.applescript"
    logger.info("add_task_tags called: task_id=%r tags=%r", task_id, tags)

    try:
        output = run_script(script_path, task_id, "add", json.dumps(tags))
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from add_task_tags")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in add_task_tags")
        return {"error": str(exc)}


@mcp.tool()
def remove_task_tags(task_id: str, tags: list[str]) -> dict:
    """
    Remove tags from a task.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        tags: List of tag identifiers to remove. Can be:
              - Tag name: "Work"
              - Full path for nested tags: "Folk : Asbjørn"
              - Tag ID: "abc123"

    Returns:
        Dictionary with status, removed tags, and current tags list
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}
    if not tags:
        return {"error": "tags list is required"}

    script_path = SCRIPTS_DIR / "manage_tags.applescript"
    logger.info("remove_task_tags called: task_id=%r tags=%r", task_id, tags)

    try:
        output = run_script(script_path, task_id, "remove", json.dumps(tags))
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from remove_task_tags")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in remove_task_tags")
        return {"error": str(exc)}


@mcp.tool()
def set_task_tags(task_id: str, tags: list[str]) -> dict:
    """
    Set the tags on a task (replaces all existing tags).

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        tags: List of tag identifiers. Can be:
              - Tag name: "Work"
              - Full path for nested tags: "Folk : Asbjørn"
              - Tag ID: "abc123"
              Use empty list [] to remove all tags.

    Returns:
        Dictionary with status and the new tags list
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}
    if tags is None:
        return {"error": "tags list is required (use [] to clear)"}

    script_path = SCRIPTS_DIR / "manage_tags.applescript"
    logger.info("set_task_tags called: task_id=%r tags=%r", task_id, tags)

    try:
        output = run_script(script_path, task_id, "set", json.dumps(tags))
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from set_task_tags")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in set_task_tags")
        return {"error": str(exc)}


@mcp.tool()
def get_task_note(task_id: str) -> dict:
    """
    Get the note/description of a task.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)

    Returns:
        Dictionary with task info and note content
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "manage_note.applescript"
    logger.info("get_task_note called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "get")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from get_task_note")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in get_task_note")
        return {"error": str(exc)}


@mcp.tool()
def set_task_note(task_id: str, note: str) -> dict:
    """
    Set the note/description of a task (replaces existing note).

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        note: The note text to set. Supports multi-line text.

    Returns:
        Dictionary with status and the new note content
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "manage_note.applescript"
    logger.info("set_task_note called: task_id=%r note_length=%d", task_id, len(note) if note else 0)

    try:
        output = run_script(script_path, task_id, "set", note or "")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from set_task_note")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in set_task_note")
        return {"error": str(exc)}


@mcp.tool()
def append_task_note(task_id: str, text: str) -> dict:
    """
    Append text to a task's note (adds to existing note with newline).

    Args:
        task_id: The OmniFocus task ID (from list_tasks)
        text: The text to append to the note

    Returns:
        Dictionary with status and the updated note content
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}
    if not text:
        return {"error": "text is required"}

    script_path = SCRIPTS_DIR / "manage_note.applescript"
    logger.info("append_task_note called: task_id=%r text_length=%d", task_id, len(text))

    try:
        output = run_script(script_path, task_id, "append", text)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from append_task_note")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in append_task_note")
        return {"error": str(exc)}


@mcp.tool()
def clear_task_note(task_id: str) -> dict:
    """
    Clear/remove the note from a task.

    Args:
        task_id: The OmniFocus task ID (from list_tasks)

    Returns:
        Dictionary with status of the operation
    """
    if not task_id or not task_id.strip():
        return {"error": "task_id is required"}

    script_path = SCRIPTS_DIR / "manage_note.applescript"
    logger.info("clear_task_note called: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id, "clear")
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from clear_task_note")
        return {"error": f"Invalid JSON from AppleScript: {exc}"}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in clear_task_note")
        return {"error": str(exc)}


if __name__ == "__main__":
    mcp.run()
