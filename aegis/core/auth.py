import os
import secrets
from typing import Optional
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


security = HTTPBearer(auto_error=False)


def get_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """extract api key"""
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return api_key


def verify_api_key(api_key: str = Depends(get_api_key)) -> bool:
    """verify api key"""
    # check against db or env vars
    # use env var check
    valid_api_keys = os.getenv("VALID_API_KEYS", "").split(",")
    valid_api_keys = [key.strip() for key in valid_api_keys if key.strip()]

    if not valid_api_keys:
        # no keys = allow all (dev mode)
        return True

    if api_key not in valid_api_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return True


def generate_api_key() -> str:
    """generate api key"""
    return secrets.token_urlsafe(32)


def require_auth(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """require auth"""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # bearer token auth
    token = credentials.credentials

    # validate jwt token
    # check not empty
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token
