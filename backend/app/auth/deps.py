"""FastAPI dependencies for admin authentication / authorization."""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.supabase import SupabaseAuthError, verify_supabase_access_token
from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.models.admin_user import AdminUser

_bearer = HTTPBearer(auto_error=False)


def require_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminUser:
    """
    Require a valid Supabase access token belonging to an active admin_users row.

    401 — missing / invalid / expired token
    403 — authenticated but not an active admin
    """
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials.strip()
    try:
        identity = verify_supabase_access_token(token, settings)
    except SupabaseAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        auth_user_id = uuid.UUID(str(identity["id"]))
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc

    admin = db.scalar(select(AdminUser).where(AdminUser.auth_user_id == auth_user_id))
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return admin
