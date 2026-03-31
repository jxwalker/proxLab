"""
Shared authentication dependency for all API routers.
Usage: `_: None = Depends(require_token)`
"""
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.config import settings

_bearer = HTTPBearer()


def require_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(_bearer)],
) -> None:
    if credentials.credentials != settings.proxlab_api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")
