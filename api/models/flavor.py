from pydantic import BaseModel, Field


class Flavor(BaseModel):
    name: str
    cores: int
    memory_mb: int
    disk_gb: int
    description: str = ""


class FlavorCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9\-]+$")
    cores: int = Field(..., ge=1, le=32)
    memory_mb: int = Field(..., ge=512, le=131072)
    disk_gb: int = Field(..., ge=8, le=2000)
    description: str = ""


# Built-in flavors — these are always available without any DB
BUILTIN_FLAVORS: list[Flavor] = [
    Flavor(name="micro",  cores=1, memory_mb=512,   disk_gb=10,  description="IoT / lightweight services"),
    Flavor(name="small",  cores=1, memory_mb=1024,  disk_gb=20,  description="Dev, light workloads"),
    Flavor(name="medium", cores=2, memory_mb=4096,  disk_gb=40,  description="General purpose dev server"),
    Flavor(name="large",  cores=4, memory_mb=8192,  disk_gb=80,  description="Build servers, heavier workloads"),
    Flavor(name="xlarge", cores=8, memory_mb=16384, disk_gb=160, description="LLM inference, data processing"),
]
