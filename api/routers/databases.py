from fastapi import APIRouter, HTTPException, Depends

from api.auth import require_token
from api.models import DatabaseCreate, DatabaseResponse
import api.services.postgres as pg_svc

router = APIRouter(prefix="/api/databases", tags=["databases"])


@router.get("", response_model=list[DatabaseResponse])
async def list_databases(_: None = Depends(require_token)):
    rows = await pg_svc.list_databases()
    # list_databases doesn't return connection_string — add placeholder
    return [DatabaseResponse(connection_string="(use /databases/{name} to get full string)", **r) for r in rows]


@router.post("", response_model=DatabaseResponse, status_code=201)
async def create_database(req: DatabaseCreate, _: None = Depends(require_token)):
    """Create a Postgres database + user. Returns connection string with password."""
    try:
        result = await pg_svc.create_database(req.name, req.owner or None)
        return DatabaseResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{name}", response_model=DatabaseResponse)
async def get_database(name: str, _: None = Depends(require_token)):
    result = await pg_svc.get_database(name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")
    return DatabaseResponse(**result)


@router.delete("/{name}", status_code=204)
async def drop_database(name: str, _: None = Depends(require_token)):
    try:
        await pg_svc.drop_database(name)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
