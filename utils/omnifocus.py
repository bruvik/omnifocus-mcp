from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .applescript import AppleScriptError, run_script_json


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class OmniFocusError(RuntimeError):
    """Raised when OmniFocus operations fail."""


@dataclass
class Task:
    id: str
    title: str
    completed: bool


def list_inbox_tasks() -> list[Task]:
    script = SCRIPTS_DIR / "list_tasks.applescript"
    try:
        data = run_script_json(script)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc

    if not data:
        return []

    tasks_data = data.get("tasks", [])
    return [
        Task(
            id=str(item.get("id", "")),
            title=str(item.get("name", item.get("title", ""))),
            completed=bool(item.get("completed", False)),
        )
        for item in tasks_data
    ]


def add_inbox_task(title: str, project: str | None = None) -> dict:
    script = SCRIPTS_DIR / "add_task.applescript"
    args = [title]
    if project:
        args.append(project)

    try:
        result = run_script_json(script, args)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc

    return result
