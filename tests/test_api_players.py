"""API tests for /api/players endpoints."""

import pytest

from tests.conftest import (
    login,
    make_manager,
    make_match,
    make_organizer,
    make_player,
    make_team,
    make_tournament,
)
from app.models.match import GoalEvent
from datetime import datetime, timezone


# =====================================================================
# POST /api/players/
# =====================================================================

class TestCreatePlayer:
    def test_organizer_creates_player(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        headers = login(client)
        resp = client.post("/api/players/", headers=headers, json={
            "team_id": team.id, "name": "Messi", "jersey_number": 10, "position": "FWD",
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "Messi"
        assert resp.json()["jersey_number"] == 10

    def test_manager_creates_player_on_own_team(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, manager_id=mgr.id)
        headers = login(client, "manager")
        resp = client.post("/api/players/", headers=headers, json={
            "team_id": team.id, "name": "Player",
        })
        assert resp.status_code == 201

    def test_manager_cannot_add_player_to_other_team(self, client, db_session):
        org = make_organizer(db_session)
        mgr = make_manager(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)  # no manager assigned
        headers = login(client, "manager")
        resp = client.post("/api/players/", headers=headers, json={
            "team_id": team.id, "name": "Intruder",
        })
        assert resp.status_code == 403

    def test_duplicate_jersey_rejected(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        make_player(db_session, team_id=team.id, name="A", jersey_number=7)
        headers = login(client)
        resp = client.post("/api/players/", headers=headers, json={
            "team_id": team.id, "name": "B", "jersey_number": 7,
        })
        assert resp.status_code in (409, 422)


# =====================================================================
# GET /api/players/
# =====================================================================

class TestListPlayers:
    def test_list_players_in_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        make_player(db_session, team_id=team.id, name="Player 1")
        make_player(db_session, team_id=team.id, name="Player 2")
        resp = client.get(f"/api/players/?team_id={team.id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 2


# =====================================================================
# GET /api/players/{id}
# =====================================================================

class TestGetPlayer:
    def test_get_player_in_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        p = make_player(db_session, team_id=team.id, name="Star")
        resp = client.get(f"/api/players/{p.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Star"

    def test_get_nonexistent_player(self, client, db_session):
        resp = client.get("/api/players/9999")
        assert resp.status_code == 404


# =====================================================================
# PATCH /api/players/{id}
# =====================================================================

class TestUpdatePlayer:
    def test_organizer_updates_player(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        p = make_player(db_session, team_id=team.id, name="Old", jersey_number=5)
        headers = login(client)
        resp = client.patch(f"/api/players/{p.id}", headers=headers, json={
            "name": "New Name", "jersey_number": 99,
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "New Name"
        assert resp.json()["jersey_number"] == 99


# =====================================================================
# DELETE /api/players/{id}
# =====================================================================

class TestDeletePlayer:
    def test_delete_player_without_stats(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        p = make_player(db_session, team_id=team.id, name="Bench")
        headers = login(client)
        resp = client.delete(f"/api/players/{p.id}", headers=headers)
        assert resp.status_code == 204

    def test_delete_player_with_goals_rejected(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        scorer = make_player(db_session, team_id=home.id, name="Scorer")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        goal = GoalEvent(
            match_id=m.id, team_id=home.id, scorer_id=scorer.id, minute=10,
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(goal)
        db_session.commit()
        headers = login(client)
        resp = client.delete(f"/api/players/{scorer.id}", headers=headers)
        assert resp.status_code == 409
