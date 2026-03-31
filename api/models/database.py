from pydantic import BaseModel, Field


class DatabaseCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-z][a-z0-9_]{1,60}$")
    owner: str = Field(default="", description="DB user/role name. Defaults to same as name.")


class DatabaseResponse(BaseModel):
    name: str
    owner: str
    size_mb: float
    connection_string: str   # postgresql://user:pass@host/name
