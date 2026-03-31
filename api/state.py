"""
Shared application state.
Kept in a separate module to avoid circular imports between routers.
"""
from api.models.task import TaskStatus

# In-memory task store: task_id -> {status, vmid, error}
# Replace with Redis for multi-worker / persistent deployments.
tasks: dict[str, dict] = {}


def new_task(task_id: str) -> None:
    tasks[task_id] = {"status": TaskStatus.pending, "vmid": None, "error": None}


def set_running(task_id: str) -> None:
    tasks[task_id]["status"] = TaskStatus.running


def set_ok(task_id: str, vmid: int | None = None) -> None:
    tasks[task_id]["status"] = TaskStatus.ok
    if vmid is not None:
        tasks[task_id]["vmid"] = vmid


def set_error(task_id: str, error: str) -> None:
    tasks[task_id]["status"] = TaskStatus.error
    tasks[task_id]["error"] = error
