"""
OmniFocus HTTP Server

FastAPI-based REST API for OmniFocus task management.
For MCP (Model Context Protocol) integration, use mcp_server.py instead.
"""

import json
import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from utils.applescript import AppleScriptError, run_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"

app = FastAPI(
    title="OmniFocus HTTP Server",
    description="REST API for OmniFocus task management via AppleScript",
)

FilterType = Literal["due_soon", "flagged", "inbox"]
ALLOWED_FILTERS: set[FilterType] = {"due_soon", "flagged", "inbox"}


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/mcp/list_tasks")
async def list_tasks(payload: dict | None = None) -> dict | JSONResponse:
    """List tasks from OmniFocus with optional filtering."""
    script_path = SCRIPTS_DIR / "list_tasks.applescript"
    logger.info("list_tasks request received")

    payload = payload or {}
    filter_value = payload.get("filter")
    args: list[str] = []

    if filter_value:
        if filter_value not in ALLOWED_FILTERS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid filter. Allowed: due_soon, flagged, inbox"},
            )
        args.append(filter_value)

    try:
        output = run_script(script_path, *args)
        return json.loads(output)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON from list_tasks script")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid JSON returned from list_tasks script"},
        )
    except AppleScriptError as exc:
        logger.exception("AppleScript error in list_tasks")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/mcp/summarize_tasks")
async def summarize_tasks(payload: dict | None = None) -> dict | JSONResponse:
    """Get a summary of tasks grouped by project."""
    from datetime import datetime, timezone

    logger.info("summarize_tasks request received")

    tasks_response = await list_tasks(payload)
    if isinstance(tasks_response, JSONResponse):
        return tasks_response

    tasks_data = tasks_response.get("tasks", [])
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

        due_dt = parse_due(task.get("due", ""))
        if due_dt:
            if due_dt.date() == today_date:
                entry["due_today"] += 1
            if due_dt < now:
                entry["overdue"] += 1

    return {"projects": list(summary.values())}


@app.post("/mcp/add_task", status_code=201)
async def add_task(payload: dict) -> dict | JSONResponse:
    """Add a new task to OmniFocus."""
    title = payload.get("title")
    project = payload.get("project")

    if not title:
        return JSONResponse(status_code=400, content={"error": "title is required"})

    script_path = SCRIPTS_DIR / "add_task.applescript"
    logger.info("add_task: title=%r project=%r", title, project)

    args = [title]
    if project:
        args.append(project)

    try:
        output = run_script(script_path, *args)
        return {"status": "ok", "output": output}
    except AppleScriptError as exc:
        logger.exception("AppleScript error in add_task")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/mcp/get_projects")
async def get_projects(payload: dict | None = None) -> dict | JSONResponse:
    """List all OmniFocus projects."""
    script_path = SCRIPTS_DIR / "get_projects.applescript"
    logger.info("get_projects request received")

    try:
        output = run_script(script_path)
        return json.loads(output)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON from get_projects script")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid JSON returned from get_projects script"},
        )
    except AppleScriptError as exc:
        logger.exception("AppleScript error in get_projects")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/mcp/complete_task")
async def complete_task(payload: dict) -> dict | JSONResponse:
    """Mark a task as completed."""
    task_id = payload.get("task_id")

    if not task_id:
        return JSONResponse(status_code=400, content={"error": "task_id is required"})

    script_path = SCRIPTS_DIR / "complete_task.applescript"
    logger.info("complete_task: task_id=%r", task_id)

    try:
        output = run_script(script_path, task_id)
        return json.loads(output)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON from complete_task script")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid JSON returned from complete_task script"},
        )
    except AppleScriptError as exc:
        logger.exception("AppleScript error in complete_task")
        return JSONResponse(status_code=500, content={"error": str(exc)})
