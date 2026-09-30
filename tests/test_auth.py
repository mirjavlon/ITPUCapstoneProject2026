"""API tests for the /auth endpoints."""

import pytest
from jose import jwt

from app.config import settings
from app.models.user import AccountType
from tests.conftest import hash_password, login, make_manager, make_organizer, make_user


# =====================================================================
# POST /auth/register
# =====================================================================

class TestRegister:
    def test_register_organizer(self, client, db_session):
        resp = client.post("/auth/register", json={
            "username": "neworg",
            "email": "neworg@example.com",
            "password": "Secret123",
            "account_type": "organizer",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "neworg"
        assert body["account_type"] == "organizer"
        assert body["is_active"] is True
        assert "hashed_password" not in body

    def test_register_manager(self, client, db_session):
        resp = client.post("/auth/register", json={
            "username": "newmgr",
            "email": "newmgr@example.com",
            "password": "Secret123",
            "account_type": "manager",
        })
        assert resp.status_code == 201
        assert resp.json()["account_type"] == "manager"

    def test_register_duplicate_username_rejected(self, client, db_session):
        make_manager(db_session, username="taken")
        resp = client.post("/auth/register", json={
            "username": "taken",
            "email": "new@example.com",
            "password": "Secret123",
            "account_type": "manager",
        })
        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"]

    def test_register_duplicate_email_rejected(self, client, db_session):
        make_manager(db_session, email="taken@example.com")
        resp = client.post("/auth/register", json={
            "username": "newuser",
            "email": "taken@example.com",
            "password": "Secret123",
            "account_type": "manager",
        })
        assert resp.status_code == 400

    def test_register_short_password_rejected(self, client, db_session):
        resp = client.post("/auth/register", json={
            "username": "short",
            "email": "short@example.com",
            "password": "abc",
            "account_type": "manager",
        })
        assert resp.status_code == 422

    def test_register_invalid_username_rejected(self, client, db_session):
        resp = client.post("/auth/register", json={
            "username": "no spaces!",
            "email": "valid@example.com",
            "password": "Secret123",
            "account_type": "manager",
        })
        assert resp.status_code == 422

    def test_register_extra_fields_rejected(self, client, db_session):
        resp = client.post("/auth/register", json={
            "username": "extra",
            "email": "extra@example.com",
            "password": "Secret123",
            "account_type": "manager",
            "is_admin": True,
        })
        assert resp.status_code == 422

    def test_register_missing_account_type_rejected(self, client, db_session):
        resp = client.post("/auth/register", json={
            "username": "notype",
            "email": "notype@example.com",
            "password": "Secret123",
        })
        assert resp.status_code == 422


# =====================================================================
# POST /auth/login
# =====================================================================

class TestLogin:
    def test_login_returns_bearer_token(self, client, db_session):
        make_manager(db_session, username="player", email="player@example.com")
        resp = client.post("/auth/login", data={"username": "player", "password": "Secret123"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        payload = jwt.decode(body["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        assert payload["sub"] is not None

    def test_login_wrong_password(self, client, db_session):
        make_manager(db_session, username="player", email="player@example.com")
        resp = client.post("/auth/login", data={"username": "player", "password": "WrongPass"})
        assert resp.status_code == 401
        assert resp.headers["www-authenticate"] == "Bearer"

    def test_login_nonexistent_user(self, client, db_session):
        resp = client.post("/auth/login", data={"username": "ghost", "password": "Secret123"})
        assert resp.status_code == 401

    def test_login_inactive_user(self, client, db_session):
        make_manager(db_session, username="inactive", email="inactive@example.com", is_active=False)
        resp = client.post("/auth/login", data={"username": "inactive", "password": "Secret123"})
        assert resp.status_code == 403


# =====================================================================
# GET /auth/me
# =====================================================================

class TestMe:
    def test_me_returns_current_user(self, client, db_session):
        make_organizer(db_session, username="orguser", email="org@example.com")
        headers = login(client, "orguser")
        resp = client.get("/auth/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "orguser"
        assert resp.json()["account_type"] == "organizer"

    def test_me_unauthenticated(self, client, db_session):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client, db_session):
        resp = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401
