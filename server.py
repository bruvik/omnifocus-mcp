import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from utils.applescript import AppleScriptError, run_script


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
    try:
        output = run_script(script_path)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="Invalid JSON returned from list_tasks script"
        ) from exc
    except AppleScriptError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/mcp/addTask", status_code=201)
def add_task(payload: AddTaskRequest):
    script_path = Path(__file__).resolve().parent / "scripts" / "add_task.applescript"
    args = [payload.title]
    if payload.project:
        args.append(payload.project)

    try:
        output = run_script(script_path, *args)
        return {"status": "ok", "output": output}
    except AppleScriptError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/mcp/getProjects")
def get_projects():
    script_path = Path(__file__).resolve().parent / "scripts" / "get_projects.applescript"
    try:
        output = run_script(script_path)
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500, detail="Invalid JSON returned from get_projects script"
        ) from exc
    except AppleScriptError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
