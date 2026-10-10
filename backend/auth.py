"""
Authentication & Authorization Dependency Layer for SmartPool FastAPI Gateway.
Module: backend/auth.py
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from firebase_config import verify_firebase_token, is_firebase_connected
    from database import db_service
except ImportError:
    from backend.firebase_config import verify_firebase_token, is_firebase_connected
    from backend.database import db_service

logger = logging.getLogger("smartpool.auth")

# HTTPBearer security scheme with auto_error=False for flexible optional auth
bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Optional[Dict[str, Any]]:
    """
    Returns the authenticated user dict if a valid token is provided.
    Returns None if no token is provided or if token verification fails.
    This enables demo modes, integration testing, and public corridor exploration.
    """
    if not credentials or not credentials.credentials:
        return None

    token = credentials.credentials.strip()
    decoded = verify_firebase_token(token)
    if not decoded:
        return None

    uid = decoded.get("uid")
    if not uid:
        return None

    # Load enriched user data from database
    user_record = db_service.get_user(uid)
    role = "passenger"
    if user_record and user_record.get("role"):
        role = user_record["role"]
    elif decoded.get("admin") is True:
        role = "admin"
    elif decoded.get("driver") is True:
        role = "driver"

    return {
        "uid": uid,
        "email": decoded.get("email", ""),
        "name": decoded.get("name") or (user_record.get("fullName") if user_record else "SmartPool User"),
        "role": role,
        "token_claims": decoded
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme)
) -> Dict[str, Any]:
    """
    Strict dependency: Requires a valid Firebase ID token in the Authorization header.
    Raises HTTP 401 if token is missing or invalid.
    """
    user = await get_optional_user(credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Enforces role-based access control.
    Example: Depends(require_role(["admin"])) or Depends(require_role(["driver", "admin"]))
    """
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_role = current_user.get("role", "passenger")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Requires one of the following roles: {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker
