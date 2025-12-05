import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from utils.applescript import AppleScriptError, run_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(title="OmniFocus MCP Server")


@app.get("/health")
def health():
    return {"status": "ok"}


ALLOWED_LIST_FILTERS = {"due_soon", "flagged", "inbox"}


@app.post("/mcp/list_tasks")
async def list_tasks(payload: dict | None = None):
    script_path = Path(__file__).resolve().parent / "scripts" / "list_tasks.applescript"
    logger.info("Received listTasks request")

    payload = payload or {}
    filter = payload.get("filter")
    args: list[str] = []
    if filter:
        if filter not in ALLOWED_LIST_FILTERS:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Invalid filter. Allowed values: due_soon, flagged, inbox."
                },
            )
        args.append(filter)

    try:
        output = run_script(script_path, *args)
        logger.info("listTasks AppleScript output: %s", output)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from listTasks output")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid JSON returned from list_tasks script"},
        )
    except AppleScriptError as exc:
        logger.exception("AppleScript error during listTasks")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/mcp/summarize_tasks")
async def summarize_tasks(payload: dict | None = None):
    logger.info("Received summarizeTasks request")

    tasks_response = await list_tasks(payload)
    if isinstance(tasks_response, JSONResponse) and tasks_response.status_code != 200:
        return tasks_response

    try:
        tasks_data = tasks_response["tasks"]  # type: ignore[index]
    except Exception:
        logger.exception("Unexpected format from listTasks")
        return JSONResponse(
            status_code=500, content={"error": "Failed to read tasks for summary"}
        )

    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    today_date = now.date()

    def parse_due(due_str: str):
        if not due_str:
            return None
        try:
            # Expecting YYYY-MM-DDTHH:MM:SS
            return datetime.fromisoformat(due_str)
        except Exception:
            return None

    summary: dict[str, dict[str, int | str]] = {}

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
            entry["active"] += 1  # type: ignore[assignment]

        if task.get("flagged", False):
            entry["flagged"] += 1  # type: ignore[assignment]

        due_str = task.get("due", "")
        due_dt = parse_due(due_str)
        if due_dt:
            if due_dt.date() == today_date:
                entry["due_today"] += 1  # type: ignore[assignment]
            if due_dt < now:
                entry["overdue"] += 1  # type: ignore[assignment]

    projects_list = list(summary.values())

    logger.info("summarizeTasks result: %s", projects_list)
    return {"projects": projects_list}


@app.post("/mcp/add_task", status_code=201)
async def add_task(payload: dict):
    title = payload.get("title")
    project = payload.get("project")
    script_path = Path(__file__).resolve().parent / "scripts" / "add_task.applescript"
    logger.info("Received addTask request title=%s project=%s", title, project)
    args = []
    if title:
        args.append(title)
    if project:
        args.append(project)

    try:
        output = run_script(script_path, *args)
        logger.info("addTask AppleScript output: %s", output)
        return {"status": "ok", "output": output}
    except AppleScriptError as exc:
        logger.exception("AppleScript error during addTask")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/mcp/get_projects")
async def get_projects(payload: dict | None = None):
    script_path = Path(__file__).resolve().parent / "scripts" / "get_projects.applescript"
    logger.info("Received getProjects request")
    try:
        output = run_script(script_path)
        logger.info("getProjects AppleScript output: %s", output)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        logger.exception("Failed to decode JSON from getProjects output")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid JSON returned from get_projects script"},
        )
    except AppleScriptError as exc:
        logger.exception("AppleScript error during getProjects")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.post("/mcp/complete_task")
async def complete_task(payload: dict):
    task_id = payload.get("task_id")
    script_path = Path(__file__).resolve().parent / "scripts" / "complete_task.applescript"
    logger.info("Received completeTask request task_id=%s", task_id)
    try:
        output = run_script(script_path, task_id)
        logger.info("completeTask AppleScript output: %s", output)
        return json.loads(output)
    except json.JSONDecodeError:
        logger.exception("Failed to decode JSON from completeTask output")
        return JSONResponse(
            status_code=500,
            content={"error": "Invalid JSON returned from complete_task script"},
        )
    except AppleScriptError as exc:
        logger.exception("AppleScript error during completeTask")
        return JSONResponse(status_code=500, content={"error": str(exc)})
