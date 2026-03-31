from pydantic import BaseModel, Field
from typing import Optional


class StorageCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9\-_]{1,40}[a-z0-9]$")
    quota_gb: int = Field(default=50, ge=1, le=10000)
    nfs_allowed_hosts: list[str] = Field(
        default_factory=list,
        description="IP/CIDR list allowed to mount. Empty = allow all LAN (192.168.8.0/24)",
    )


class StorageResponse(BaseModel):
    name: str
    dataset_path: str        # bigpool/proxlab/<name>
    nfs_path: str            # /mnt/bigpool/proxlab/<name>
    nfs_server: str          # 192.168.8.198
    quota_gb: int
    used_gb: float
    available_gb: float
