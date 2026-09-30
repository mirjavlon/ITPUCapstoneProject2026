"""API tests for /api/matches endpoints — scheduling, scoring, goal events, and revisions."""

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


def _setup_tournament(db_session):
    """Create an organizer with a tournament and two teams."""
    org = make_organizer(db_session)
    t = make_tournament(db_session, created_by_id=org.id)
    home = make_team(db_session, tournament_id=t.id, name="Home FC")
    away = make_team(db_session, tournament_id=t.id, name="Away FC")
    return org, t, home, away


# =====================================================================
# POST /api/matches/
# =====================================================================

class TestCreateMatch:
    def test_organizer_creates_match(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        headers = login(client)
        resp = client.post("/api/matches/", headers=headers, json={
            "tournament_id": t.id,
            "home_team_id": home.id,
            "away_team_id": away.id,
            "match_date": "2026-10-01T10:00:00+05:00",
            "venue": "Pitch 1",
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "scheduled"
        assert body["version"] == 1

    def test_manager_cannot_create_match(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        make_manager(db_session)
        headers = login(client, "manager")
        resp = client.post("/api/matches/", headers=headers, json={
            "tournament_id": t.id,
            "home_team_id": home.id,
            "away_team_id": away.id,
            "match_date": "2026-10-01T10:00:00+05:00",
        })
        assert resp.status_code == 403

    def test_same_team_both_sides_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        headers = login(client)
        resp = client.post("/api/matches/", headers=headers, json={
            "tournament_id": t.id,
            "home_team_id": home.id,
            "away_team_id": home.id,
            "match_date": "2026-10-01T10:00:00+05:00",
        })
        assert resp.status_code == 422

    def test_match_date_without_timezone_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        headers = login(client)
        resp = client.post("/api/matches/", headers=headers, json={
            "tournament_id": t.id,
            "home_team_id": home.id,
            "away_team_id": away.id,
            "match_date": "2026-10-01T10:00:00",
        })
        assert resp.status_code == 422


# =====================================================================
# GET /api/matches/
# =====================================================================

class TestListMatches:
    def test_list_matches_in_published_tournament(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        resp = client.get("/api/matches/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_list_matches_filter_by_status(self, client, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, status="published", created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        resp = client.get("/api/matches/?status=completed")
        assert resp.status_code == 200
        assert len(resp.json()) == 0


# =====================================================================
# PUT /api/matches/{id}/score
# =====================================================================

class TestRecordScore:
    def test_record_first_score(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        resp = client.put(f"/api/matches/{m.id}/score", headers=headers, json={
            "home_score": 2, "away_score": 1, "expected_version": m.version,
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["home_score"] == 2
        assert body["away_score"] == 1
        assert body["status"] == "completed"
        assert body["version"] == m.version + 1

    def test_score_correction_requires_reason(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        headers = login(client)
        resp = client.put(f"/api/matches/{m.id}/score", headers=headers, json={
            "home_score": 2, "away_score": 0, "expected_version": m.version,
        })
        assert resp.status_code == 422
        assert "reason" in resp.json()["detail"].lower()

    def test_version_conflict_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        resp = client.put(f"/api/matches/{m.id}/score", headers=headers, json={
            "home_score": 1, "away_score": 0, "expected_version": 999,
        })
        assert resp.status_code == 409


# =====================================================================
# POST /{id}/withdraw-result
# =====================================================================

class TestWithdrawResult:
    def test_withdraw_completed_match(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        headers = login(client)
        resp = client.post(f"/api/matches/{m.id}/withdraw-result", headers=headers, json={
            "expected_version": m.version, "reason": "Error in reporting",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "scheduled"
        assert body["home_score"] is None
        assert body["away_score"] is None

    def test_withdraw_scheduled_match_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        resp = client.post(f"/api/matches/{m.id}/withdraw-result", headers=headers, json={
            "expected_version": m.version, "reason": "Mistake",
        })
        assert resp.status_code == 409


# =====================================================================
# Goal events
# =====================================================================

class TestGoalEvents:
    def test_add_goal_event(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        scorer = make_player(db_session, team_id=home.id, name="Striker")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        headers = login(client)
        resp = client.post(f"/api/matches/{m.id}/goals", headers=headers, json={
            "scorer_id": scorer.id, "minute": 15,
        })
        assert resp.status_code == 201
        assert resp.json()["scorer_name"] == "Striker"
        assert resp.json()["minute"] == 15

    def test_goal_event_on_scheduled_match_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        scorer = make_player(db_session, team_id=home.id, name="Striker")
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        resp = client.post(f"/api/matches/{m.id}/goals", headers=headers, json={
            "scorer_id": scorer.id, "minute": 15,
        })
        assert resp.status_code == 409

    def test_goal_exceeding_score_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        scorer = make_player(db_session, team_id=home.id, name="Striker")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=0, away_score=1,  # home scored 0
        )
        headers = login(client)
        resp = client.post(f"/api/matches/{m.id}/goals", headers=headers, json={
            "scorer_id": scorer.id, "minute": 15,
        })
        assert resp.status_code == 409

    def test_scorer_must_belong_to_match_teams(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        # Create a player on a third team (not in this match)
        third = make_team(db_session, tournament_id=t.id, name="Third")
        outsider = make_player(db_session, team_id=third.id, name="Outsider")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        headers = login(client)
        resp = client.post(f"/api/matches/{m.id}/goals", headers=headers, json={
            "scorer_id": outsider.id, "minute": 10,
        })
        assert resp.status_code == 422

    def test_delete_goal_event(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        scorer = make_player(db_session, team_id=home.id, name="Striker")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        headers = login(client)
        goal = client.post(f"/api/matches/{m.id}/goals", headers=headers, json={
            "scorer_id": scorer.id, "minute": 15,
        })
        assert goal.status_code == 201
        resp = client.delete(f"/api/matches/{m.id}/goals/{goal.json()['id']}", headers=headers)
        assert resp.status_code == 204


# =====================================================================
# DELETE /api/matches/{id}
# =====================================================================

class TestDeleteMatch:
    def test_delete_scheduled_match(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        resp = client.delete(f"/api/matches/{m.id}", headers=headers)
        assert resp.status_code == 204

    def test_delete_completed_match_rejected(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        headers = login(client)
        resp = client.delete(f"/api/matches/{m.id}", headers=headers)
        assert resp.status_code == 409


# =====================================================================
# Revisions
# =====================================================================

class TestRevisions:
    def test_list_revisions_after_scoring(self, client, db_session):
        org, t, home, away = _setup_tournament(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        headers = login(client)
        client.put(f"/api/matches/{m.id}/score", headers=headers, json={
            "home_score": 1, "away_score": 0, "expected_version": m.version,
        })
        resp = client.get(f"/api/matches/{m.id}/revisions", headers=headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["new_home_score"] == 1
