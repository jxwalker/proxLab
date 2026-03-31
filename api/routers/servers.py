from __future__ import annotations

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from api.auth import require_token
from api.config import settings
from api.models import (
    ServerCreate, ServerResponse, ServerAction, BatchServerCreate,
    TaskResponse, TaskStatus,
)
from api.models.flavor import BUILTIN_FLAVORS
import api.services.proxmox as px_svc
import api.services.truenas as tn_svc
import api.services.postgres as pg_svc
import api.state as state

router = APIRouter(prefix="/api/servers", tags=["servers"])


def _resolve_flavor(req: ServerCreate) -> tuple[int, int, int]:
    """Return (cores, memory_mb, disk_gb) from a flavor name or custom values."""
    if req.flavor == "custom":
        if not all([req.cores, req.memory_mb, req.disk_gb]):
            raise HTTPException(
                status_code=400,
                detail="flavor='custom' requires cores, memory_mb and disk_gb",
            )
        return req.cores, req.memory_mb, req.disk_gb  # type: ignore
    flavor = next((f for f in BUILTIN_FLAVORS if f.name == req.flavor), None)
    if not flavor:
        raise HTTPException(status_code=400, detail=f"Unknown flavor: {req.flavor}")
    return (
        req.cores or flavor.cores,
        req.memory_mb or flavor.memory_mb,
        req.disk_gb or flavor.disk_gb,
    )


def _vm_to_response(vm: dict, config: dict | None = None) -> ServerResponse:
    vmid = int(vm["vmid"])
    status_map = {"running": "running", "stopped": "stopped"}
    vm_status = status_map.get(vm.get("status", ""), "pending")
    ip = px_svc.get_vm_ip(vmid) if vm_status == "running" else None
    if config is None:
        try:
            config = px_svc.get_vm_config(vmid)
        except Exception:
            config = {}
    return ServerResponse(
        id=vmid,
        name=vm.get("name", str(vmid)),
        status=vm_status,  # type: ignore[arg-type]
        ip=ip,
        flavor=config.get("description", "unknown"),
        template="unknown",
        cores=config.get("cores", vm.get("cpus", 1)),
        memory_mb=config.get("memory", 1024),
        disk_gb=0,
        node=settings.proxmox_node,
        task_id=None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[ServerResponse])
def list_servers(_: None = Depends(require_token)):
    """List all proxlab-managed servers (VMID 200-299)."""
    vms = px_svc.list_vms()
    proxlab_vms = [
        v for v in vms
        if settings.proxmox_vmid_min <= int(v["vmid"]) <= settings.proxmox_vmid_max
    ]
    return [_vm_to_response(v) for v in proxlab_vms]


@router.post("", response_model=TaskResponse, status_code=202)
async def create_server(
    req: ServerCreate,
    background: BackgroundTasks,
    _: None = Depends(require_token),
):
    """Provision a new server. Returns a task ID to poll for completion."""
    cores, memory_mb, disk_gb = _resolve_flavor(req)
    task_id = f"create-{req.name}-{id(req)}"
    state.new_task(task_id)

    async def _provision() -> None:
        try:
            state.set_running(task_id)
            vmid, _ = px_svc.clone_template(
                name=req.name,
                cores=cores,
                memory_mb=memory_mb,
                disk_gb=disk_gb,
                ssh_keys=req.ssh_keys or None,
            )
            if req.storage_name:
                tn_svc.create_dataset(req.storage_name, req.storage_quota_gb or 50)
                tn_svc.create_nfs_export(req.storage_name)
            if req.database_name:
                await pg_svc.create_database(req.database_name)
            start_upid = px_svc.start_vm(vmid)
            px_svc.wait_for_task(start_upid)
            state.set_ok(task_id, vmid=vmid)
        except Exception as exc:
            state.set_error(task_id, str(exc))

    background.add_task(_provision)
    return TaskResponse(
        id=task_id,
        type="server-create",
        status=TaskStatus.pending,
        node=settings.proxmox_node,
    )


@router.post("/batch", response_model=list[TaskResponse], status_code=202)
async def batch_create_servers(
    req: BatchServerCreate,
    background: BackgroundTasks,
    _: None = Depends(require_token),
):
    """Provision multiple servers in one call. Returns one task ID per server."""
    results = []
    for server_req in req.servers:
        cores, memory_mb, disk_gb = _resolve_flavor(server_req)
        task_id = f"create-{server_req.name}-{id(server_req)}"
        state.new_task(task_id)

        # Capture loop vars by default-argument binding
        async def _provision(
            r=server_req, c=cores, m=memory_mb, d=disk_gb, tid=task_id
        ) -> None:
            try:
                state.set_running(tid)
                vmid, _ = px_svc.clone_template(
                    name=r.name, cores=c, memory_mb=m, disk_gb=d,
                    ssh_keys=r.ssh_keys or None,
                )
                if r.storage_name:
                    tn_svc.create_dataset(r.storage_name, r.storage_quota_gb or 50)
                    tn_svc.create_nfs_export(r.storage_name)
                if r.database_name:
                    await pg_svc.create_database(r.database_name)
                px_svc.wait_for_task(px_svc.start_vm(vmid))
                state.set_ok(tid, vmid=vmid)
            except Exception as exc:
                state.set_error(tid, str(exc))

        background.add_task(_provision)
        results.append(TaskResponse(
            id=task_id,
            type="server-create",
            status=TaskStatus.pending,
            node=settings.proxmox_node,
        ))
    return results


@router.get("/{vmid}", response_model=ServerResponse)
def get_server(vmid: int, _: None = Depends(require_token)):
    if not (settings.proxmox_vmid_min <= vmid <= settings.proxmox_vmid_max):
        raise HTTPException(status_code=403, detail="VMID outside proxlab range")
    try:
        vm = px_svc.get_vm(vmid)
        return _vm_to_response(vm)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/{vmid}/action", response_model=TaskResponse, status_code=202)
def server_action(vmid: int, action: ServerAction, _: None = Depends(require_token)):
    """Nova-style power actions: os-start, os-stop, os-reboot."""
    if not (settings.proxmox_vmid_min <= vmid <= settings.proxmox_vmid_max):
        raise HTTPException(status_code=403, detail="VMID outside proxlab range")
    try:
        if action.action == "os-start":
            upid = px_svc.start_vm(vmid)
        elif action.action == "os-stop":
            upid = px_svc.stop_vm(vmid)
        elif action.action == "os-reboot":
            upid = px_svc.reboot_vm(vmid)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action.action}")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return TaskResponse(
        id=upid,
        type=action.action,
        status=TaskStatus.running,
        node=settings.proxmox_node,
        vmid=vmid,
    )


@router.delete("/{vmid}", status_code=204)
def destroy_server(vmid: int, _: None = Depends(require_token)):
    if not (settings.proxmox_vmid_min <= vmid <= settings.proxmox_vmid_max):
        raise HTTPException(status_code=403, detail="VMID outside proxlab range")
    try:
        px_svc.destroy_vm(vmid)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
