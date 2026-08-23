"""Supabase Auth access-token verification (server-side only)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


class SupabaseAuthError(Exception):
    """Raised when a Supabase access token cannot be verified."""


def verify_supabase_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """
    Validate a Supabase user access token via Auth API.

    Uses SUPABASE_URL + SUPABASE_ANON_KEY only (never trusts client-supplied identity).
    """
    base = (settings.supabase_url or "").strip().rstrip("/")
    anon = (settings.supabase_anon_key or "").strip()
    if not base or not anon:
        raise SupabaseAuthError("Supabase Auth is not configured on the server")

    url = f"{base}/auth/v1/user"
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": anon,
                },
            )
    except httpx.HTTPError as exc:
        logger.warning("supabase_auth_unreachable error=%s", type(exc).__name__)
        raise SupabaseAuthError("Auth provider is unavailable") from exc

    if response.status_code in {401, 403}:
        raise SupabaseAuthError("Invalid or expired token")
    if response.status_code >= 400:
        logger.warning("supabase_auth_error status=%s", response.status_code)
        raise SupabaseAuthError("Token verification failed")

    try:
        body = response.json()
    except ValueError as exc:
        raise SupabaseAuthError("Malformed auth response") from exc

    user_id = body.get("id")
    email = body.get("email")
    if not user_id:
        raise SupabaseAuthError("Token payload missing user id")
    return {"id": str(user_id), "email": email}
