"""Tests for service modules — standings and player stats."""

import pytest
from datetime import datetime, timezone

from app.models.match import GoalEvent, Match
from app.services.standings import calculate_standings
from app.services.player_stats import get_player_stats, calculate_top_scorers
from tests.conftest import (
    make_match,
    make_organizer,
    make_player,
    make_team,
    make_tournament,
)


# =====================================================================
# Standings calculation
# =====================================================================

class TestStandings:
    def test_empty_standings(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        make_team(db_session, tournament_id=t.id, name="Team A")
        standings = calculate_standings(db_session, t)
        assert len(standings) == 1
        assert standings[0]["played"] == 0
        assert standings[0]["points"] == 0

    def test_standings_after_home_win(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id, win_points=3, draw_points=1, loss_points=0)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        make_match(
            db_session, tournament_id=t.id,
            home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=2, away_score=0,
        )
        standings = calculate_standings(db_session, t)
        home_row = next(s for s in standings if s["team_id"] == home.id)
        away_row = next(s for s in standings if s["team_id"] == away.id)
        assert home_row["wins"] == 1
        assert home_row["points"] == 3
        assert home_row["goals_for"] == 2
        assert home_row["goal_difference"] == 2
        assert away_row["losses"] == 1
        assert away_row["points"] == 0

    def test_standings_draw(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        make_match(
            db_session, tournament_id=t.id,
            home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=1,
        )
        standings = calculate_standings(db_session, t)
        for row in standings:
            assert row["draws"] == 1
            assert row["points"] == 1

    def test_scheduled_matches_ignored(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        standings = calculate_standings(db_session, t)
        assert all(s["played"] == 0 for s in standings)

    def test_standings_ordered_by_points_then_gd(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        a = make_team(db_session, tournament_id=t.id, name="Alpha")
        b = make_team(db_session, tournament_id=t.id, name="Bravo")
        c = make_team(db_session, tournament_id=t.id, name="Charlie")
        # Alpha beats Bravo 3-0
        make_match(db_session, tournament_id=t.id, home_team_id=a.id, away_team_id=b.id,
                   match_date="2026-10-01T10:00:00+05:00", status="completed", home_score=3, away_score=0)
        # Bravo beats Charlie 2-1
        make_match(db_session, tournament_id=t.id, home_team_id=b.id, away_team_id=c.id,
                   match_date="2026-10-02T10:00:00+05:00", status="completed", home_score=2, away_score=1)
        standings = calculate_standings(db_session, t)
        names = [s["team_name"] for s in standings]
        # Alpha: 3pts GD+3, Bravo: 3pts GD-1, Charlie: 0pts
        assert names[0] == "Alpha"
        assert names[1] == "Bravo"


# =====================================================================
# Player stats
# =====================================================================

class TestPlayerStats:
    def test_get_player_stats_no_goals(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        p = make_player(db_session, team_id=team.id, name="Bench")
        stats = get_player_stats(db_session, p)
        assert stats["goals"] == 0
        assert stats["assists"] == 0

    def test_get_player_stats_with_goals(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        scorer = make_player(db_session, team_id=home.id, name="Striker")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=1, away_score=0,
        )
        db_session.add(GoalEvent(
            match_id=m.id, team_id=home.id, scorer_id=scorer.id, minute=30,
            created_at=datetime.now(timezone.utc),
        ))
        db_session.commit()
        stats = get_player_stats(db_session, scorer)
        assert stats["goals"] == 1
        assert stats["assists"] == 0


# =====================================================================
# Top scorers
# =====================================================================

class TestTopScorers:
    def test_top_scorers_empty_tournament(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        result = calculate_top_scorers(db_session, t)
        assert result == []

    def test_top_scorers_ranking(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        p1 = make_player(db_session, team_id=home.id, name="Top Scorer")
        p2 = make_player(db_session, team_id=away.id, name="Runner Up")
        m = make_match(
            db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id,
            status="completed", home_score=2, away_score=1,
        )
        now = datetime.now(timezone.utc)
        db_session.add_all([
            GoalEvent(match_id=m.id, team_id=home.id, scorer_id=p1.id, minute=10, created_at=now),
            GoalEvent(match_id=m.id, team_id=home.id, scorer_id=p1.id, minute=30, created_at=now),
            GoalEvent(match_id=m.id, team_id=away.id, scorer_id=p2.id, minute=45, created_at=now),
        ])
        db_session.commit()
        result = calculate_top_scorers(db_session, t)
        assert len(result) == 2
        assert result[0]["player_name"] == "Top Scorer"
        assert result[0]["goals"] == 2
        assert result[0]["position"] == 1
        assert result[1]["player_name"] == "Runner Up"
        assert result[1]["goals"] == 1
