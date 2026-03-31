"""
Integration tests for API endpoints using FastAPI TestClient.
External services (Proxmox, TrueNAS, Postgres) are mocked.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from api.main import app

TOKEN = "test-api-token"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


@pytest.fixture()
def client():
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def test_no_token_returns_401(client):
    resp = client.get("/api/servers")
    assert resp.status_code == 401  # HTTPBearer returns 401 when Authorization header missing


def test_wrong_token_returns_401(client):
    resp = client.get("/api/servers", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Flavors (no external deps)
# ---------------------------------------------------------------------------

def test_list_flavors_no_auth_not_required(client):
    # Flavors endpoint has no auth — it's public read-only metadata
    resp = client.get("/api/flavors")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 5
    names = [f["name"] for f in data]
    assert "small" in names
    assert "xlarge" in names


def test_flavor_structure(client):
    resp = client.get("/api/flavors")
    flavor = resp.json()[0]
    assert "name" in flavor
    assert "cores" in flavor
    assert "memory_mb" in flavor
    assert "disk_gb" in flavor


# ---------------------------------------------------------------------------
# Servers (mocked Proxmox)
# ---------------------------------------------------------------------------

def test_list_servers_empty(client):
    with patch("api.services.proxmox.list_vms", return_value=[]):
        resp = client.get("/api/servers", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_servers_filters_vmid_range(client):
    vms = [
        {"vmid": 100, "name": "old-vm", "status": "running", "cpus": 1},   # outside range
        {"vmid": 200, "name": "proxlab-vm", "status": "stopped", "cpus": 2},  # in range
        {"vmid": 300, "name": "beyond", "status": "stopped", "cpus": 1},   # outside range
    ]
    with patch("api.services.proxmox.list_vms", return_value=vms), \
         patch("api.services.proxmox.get_vm_config", return_value={"cores": 2, "memory": 2048}):
        resp = client.get("/api/servers", headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == 200
    assert data[0]["name"] == "proxlab-vm"


def test_get_server_outside_range_returns_403(client):
    resp = client.get("/api/servers/100", headers=HEADERS)
    assert resp.status_code == 403


def test_server_action_start(client):
    with patch("api.services.proxmox.start_vm", return_value="UPID:beast:000:start"):
        resp = client.post(
            "/api/servers/200/action",
            json={"action": "os-start"},
            headers=HEADERS,
        )
    assert resp.status_code == 202
    data = resp.json()
    assert data["type"] == "os-start"
    assert data["vmid"] == 200


def test_server_action_invalid(client):
    resp = client.post(
        "/api/servers/200/action",
        json={"action": "invalid-action"},
        headers=HEADERS,
    )
    assert resp.status_code == 422  # Pydantic validation rejects unknown Literal


# ---------------------------------------------------------------------------
# Storage (mocked TrueNAS)
# ---------------------------------------------------------------------------

def test_list_storage_empty(client):
    with patch("api.services.truenas.list_datasets", return_value=[]):
        resp = client.get("/api/storage", headers=HEADERS)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_storage(client):
    mock_ds = {
        "name": "myproject",
        "dataset_path": "bigpool/proxlab/myproject",
        "nfs_path": "/mnt/bigpool/proxlab/myproject",
        "nfs_server": "192.168.8.198",
        "quota_gb": 50,
        "used_gb": 0.0,
        "available_gb": 50.0,
    }
    with patch("api.services.truenas.create_dataset", return_value=mock_ds), \
         patch("api.services.truenas.create_nfs_export", return_value={}):
        resp = client.post(
            "/api/storage",
            json={"name": "myproject", "quota_gb": 50},
            headers=HEADERS,
        )
    assert resp.status_code == 201
    assert resp.json()["name"] == "myproject"
    assert resp.json()["quota_gb"] == 50


def test_delete_protected_dataset_returns_403(client):
    with patch(
        "api.services.truenas.delete_dataset",
        side_effect=PermissionError("Dataset 'bigpool/vmdata' is protected"),
    ):
        resp = client.delete("/api/storage/vmdata", headers=HEADERS)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Databases (mocked Postgres)
# ---------------------------------------------------------------------------

def test_list_databases_empty(client):
    with patch("api.services.postgres.list_databases", return_value=[]):
        resp = client.get("/api/databases", headers=HEADERS)
    assert resp.status_code == 200


def test_create_database(client):
    mock_result = {
        "name": "myapp",
        "owner": "myapp",
        "size_mb": 0.0,
        "connection_string": "postgresql://myapp:abc123@192.168.8.10:5432/myapp",
    }
    with patch("api.services.postgres.create_database", return_value=mock_result):
        resp = client.post(
            "/api/databases",
            json={"name": "myapp"},
            headers=HEADERS,
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "myapp"
    assert "connection_string" in data
    assert "myapp" in data["connection_string"]
