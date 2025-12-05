from __future__ import annotations

import json
import subprocess
from pathlib import Path


class AppleScriptError(RuntimeError):
    """Raised when an osascript invocation fails."""


def run_script(path: str | Path, *args: str) -> str:
    script_path = Path(path)
    command = ["osascript", str(script_path), *[str(arg) for arg in args]]

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
        details = f"{stderr or stdout or 'no output'}"
        raise AppleScriptError(
            f"osascript failed for {script_path} with exit code {exc.returncode}: {details}"
        ) from exc

    return completed.stdout.strip()


def run_script_json(path: str | Path, *args: str):
    output = run_script(path, *args)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise AppleScriptError(f"Invalid JSON output: {output}") from exc
