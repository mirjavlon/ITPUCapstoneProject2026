"""Frontend (web router) tests — HTML page rendering and form submissions."""

import pytest

from app.models.user import AccountType
from tests.conftest import (
    login,
    make_manager,
    make_organizer,
    make_player,
    make_team,
    make_tournament,
    make_match,
)


def _web_login(client, username="organizer", password="Secret123"):
    """Login via the web form and return the CSRF token."""
    resp = client.get("/login")
    csrf = resp.cookies.get("csrf_token", "test-csrf")
    client.post("/login", data={
        "username": username, "password": password, "csrf_token": csrf,
    }, follow_redirects=False)
    return csrf


# =====================================================================
# Public pages
# =====================================================================

class TestPublicPages:
    def test_homepage_renders(self, client, db_session):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_login_page_renders(self, client, db_session):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_register_page_renders(self, client, db_session):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_organizer_register_page_renders(self, client, db_session):
        resp = client.get("/register-organizer")
        assert resp.status_code == 200

    def test_published_tournament_detail_renders(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        resp = client.get(f"/tournaments/{t.id}")
        assert resp.status_code == 200


# =====================================================================
# Registration flow
# =====================================================================

class TestWebRegistration:
    def test_web_register_manager(self, client, db_session):
        csrf = client.get("/register").cookies.get("csrf_token", "test-csrf")
        resp = client.post("/register", data={
            "username": "webuser",
            "email": "webuser@example.com",
            "password": "Secret123",
            "csrf_token": csrf,
        }, follow_redirects=False)
        # Should redirect to login or dashboard
        assert resp.status_code == 303

    def test_web_register_organizer(self, client, db_session):
        csrf = client.get("/register-organizer").cookies.get("csrf_token", "test-csrf")
        resp = client.post("/register-organizer", data={
            "username": "weborg",
            "email": "weborg@example.com",
            "password": "Secret123",
            "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303


# =====================================================================
# Login/logout flow
# =====================================================================

class TestWebLogin:
    def test_web_login_valid(self, client, db_session):
        make_organizer(db_session)
        csrf = client.get("/login").cookies.get("csrf_token", "test-csrf")
        resp = client.post("/login", data={
            "username": "organizer", "password": "Secret123", "csrf_token": csrf,
        }, follow_redirects=False)
        assert resp.status_code == 303

    def test_web_login_invalid(self, client, db_session):
        csrf = client.get("/login").cookies.get("csrf_token", "test-csrf")
        resp = client.post("/login", data={
            "username": "nobody", "password": "wrong", "csrf_token": csrf,
        })
        # Web login returns 401 for invalid credentials
        assert resp.status_code == 401

    def test_web_logout(self, client, db_session):
        make_organizer(db_session)
        csrf = _web_login(client)
        resp = client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
        assert resp.status_code == 303


# =====================================================================
# Dashboard pages (require auth)
# =====================================================================

class TestDashboard:
    def test_dashboard_redirects_unauthenticated(self, client, db_session):
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 303
        assert "/login" in resp.headers["location"]

    def test_dashboard_renders_for_organizer(self, client, db_session):
        make_organizer(db_session)
        _web_login(client)
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_tournament_create_page_requires_organizer(self, client, db_session):
        make_manager(db_session)
        _web_login(client, "manager")
        resp = client.get("/dashboard/tournaments/new")
        # Returns 403 for non-organizer users
        assert resp.status_code == 403


# =====================================================================
# Health check
# =====================================================================

class TestHealthCheck:
    def test_health_endpoint(self, client, db_session):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
