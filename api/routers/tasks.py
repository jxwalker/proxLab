from fastapi import APIRouter, HTTPException, Depends

from api.auth import require_token
from api.config import settings
from api.models import TaskResponse, TaskStatus
import api.services.proxmox as px_svc
import api.state as state  # no circular import

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, _: None = Depends(require_token)):
    """
    Poll a task. Supports both:
    - proxlab internal task IDs (create-<name>-<id>)
    - raw Proxmox UPIDs
    """
    # Internal proxlab task
    if task_id in state.tasks:
        t = state.tasks[task_id]
        return TaskResponse(
            id=task_id,
            type="server-create",
            status=t["status"],
            node=settings.proxmox_node,
            vmid=t.get("vmid"),
            error=t.get("error"),
        )

    # Raw Proxmox UPID (for power actions etc.)
    try:
        status = px_svc.get_task_status(task_id)
        log = px_svc.get_task_log(task_id)
        px_status = status.get("status", "")
        exitstatus = status.get("exitstatus", "")
        if px_status == "stopped":
            task_status = TaskStatus.ok if exitstatus == "OK" else TaskStatus.error
        else:
            task_status = TaskStatus.running

        return TaskResponse(
            id=task_id,
            type=status.get("type", "unknown"),
            status=task_status,
            node=status.get("node", settings.proxmox_node),
            vmid=status.get("id") and int(status["id"]) if status.get("id") else None,
            log=log[-20:],  # last 20 lines
            error=exitstatus if task_status == TaskStatus.error else None,
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {e}")
