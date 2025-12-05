#!/usr/bin/env python3
"""
Simple manual test runner for OmniFocus MCP API endpoints.

It exercises:
- GET /mcp/listTasks
- POST /mcp/addTask
- GET /mcp/listTasks (to verify the addition)
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict


BASE_URL = "http://localhost:8000"


def call_api(method: str, path: str, payload: Dict[str, Any] | None = None) -> Any:
    url = urllib.parse.urljoin(BASE_URL, path)
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            if body:
                return json.loads(body)
            return {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        msg = f"HTTP {exc.code} for {method} {path}"
        if body:
            msg += f" | body: {body}"
        raise RuntimeError(msg) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to reach server at {url}: {exc}") from exc


def pretty(label: str, data: Any) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(data, indent=2))


def main() -> int:
    try:
        initial = call_api("GET", "/mcp/listTasks")
        pretty("Initial tasks", initial)
    except Exception as exc:  # pragma: no cover - manual script
        print(f"Failed to list tasks initially: {exc}", file=sys.stderr)
        return 1

    new_task_payload = {"title": "Test task from test_api.py"}
    try:
        add_resp = call_api("POST", "/mcp/addTask", new_task_payload)
        pretty("Add task response", add_resp)
    except Exception as exc:
        print(f"Failed to add task: {exc}", file=sys.stderr)
        return 1

    try:
        after = call_api("GET", "/mcp/listTasks")
        pretty("Tasks after addition", after)
    except Exception as exc:
        print(f"Failed to list tasks after addition: {exc}", file=sys.stderr)
        return 1

    # Attempt a simple verification if possible.
    try:
        initial_ids = {t.get("id") for t in initial.get("tasks", [])}
        new_ids = {t.get("id") for t in after.get("tasks", [])}
        added_ids = [i for i in new_ids if i not in initial_ids and i]
        if added_ids:
            print(f"\nNew task IDs detected: {added_ids}")
        else:
            print("\nNo new task detected (check addTask response above).")
    except Exception:
        print("\nCould not verify new task presence.", file=sys.stderr)

    return 0


if __name__ == "__main__":  # pragma: no cover - manual script
    sys.exit(main())
