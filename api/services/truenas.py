"""
TrueNAS SCALE service — httpx client against https://192.168.8.198/api/v2.0
Manages datasets under bigpool/proxlab/ only.
Protected (never touched): bigpool/vmdata, bigpool/models
"""
from __future__ import annotations

from typing import Optional
import httpx

from api.config import settings


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=f"https://{settings.truenas_host}/api/v2.0",
        headers={"Authorization": f"Bearer {settings.truenas_api_key}"},
        verify=settings.truenas_verify_ssl,
        timeout=30.0,
    )


def _dataset_path(name: str) -> str:
    """Full ZFS dataset path for a proxlab-managed dataset."""
    return f"{settings.truenas_proxlab_parent}/{name}"


def _nfs_path(name: str) -> str:
    """NFS-mountable path (TrueNAS puts datasets under /mnt/)."""
    return f"/mnt/{_dataset_path(name)}"


def _assert_not_protected(dataset_path: str) -> None:
    for protected in settings.truenas_protected_datasets:
        if dataset_path == protected or dataset_path.startswith(protected + "/"):
            raise PermissionError(
                f"Dataset '{dataset_path}' is protected and cannot be modified by proxlab"
            )


# ---------------------------------------------------------------------------
# Datasets
# ---------------------------------------------------------------------------

def list_datasets() -> list[dict]:
    """List all proxlab-managed datasets (bigpool/proxlab/* only)."""
    with _client() as c:
        resp = c.get("/pool/dataset", params={"name": settings.truenas_proxlab_parent})
        resp.raise_for_status()
        datasets = resp.json()

    results = []
    for ds in datasets:
        path = ds.get("name", "")
        if path == settings.truenas_proxlab_parent:
            # The parent container dataset itself — skip
            continue
        if path.startswith(settings.truenas_proxlab_parent + "/"):
            name = path.removeprefix(settings.truenas_proxlab_parent + "/")
            used = ds.get("used", {}).get("parsed", 0)
            avail = ds.get("available", {}).get("parsed", 0)
            results.append({
                "name": name,
                "dataset_path": path,
                "nfs_path": f"/mnt/{path}",
                "nfs_server": settings.truenas_nfs_server,
                "used_gb": round(used / 1024**3, 2),
                "available_gb": round(avail / 1024**3, 2),
                "quota_gb": round(ds.get("quota", {}).get("parsed", 0) / 1024**3, 2),
            })
    return results


def create_dataset(name: str, quota_gb: int) -> dict:
    """Create a new dataset at bigpool/proxlab/<name> with a quota."""
    dataset_path = _dataset_path(name)
    _assert_not_protected(dataset_path)

    with _client() as c:
        resp = c.post("/pool/dataset", json={
            "name": dataset_path,
            "type": "FILESYSTEM",
            "sync": "STANDARD",
            "compression": "lz4",   # TrueNAS SCALE lowercase
            "atime": "OFF",
            "quota": quota_gb * 1024**3,
        })
        resp.raise_for_status()
        ds = resp.json()

    return {
        "name": name,
        "dataset_path": dataset_path,
        "nfs_path": _nfs_path(name),
        "nfs_server": settings.truenas_nfs_server,
        "quota_gb": quota_gb,
        "used_gb": 0.0,
        "available_gb": float(quota_gb),
    }


def delete_dataset(name: str) -> None:
    """Delete a proxlab-managed dataset and its NFS export."""
    dataset_path = _dataset_path(name)
    _assert_not_protected(dataset_path)

    # Remove NFS export first (if any)
    try:
        _delete_nfs_export(name)
    except Exception:
        pass  # NFS share may not exist

    # URL-encode the dataset path: httpx will re-encode if we put slashes in the URL,
    # so we encode manually and use a raw path.
    encoded = dataset_path.replace("/", "%2F")
    with _client() as c:
        # TrueNAS expects recursive as a JSON body, not a query param
        resp = c.delete(f"/pool/dataset/id/{encoded}", json={"recursive": True})
        resp.raise_for_status()


def get_dataset(name: str) -> Optional[dict]:
    dataset_path = _dataset_path(name)
    encoded = dataset_path.replace("/", "%2F")
    with _client() as c:
        resp = c.get(f"/pool/dataset/id/{encoded}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        ds = resp.json()
    used = ds.get("used", {}).get("parsed", 0)
    avail = ds.get("available", {}).get("parsed", 0)
    return {
        "name": name,
        "dataset_path": dataset_path,
        "nfs_path": _nfs_path(name),
        "nfs_server": settings.truenas_nfs_server,
        "used_gb": round(used / 1024**3, 2),
        "available_gb": round(avail / 1024**3, 2),
        "quota_gb": round(ds.get("quota", {}).get("parsed", 0) / 1024**3, 2),
    }


# ---------------------------------------------------------------------------
# NFS exports
# ---------------------------------------------------------------------------

def create_nfs_export(
    name: str,
    allowed_hosts: Optional[list[str]] = None,
) -> dict:
    """
    Create an NFS export for a proxlab dataset.
    If allowed_hosts is empty, defaults to the home LAN (192.168.8.0/24).
    """
    nfs_path = _nfs_path(name)
    hosts = allowed_hosts or ["192.168.8.0/24"]

    with _client() as c:
        resp = c.post("/sharing/nfs", json={
            "path": nfs_path,
            "comment": f"proxlab: {name}",
            "hosts": hosts,
            "ro": False,
            "maproot_user": "root",
            "maproot_group": "root",  # SCALE is Linux, not BSD — root not wheel
        })
        resp.raise_for_status()
        return resp.json()


def _delete_nfs_export(name: str) -> None:
    nfs_path = _nfs_path(name)
    with _client() as c:
        resp = c.get("/sharing/nfs")
        resp.raise_for_status()
        shares = resp.json()
        for share in shares:
            if share.get("path") == nfs_path:
                del_resp = c.delete(f"/sharing/nfs/id/{share['id']}")
                del_resp.raise_for_status()
                return


# ---------------------------------------------------------------------------
# Pool info
# ---------------------------------------------------------------------------

def pool_status() -> dict:
    with _client() as c:
        resp = c.get(f"/pool")
        resp.raise_for_status()
        pools = resp.json()
    for pool in pools:
        if pool["name"] == settings.truenas_pool:
            return pool
    raise KeyError(f"Pool '{settings.truenas_pool}' not found on TrueNAS")
