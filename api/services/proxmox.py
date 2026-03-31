"""
Proxmox VE service — wraps proxmoxer 2.x with API token auth.
Node: beast (192.168.8.197)
VMID range: 200-299
"""
from __future__ import annotations

import time
from typing import Optional
from proxmoxer import ProxmoxAPI

from api.config import settings


def _client() -> ProxmoxAPI:
    return ProxmoxAPI(
        settings.proxmox_host,
        user=settings.proxmox_user,
        token_name=settings.proxmox_token_name,
        token_value=settings.proxmox_token_value,
        verify_ssl=settings.proxmox_verify_ssl,
    )


# ---------------------------------------------------------------------------
# VMID management
# ---------------------------------------------------------------------------

def next_vmid() -> int:
    """Return the next free VMID in the proxlab range (200-299)."""
    px = _client()
    used: set[int] = set()
    for node in px.nodes.get():
        for vm in px.nodes(node["node"]).qemu.get():
            used.add(int(vm["vmid"]))
        for ct in px.nodes(node["node"]).lxc.get():
            used.add(int(ct["vmid"]))
    for vmid in range(settings.proxmox_vmid_min, settings.proxmox_vmid_max + 1):
        if vmid not in used:
            return vmid
    raise RuntimeError(
        f"No free VMIDs in range {settings.proxmox_vmid_min}-{settings.proxmox_vmid_max}"
    )


# ---------------------------------------------------------------------------
# Task management
# ---------------------------------------------------------------------------

def wait_for_task(upid: str, timeout: int = 300, poll_interval: float = 2.0) -> dict:
    """
    Poll a Proxmox task UPID until it stops.
    Returns the status dict. Raises RuntimeError on task failure.
    """
    px = _client()
    node = settings.proxmox_node
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = px.nodes(node).tasks(upid).status.get()
        if status["status"] == "stopped":
            exit_status = status.get("exitstatus", "OK")
            if exit_status != "OK":
                raise RuntimeError(f"Proxmox task {upid} failed: {exit_status}")
            return status
        time.sleep(poll_interval)
    raise TimeoutError(f"Proxmox task {upid} timed out after {timeout}s")


def get_task_status(upid: str) -> dict:
    px = _client()
    return px.nodes(settings.proxmox_node).tasks(upid).status.get()


def get_task_log(upid: str) -> list[str]:
    px = _client()
    entries = px.nodes(settings.proxmox_node).tasks(upid).log.get()
    return [e["t"] for e in entries]


# ---------------------------------------------------------------------------
# VM lifecycle
# ---------------------------------------------------------------------------

def list_vms() -> list[dict]:
    """Return all VMs on beast with status."""
    px = _client()
    vms = px.nodes(settings.proxmox_node).qemu.get()
    return sorted(vms, key=lambda v: v["vmid"])


def get_vm(vmid: int) -> dict:
    px = _client()
    return px.nodes(settings.proxmox_node).qemu(vmid).status.current.get()


def get_vm_config(vmid: int) -> dict:
    px = _client()
    return px.nodes(settings.proxmox_node).qemu(vmid).config.get()


def get_vm_ip(vmid: int) -> Optional[str]:
    """
    Read the VM's IP from the QEMU guest agent.
    Returns None if the agent is not running or no IPv4 found.
    """
    px = _client()
    try:
        ifaces = px.nodes(settings.proxmox_node).qemu(vmid).agent(
            "network-get-interfaces"
        ).get()
        for iface in ifaces.get("result", []):
            if iface.get("name") in ("lo",):
                continue
            for addr in iface.get("ip-addresses", []):
                if addr.get("ip-address-type") == "ipv4":
                    ip = addr["ip-address"]
                    if not ip.startswith("127."):
                        return ip
    except Exception:
        pass
    return None


def clone_template(
    name: str,
    cores: int,
    memory_mb: int,
    disk_gb: int,
    cloud_init_user_data: Optional[str] = None,
    ssh_keys: Optional[list[str]] = None,
) -> tuple[int, str]:
    """
    Clone the base template, configure resources, and return (vmid, upid).
    The VM is NOT started here — caller decides when to start.
    """
    px = _client()
    node = settings.proxmox_node
    vmid = next_vmid()

    # Clone the template
    upid = px.nodes(node).qemu(settings.proxmox_template_id).clone.post(
        newid=vmid,
        name=name,
        full=1,
        storage=settings.proxmox_storage,
    )
    wait_for_task(upid)

    # Configure cores and memory
    px.nodes(node).qemu(vmid).config.put(
        cores=cores,
        memory=memory_mb,
        agent="enabled=1",
    )

    # Resize disk if needed (template disk is typically 8GB)
    if disk_gb > 8:
        px.nodes(node).qemu(vmid).resize.put(
            disk="scsi0",
            size=f"+{disk_gb - 8}G",
        )

    # Inject SSH keys via cloud-init
    if ssh_keys:
        from urllib.parse import quote
        keys_str = "\n".join(ssh_keys)
        px.nodes(node).qemu(vmid).config.put(sshkeys=quote(keys_str, safe=""))

    # Inject custom cloud-init user-data if provided
    if cloud_init_user_data:
        # Write to a snippet on local storage and reference it
        # For now we set the cicustom field (requires snippet storage configured)
        pass

    return vmid, upid


def start_vm(vmid: int) -> str:
    px = _client()
    return px.nodes(settings.proxmox_node).qemu(vmid).status.start.post()


def stop_vm(vmid: int, force: bool = False) -> str:
    px = _client()
    if force:
        return px.nodes(settings.proxmox_node).qemu(vmid).status.stop.post()
    return px.nodes(settings.proxmox_node).qemu(vmid).status.shutdown.post()


def reboot_vm(vmid: int) -> str:
    px = _client()
    return px.nodes(settings.proxmox_node).qemu(vmid).status.reboot.post()


def destroy_vm(vmid: int) -> str:
    """Stop (if running) then destroy a VM."""
    px = _client()
    node = settings.proxmox_node
    current = px.nodes(node).qemu(vmid).status.current.get()
    if current["status"] == "running":
        upid = px.nodes(node).qemu(vmid).status.stop.post()
        wait_for_task(upid)
    upid = px.nodes(node).qemu(vmid).delete()
    return upid


# ---------------------------------------------------------------------------
# Node info
# ---------------------------------------------------------------------------

def node_status() -> dict:
    px = _client()
    return px.nodes(settings.proxmox_node).status.get()
