from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .applescript import AppleScriptError, run_script


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"


class OmniFocusError(RuntimeError):
    """Raised when OmniFocus operations fail."""


@dataclass
class Task:
    id: str
    name: str
    completed: bool


def list_inbox_tasks() -> list[Task]:
    script = SCRIPTS_DIR / "list_tasks.applescript"
    try:
        raw_output = run_script(script)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc

    if not raw_output:
        return []

    tasks: list[Task] = []
    for line in raw_output.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        task_id, name, completed_str = parts
        tasks.append(Task(id=task_id, name=name, completed=completed_str.lower() == "true"))
    return tasks


def add_inbox_task(name: str, note: str | None = None) -> str:
    script = SCRIPTS_DIR / "add_task.applescript"
    args = [name]
    if note:
        args.append(note)

    try:
        task_id = run_script(script, args)
    except AppleScriptError as exc:
        raise OmniFocusError(str(exc)) from exc

    return task_id
