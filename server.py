import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from utils.applescript import AppleScriptError, run_script

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AddTaskRequest(BaseModel):
    title: str
    project: str | None = None


app = FastAPI(title="OmniFocus MCP Server")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/mcp/listTasks")
def list_tasks():
    script_path = Path(__file__).resolve().parent / "scripts" / "list_tasks.applescript"
    logger.info("Received listTasks request")
    try:
        output = run_script(script_path)
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


@app.post("/mcp/addTask", status_code=201)
def add_task(payload: AddTaskRequest):
    script_path = Path(__file__).resolve().parent / "scripts" / "add_task.applescript"
    logger.info("Received addTask request title=%s project=%s", payload.title, payload.project)
    args = [payload.title]
    if payload.project:
        args.append(payload.project)

    try:
        output = run_script(script_path, *args)
        logger.info("addTask AppleScript output: %s", output)
        return {"status": "ok", "output": output}
    except AppleScriptError as exc:
        logger.exception("AppleScript error during addTask")
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/mcp/getProjects")
def get_projects():
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


@app.post("/mcp/completeTask")
def complete_task(task_id: str):
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
