from fastapi import APIRouter
from api.models.flavor import Flavor, BUILTIN_FLAVORS

router = APIRouter(prefix="/api/flavors", tags=["flavors"])


@router.get("", response_model=list[Flavor])
def list_flavors():
    """List available VM resource profiles."""
    return BUILTIN_FLAVORS
