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
    script_path = SCRIPTS_DIR / "list_tasks.applescript"
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
def add_task(title: str, project: str | None = None) -> dict:
    """
    Add a new task to OmniFocus.

    Args:
        title: The task title/name (required)
        project: Optional project name to add the task to

    Returns:
        Dictionary with status and the created task details
    """
    if not title or not title.strip():
        return {"error": "Task title is required"}

    script_path = SCRIPTS_DIR / "add_task.applescript"
    logger.info("add_task called: title=%r project=%r", title, project)

    args = [title]
    if project:
        args.append(project)

    try:
        output = run_script(script_path, *args)
        logger.info("add_task output: %s", output)
        return {"status": "ok", "output": output}
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


if __name__ == "__main__":
    mcp.run()
