"""API tests for the /api/tournaments endpoints."""

import pytest

from app.models.user import AccountType
from tests.conftest import login, make_manager, make_organizer, make_tournament


# =====================================================================
# POST /api/tournaments/
# =====================================================================

class TestCreateTournament:
    def test_organizer_can_create_tournament(self, client, db_session):
        make_organizer(db_session)
        headers = login(client)
        resp = client.post("/api/tournaments/", headers=headers, json={
            "name": "Autumn Cup",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Autumn Cup"
        assert body["slug"]  # auto-generated
        assert body["status"] == "draft"
        assert body["win_points"] == 3

    def test_manager_cannot_create_tournament(self, client, db_session):
        make_manager(db_session)
        headers = login(client, "manager")
        resp = client.post("/api/tournaments/", headers=headers, json={"name": "Cup"})
        assert resp.status_code == 403

    def test_unauthenticated_cannot_create_tournament(self, client, db_session):
        resp = client.post("/api/tournaments/", json={"name": "Cup"})
        assert resp.status_code == 401

    def test_short_name_rejected(self, client, db_session):
        make_organizer(db_session)
        headers = login(client)
        resp = client.post("/api/tournaments/", headers=headers, json={"name": "X"})
        assert resp.status_code == 422


# =====================================================================
# GET /api/tournaments/
# =====================================================================

class TestListTournaments:
    def test_list_only_published_tournaments(self, client, db_session):
        org = make_organizer(db_session)
        make_tournament(db_session, name="Draft Cup", slug="draft", status="draft", created_by_id=org.id)
        make_tournament(db_session, name="Public Cup", slug="public", status="published", created_by_id=org.id)
        resp = client.get("/api/tournaments/")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "Public Cup" in names
        assert "Draft Cup" not in names


# =====================================================================
# GET /api/tournaments/manage
# =====================================================================

class TestManageTournaments:
    def test_organizer_sees_own_tournaments(self, client, db_session):
        org = make_organizer(db_session)
        make_tournament(db_session, slug="mine", created_by_id=org.id)
        headers = login(client)
        resp = client.get("/api/tournaments/manage", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_manager_forbidden(self, client, db_session):
        make_manager(db_session)
        headers = login(client, "manager")
        resp = client.get("/api/tournaments/manage", headers=headers)
        assert resp.status_code == 403


# =====================================================================
# GET /api/tournaments/{id}
# =====================================================================

class TestGetTournament:
    def test_get_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        resp = client.get(f"/api/tournaments/{t.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test Cup"

    def test_get_draft_tournament_unauthenticated(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="draft", created_by_id=org.id)
        resp = client.get(f"/api/tournaments/{t.id}")
        assert resp.status_code == 404

    def test_get_nonexistent_tournament(self, client, db_session):
        resp = client.get("/api/tournaments/9999")
        assert resp.status_code == 404


# =====================================================================
# PATCH /api/tournaments/{id}
# =====================================================================

class TestUpdateTournament:
    def test_organizer_can_update_own_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        headers = login(client)
        resp = client.patch(f"/api/tournaments/{t.id}", headers=headers, json={"name": "Updated Cup"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Updated Cup"

    def test_organizer_cannot_update_other_tournament(self, client, db_session):
        org1 = make_organizer(db_session, username="org1", email="org1@example.com")
        org2 = make_organizer(db_session, username="org2", email="org2@example.com")
        t = make_tournament(db_session, created_by_id=org1.id)
        headers = login(client, "org2")
        resp = client.patch(f"/api/tournaments/{t.id}", headers=headers, json={"name": "Hijack"})
        assert resp.status_code == 403


# =====================================================================
# PATCH /api/tournaments/{id}/status
# =====================================================================

class TestUpdateTournamentStatus:
    def test_publish_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        headers = login(client)
        resp = client.patch(f"/api/tournaments/{t.id}/status", headers=headers, json={"status": "published"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "published"

    def test_invalid_status_rejected(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        headers = login(client)
        resp = client.patch(f"/api/tournaments/{t.id}/status", headers=headers, json={"status": "invalid"})
        assert resp.status_code == 422
