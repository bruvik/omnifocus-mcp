from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable


class AppleScriptError(RuntimeError):
    """Raised when an osascript invocation fails."""


def run_script(script_path: Path, args: Iterable[str] | None = None) -> str:
    command = ["osascript", str(script_path)]
    if args:
        command.extend(args)

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stdout = exc.stdout.strip() if exc.stdout else ""
        stderr = exc.stderr.strip() if exc.stderr else ""
        message = f"osascript failed: {stderr or stdout or exc}"
        raise AppleScriptError(message) from exc

    return completed.stdout.strip()
