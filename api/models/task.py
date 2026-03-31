from pydantic import BaseModel
from typing import Literal, Optional, Any
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    ok = "ok"
    error = "error"


class TaskResponse(BaseModel):
    id: str                          # Proxmox UPID
    type: str                        # e.g. "qmclone", "qmstart", "qmdestroy"
    status: TaskStatus
    node: str
    vmid: Optional[int] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    log: list[str] = []              # last N lines of task log
    result: Optional[Any] = None    # populated on completion (e.g. ServerResponse)
    error: Optional[str] = None
