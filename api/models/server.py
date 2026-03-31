from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class ServerCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-]{1,30}[a-z0-9]$", description="Hostname for the VM")
    flavor: str = Field(default="small", description="Flavor name (small/medium/large) or 'custom'")
    template: str = Field(default="base", description="Cloud-init template name (base/dev)")
    # Custom resource overrides (only used when flavor='custom')
    cores: Optional[int] = Field(default=None, ge=1, le=32)
    memory_mb: Optional[int] = Field(default=None, ge=512, le=131072)
    disk_gb: Optional[int] = Field(default=None, ge=8, le=2000)
    # Optional extras
    storage_name: Optional[str] = Field(default=None, description="Allocate a NAS dataset and mount it")
    storage_quota_gb: Optional[int] = Field(default=None, ge=1)
    database_name: Optional[str] = Field(default=None, description="Provision a Postgres DB for this server")
    ssh_keys: list[str] = Field(default_factory=list, description="SSH public keys to inject")
    tailscale_auth_key: Optional[str] = Field(default=None, description="Tailscale auth key for auto-join")


class BatchServerCreate(BaseModel):
    servers: list[ServerCreate] = Field(..., min_length=1, max_length=50)


class ServerAction(BaseModel):
    action: Literal["os-start", "os-stop", "os-reboot"]


class ServerResponse(BaseModel):
    id: int                          # Proxmox VMID
    name: str
    status: Literal["running", "stopped", "pending", "error"]
    ip: Optional[str] = None        # from QEMU guest agent
    flavor: str
    template: str
    cores: int
    memory_mb: int
    disk_gb: int
    node: str
    storage_dataset: Optional[str] = None
    database_name: Optional[str] = None
    created_at: Optional[datetime] = None
    task_id: Optional[str] = None   # set when an async operation is in progress
