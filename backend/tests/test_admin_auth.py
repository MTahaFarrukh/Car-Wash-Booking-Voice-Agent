"""Phase 10A — admin authentication / authorization tests."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth.supabase import SupabaseAuthError, verify_supabase_access_token
from app.core.config import Settings
from app.main import app
from app.models.admin_user import AdminUser
from tests.conftest import requires_database

client = TestClient(app)


def _settings(**overrides) -> Settings:
    base = {
        "supabase_url": "https://example.supabase.co",
        "supabase_anon_key": "anon-test-key",
    }
    base.update(overrides)
    return Settings(**base)


class TestVerifySupabaseToken:
    def test_missing_config(self):
        try:
            verify_supabase_access_token("tok", Settings(supabase_url="", supabase_anon_key=""))
            assert False, "expected SupabaseAuthError"
        except SupabaseAuthError as exc:
            assert "not configured" in str(exc).lower()

    def test_invalid_token(self, httpx_mock=None):
        with patch("app.auth.supabase.httpx.Client") as client_cls:
            instance = client_cls.return_value.__enter__.return_value
            response = instance.get.return_value
            response.status_code = 401
            response.json.return_value = {"message": "invalid"}
            try:
                verify_supabase_access_token("bad", _settings())
                assert False
            except SupabaseAuthError as exc:
                assert "invalid" in str(exc).lower() or "expired" in str(exc).lower()


@requires_database
class TestAdminAuthEndpoints:
    def test_admin_requires_bearer(self):
        resp = client.get("/api/admin/status")
        assert resp.status_code == 401

    def test_admin_rejects_invalid_token(self):
        with patch(
            "app.auth.deps.verify_supabase_access_token",
            side_effect=SupabaseAuthError("Invalid or expired token"),
        ):
            resp = client.get(
                "/api/admin/status",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 401

    def test_authenticated_non_admin_forbidden(self, db_session):
        auth_id = uuid.uuid4()

        def _fake_verify(token: str, settings):
            return {"id": str(auth_id), "email": "user@example.com"}

        with patch("app.auth.deps.verify_supabase_access_token", side_effect=_fake_verify):
            resp = client.get(
                "/api/admin/status",
                headers={"Authorization": "Bearer user-token"},
            )
        assert resp.status_code == 403

    def test_active_admin_allowed(self, db_session):
        auth_id = uuid.uuid4()
        email = f"admin-{uuid.uuid4().hex[:8]}@sparkle.test"
        db_session.add(
            AdminUser(auth_user_id=auth_id, email=email, role="ADMIN", is_active=True)
        )
        db_session.commit()

        def _fake_verify(token: str, settings):
            return {"id": str(auth_id), "email": email}

        with patch("app.auth.deps.verify_supabase_access_token", side_effect=_fake_verify):
            resp = client.get(
                "/api/admin/status",
                headers={"Authorization": "Bearer admin-token"},
            )
            me = client.get(
                "/api/admin/me",
                headers={"Authorization": "Bearer admin-token"},
            )
        assert resp.status_code == 200
        assert "database" in resp.json()
        assert me.status_code == 200
        assert me.json()["email"] == email

    def test_inactive_admin_forbidden(self, db_session):
        auth_id = uuid.uuid4()
        email = f"inactive-{uuid.uuid4().hex[:8]}@sparkle.test"
        db_session.add(
            AdminUser(auth_user_id=auth_id, email=email, role="ADMIN", is_active=False)
        )
        db_session.commit()

        def _fake_verify(token: str, settings):
            return {"id": str(auth_id), "email": email}

        with patch("app.auth.deps.verify_supabase_access_token", side_effect=_fake_verify):
            resp = client.get(
                "/api/admin/status",
                headers={"Authorization": "Bearer admin-token"},
            )
        assert resp.status_code == 403

    def test_public_health_unauthenticated(self):
        assert client.get("/health").status_code == 200
        assert client.get("/api/services").status_code == 200
