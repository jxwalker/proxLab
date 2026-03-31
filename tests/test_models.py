"""
Unit tests for Pydantic models, state management, and flavors.
No external connections required.
"""
import pytest
from pydantic import ValidationError


def test_server_create_valid():
    from api.models.server import ServerCreate
    s = ServerCreate(name="my-server", flavor="small", template="base")
    assert s.name == "my-server"
    assert s.flavor == "small"


def test_server_create_name_validation():
    from api.models.server import ServerCreate
    with pytest.raises(ValidationError):
        ServerCreate(name="My Server!")  # uppercase + space invalid


def test_server_create_custom_flavor():
    from api.models.server import ServerCreate
    s = ServerCreate(name="my-box", flavor="custom", cores=4, memory_mb=8192, disk_gb=100)
    assert s.cores == 4
    assert s.memory_mb == 8192


def test_flavor_list():
    from api.models.flavor import BUILTIN_FLAVORS
    names = [f.name for f in BUILTIN_FLAVORS]
    assert "micro" in names
    assert "small" in names
    assert "medium" in names
    assert "large" in names
    assert "xlarge" in names


def test_flavors_ascending_resources():
    from api.models.flavor import BUILTIN_FLAVORS
    cores = [f.cores for f in BUILTIN_FLAVORS]
    memory = [f.memory_mb for f in BUILTIN_FLAVORS]
    # Resources should be non-decreasing
    assert cores == sorted(cores)
    assert memory == sorted(memory)


def test_storage_create_valid():
    from api.models.storage import StorageCreate
    s = StorageCreate(name="myproject", quota_gb=100)
    assert s.quota_gb == 100


def test_storage_create_name_validation():
    from api.models.storage import StorageCreate
    with pytest.raises(ValidationError):
        StorageCreate(name="MY PROJECT")  # spaces/uppercase invalid


def test_database_create_valid():
    from api.models.database import DatabaseCreate
    d = DatabaseCreate(name="myapp")
    assert d.name == "myapp"
    assert d.owner == ""


def test_task_status_enum():
    from api.models.task import TaskStatus
    assert TaskStatus.ok == "ok"
    assert TaskStatus.error == "error"
    assert TaskStatus.running == "running"
    assert TaskStatus.pending == "pending"


def test_state_task_lifecycle():
    from api.state import tasks, new_task, set_running, set_ok, set_error
    tasks.clear()

    new_task("t1")
    assert tasks["t1"]["status"].value == "pending"

    set_running("t1")
    assert tasks["t1"]["status"].value == "running"

    set_ok("t1", vmid=201)
    assert tasks["t1"]["status"].value == "ok"
    assert tasks["t1"]["vmid"] == 201

    new_task("t2")
    set_error("t2", "something went wrong")
    assert tasks["t2"]["status"].value == "error"
    assert "something went wrong" in tasks["t2"]["error"]

    tasks.clear()
