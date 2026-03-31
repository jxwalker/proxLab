from fastapi import APIRouter, HTTPException, Depends

from api.auth import require_token
from api.models import StorageCreate, StorageResponse
import api.services.truenas as tn_svc

router = APIRouter(prefix="/api/storage", tags=["storage"])


@router.get("", response_model=list[StorageResponse])
def list_storage(_: None = Depends(require_token)):
    """List all proxlab-managed NAS datasets."""
    datasets = tn_svc.list_datasets()
    return [StorageResponse(**ds) for ds in datasets]


@router.post("", response_model=StorageResponse, status_code=201)
def create_storage(req: StorageCreate, _: None = Depends(require_token)):
    """Allocate a new ZFS dataset on TrueNAS and create an NFS export."""
    try:
        ds = tn_svc.create_dataset(req.name, req.quota_gb)
        tn_svc.create_nfs_export(req.name, req.nfs_allowed_hosts or None)
        return StorageResponse(**ds)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{name}", status_code=204)
def delete_storage(name: str, _: None = Depends(require_token)):
    """Delete a proxlab NAS dataset and its NFS export."""
    try:
        tn_svc.delete_dataset(name)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
