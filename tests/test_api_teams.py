"""API tests for the /api/teams endpoints."""

import pytest

from app.models.user import AccountType
from tests.conftest import (
    login,
    make_manager,
    make_match,
    make_organizer,
    make_team,
    make_tournament,
)


# =====================================================================
# POST /api/teams/
# =====================================================================

class TestCreateTeam:
    def test_organizer_creates_team_with_manager(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        headers = login(client)
        resp = client.post("/api/teams/", headers=headers, json={
            "tournament_id": t.id, "name": "Eagles", "manager_id": mgr.id,
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Eagles"
        assert resp.json()["manager_id"] == mgr.id

    def test_manager_creates_team_in_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        headers = login(client, "manager")
        resp = client.post("/api/teams/", headers=headers, json={
            "tournament_id": t.id, "name": "Hawks",
        })
        assert resp.status_code == 201
        assert resp.json()["manager_id"] == mgr.id  # auto-assigned

    def test_duplicate_team_name_in_tournament_rejected(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        make_team(db_session, tournament_id=t.id, name="Eagles")
        headers = login(client)
        resp = client.post("/api/teams/", headers=headers, json={
            "tournament_id": t.id, "name": "Eagles",
        })
        assert resp.status_code == 409

    def test_team_in_nonexistent_tournament_rejected(self, client, db_session):
        make_organizer(db_session)
        headers = login(client)
        resp = client.post("/api/teams/", headers=headers, json={
            "tournament_id": 9999, "name": "Ghost",
        })
        assert resp.status_code == 404

    def test_unauthenticated_cannot_create_team(self, client, db_session):
        resp = client.post("/api/teams/", json={"tournament_id": 1, "name": "Team"})
        assert resp.status_code == 401


# =====================================================================
# GET /api/teams/
# =====================================================================

class TestListTeams:
    def test_list_teams_in_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        make_team(db_session, tournament_id=t.id, name="Team A")
        make_team(db_session, tournament_id=t.id, name="Team B")
        resp = client.get(f"/api/teams/?tournament_id={t.id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_list_teams_hides_draft_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="draft", created_by_id=org.id)
        make_team(db_session, tournament_id=t.id, name="Hidden")
        resp = client.get("/api/teams/")
        assert resp.status_code == 200
        assert len(resp.json()) == 0


# =====================================================================
# GET /api/teams/{id}
# =====================================================================

class TestGetTeam:
    def test_get_team_in_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, name="Eagles")
        resp = client.get(f"/api/teams/{team.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Eagles"
        # Contact info hidden from public
        assert resp.json()["contact_info"] is None

    def test_get_nonexistent_team(self, client, db_session):
        resp = client.get("/api/teams/9999")
        assert resp.status_code == 404


# =====================================================================
# PATCH /api/teams/{id}
# =====================================================================

class TestUpdateTeam:
    def test_organizer_updates_team(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, name="Old Name")
        headers = login(client)
        resp = client.patch(f"/api/teams/{team.id}", headers=headers, json={"name": "New Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"

    def test_manager_updates_own_team(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, name="My Team", manager_id=mgr.id)
        headers = login(client, "manager")
        resp = client.patch(f"/api/teams/{team.id}", headers=headers, json={"name": "Updated"})
        assert resp.status_code == 200

    def test_manager_cannot_update_other_team(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, name="Not Mine")
        headers = login(client, "manager")
        resp = client.patch(f"/api/teams/{team.id}", headers=headers, json={"name": "Hijack"})
        assert resp.status_code == 403

    def test_manager_cannot_change_is_active(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, name="Team", manager_id=mgr.id)
        headers = login(client, "manager")
        resp = client.patch(f"/api/teams/{team.id}", headers=headers, json={"is_active": False})
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True  # ignored for managers


# =====================================================================
# DELETE /api/teams/{id}
# =====================================================================

class TestDeleteTeam:
    def test_delete_team_without_matches(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        headers = login(client)
        resp = client.delete(f"/api/teams/{team.id}", headers=headers)
        assert resp.status_code == 204

    def test_delete_team_with_matches_archives_instead(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        resp = client.delete(f"/api/teams/{home.id}", headers=headers)
        assert resp.status_code == 204
        # Verify team was archived (is_active=False) not deleted
        team_resp = client.get(f"/api/teams/{home.id}", headers=headers)
        assert team_resp.status_code == 200
        assert team_resp.json()["is_active"] is False
