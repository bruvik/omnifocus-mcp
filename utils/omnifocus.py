"""High-level OmniFocus Python API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .applescript import AppleScriptError, run_script_json

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class OmniFocusError(RuntimeError):
    """Raised when OmniFocus operations fail."""


@dataclass
class Task:
    """Represents an OmniFocus task."""

    id: str
    title: str
    project: str
    due: str
    defer: str
    flagged: bool
    completed: bool
    note: str


def list_tasks(filter_type: str | None = None) -> list[Task]:
    """
    List tasks from OmniFocus.

    Args:
        filter_type: Optional filter - "due_soon", "flagged", or "inbox"

    Returns:
        List of Task objects
    """
    script = SCRIPTS_DIR / "list_tasks.applescript"
    args: list[str] = []
    if filter_type:
        args.append(filter_type)

    try:
        data = run_script_json(script, *args)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc

    if not data:
        return []

    return [
        Task(
            id=str(item.get("id", "")),
            title=str(item.get("name", item.get("title", ""))),
            project=str(item.get("project", "")),
            due=str(item.get("due", "")),
            defer=str(item.get("defer", "")),
            flagged=bool(item.get("flagged", False)),
            completed=bool(item.get("completed", False)),
            note=str(item.get("note", "")),
        )
        for item in data.get("tasks", [])
    ]


def add_task(title: str, project: str | None = None) -> dict[str, Any]:
    """
    Add a new task to OmniFocus.

    Args:
        title: Task title (required)
        project: Optional project name

    Returns:
        Result dictionary from AppleScript
    """
    script = SCRIPTS_DIR / "add_task.applescript"
    args = [title]
    if project:
        args.append(project)

    try:
        return run_script_json(script, *args)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc


def complete_task(task_id: str) -> dict[str, Any]:
    """
    Mark a task as completed.

    Args:
        task_id: The OmniFocus task ID

    Returns:
        Result dictionary from AppleScript
    """
    script = SCRIPTS_DIR / "complete_task.applescript"
    try:
        return run_script_json(script, task_id)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc


def get_projects() -> list[dict[str, Any]]:
    """
    List all OmniFocus projects.

    Returns:
        List of project dictionaries
    """
    script = SCRIPTS_DIR / "get_projects.applescript"
    try:
        data = run_script_json(script)
        return data.get("projects", [])
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc
