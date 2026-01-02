"""AppleScript execution utilities."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


class AppleScriptError(RuntimeError):
    """Raised when an osascript invocation fails."""


def run_script(path: str | Path, *args: str) -> str:
    """
    Execute an AppleScript or JXA file and return its output.

    Args:
        path: Path to the .applescript or .js file
        *args: Arguments to pass to the script

    Returns:
        The script's stdout output (stripped)

    Raises:
        AppleScriptError: If osascript is not found or the script fails
    """
    script_path = Path(path)

    # Use -l JavaScript for .js files
    if script_path.suffix == ".js":
        command = ["osascript", "-l", "JavaScript", str(script_path), *(str(arg) for arg in args)]
    else:
        command = ["osascript", str(script_path), *(str(arg) for arg in args)]

    try:
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise AppleScriptError("osascript executable not found") from exc
    except subprocess.CalledProcessError as exc:
        stdout = (exc.stdout or "").strip()
        stderr = (exc.stderr or "").strip()
        details = stderr or stdout or "no output"
        raise AppleScriptError(
            f"osascript failed for {script_path.name} (exit {exc.returncode}): {details}"
        ) from exc

    return completed.stdout.strip()


def run_script_json(path: str | Path, *args: str) -> Any:
    """
    Execute an AppleScript file and parse the output as JSON.

    Args:
        path: Path to the .applescript file
        *args: Arguments to pass to the script

    Returns:
        Parsed JSON output

    Raises:
        AppleScriptError: If the script fails or returns invalid JSON
    """
    output = run_script(path, *args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise AppleScriptError(f"Invalid JSON output: {output[:200]}") from exc
