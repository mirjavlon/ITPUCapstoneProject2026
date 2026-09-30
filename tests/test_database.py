"""Database integration tests — model constraints and relationships."""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.match import GoalEvent, Match, MatchResultRevision
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import AccountType, User
from tests.conftest import (
    hash_password,
    make_match,
    make_organizer,
    make_manager,
    make_player,
    make_team,
    make_tournament,
)


# =====================================================================
# User model
# =====================================================================

class TestUserModel:
    def test_create_organizer(self, db_session):
        user = make_organizer(db_session)
        assert user.id is not None
        assert user.account_type == AccountType.ORGANIZER
        assert user.is_organizer is True

    def test_create_manager(self, db_session):
        user = make_manager(db_session)
        assert user.account_type == AccountType.MANAGER
        assert user.is_organizer is False

    def test_duplicate_username_rejected(self, db_session):
        make_organizer(db_session, username="dupe")
        with pytest.raises(IntegrityError):
            make_manager(db_session, username="dupe", email="other@example.com")

    def test_duplicate_email_rejected(self, db_session):
        make_organizer(db_session, email="same@example.com")
        with pytest.raises(IntegrityError):
            make_manager(db_session, username="other", email="same@example.com")

    def test_default_account_type_is_manager(self, db_session):
        user = User(username="bare", email="bare@example.com", hashed_password="x")
        db_session.add(user)
        db_session.commit()
        assert user.account_type == AccountType.MANAGER

    def test_default_is_active_true(self, db_session):
        user = make_manager(db_session)
        assert user.is_active is True


# =====================================================================
# Tournament model
# =====================================================================

class TestTournamentModel:
    def test_create_tournament(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        assert t.id is not None
        assert t.status == "draft"

    def test_duplicate_slug_rejected(self, db_session):
        org = make_organizer(db_session)
        make_tournament(db_session, slug="cup", created_by_id=org.id)
        with pytest.raises(IntegrityError):
            make_tournament(db_session, name="Other Cup", slug="cup", created_by_id=org.id)

    def test_tournament_user_relationship(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        assert t.created_by.id == org.id
        assert t in org.created_tournaments


# =====================================================================
# Team model
# =====================================================================

class TestTeamModel:
    def test_create_team(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id, name="Eagles")
        assert team.id is not None
        assert team.is_active is True

    def test_duplicate_team_name_per_tournament_rejected(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        make_team(db_session, tournament_id=t.id, name="Eagles")
        with pytest.raises(IntegrityError):
            make_team(db_session, tournament_id=t.id, name="Eagles")

    def test_same_name_allowed_in_different_tournaments(self, db_session):
        org = make_organizer(db_session)
        t1 = make_tournament(db_session, slug="cup-1", created_by_id=org.id)
        t2 = make_tournament(db_session, name="Cup 2", slug="cup-2", created_by_id=org.id)
        team1 = make_team(db_session, tournament_id=t1.id, name="Eagles")
        team2 = make_team(db_session, tournament_id=t2.id, name="Eagles")
        assert team1.id != team2.id

    def test_team_cascade_deletes_players(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        make_player(db_session, team_id=team.id, name="Player 1")
        db_session.delete(team)
        db_session.commit()
        assert db_session.query(Player).count() == 0


# =====================================================================
# Player model
# =====================================================================

class TestPlayerModel:
    def test_create_player_with_jersey(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        p = make_player(db_session, team_id=team.id, name="Ronaldo", jersey_number=7)
        assert p.jersey_number == 7

    def test_duplicate_jersey_on_same_team_rejected(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        team = make_team(db_session, tournament_id=t.id)
        make_player(db_session, team_id=team.id, name="Player A", jersey_number=10)
        with pytest.raises(IntegrityError):
            make_player(db_session, team_id=team.id, name="Player B", jersey_number=10)


# =====================================================================
# Match model
# =====================================================================

class TestMatchModel:
    def _setup(self, db_session):
        org = make_organizer(db_session)
        t = make_tournament(db_session, created_by_id=org.id)
        home = make_team(db_session, tournament_id=t.id, name="Home")
        away = make_team(db_session, tournament_id=t.id, name="Away")
        return t, home, away

    def test_create_match(self, db_session):
        t, home, away = self._setup(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        assert m.status == "scheduled"
        assert m.version == 1

    def test_completed_match_requires_scores(self, db_session):
        t, home, away = self._setup(db_session)
        m = make_match(
            db_session,
            tournament_id=t.id,
            home_team_id=home.id,
            away_team_id=away.id,
            status="completed",
            home_score=2,
            away_score=1,
        )
        assert m.home_score == 2

    def test_match_tournament_relationship(self, db_session):
        t, home, away = self._setup(db_session)
        m = make_match(db_session, tournament_id=t.id, home_team_id=home.id, away_team_id=away.id)
        assert m.tournament.id == t.id
        assert m in t.matches
