from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from utils import omnifocus


class TaskCreate(BaseModel):
    name: str
    note: str | None = None


app = FastAPI(title="OmniFocus MCP Server")


@app.get("/tasks")
def list_tasks():
    try:
        tasks = [task.__dict__ for task in omnifocus.list_inbox_tasks()]
        return {"tasks": tasks}
    except omnifocus.OmniFocusError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    try:
        created_id = omnifocus.add_inbox_task(task.name, task.note)
        return {"id": created_id}
    except omnifocus.OmniFocusError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
