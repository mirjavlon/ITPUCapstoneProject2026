"""Shared fixtures for the Mini-Football Management API test suite."""

from pathlib import Path
from tempfile import TemporaryDirectory

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.match import GoalEvent, Match, MatchResultRevision
from app.models.player import Player
from app.models.team import Team
from app.models.tournament import Tournament
from app.models.user import AccountType, User


# ---------------------------------------------------------------------------
# Database & client fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_env():
    """Yield (engine, session_factory) backed by a temporary SQLite file."""
    with TemporaryDirectory() as directory:
        db_path = Path(directory) / "test.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        # SQLite ignores FK constraints by default — enable them.
        @event.listens_for(engine, "connect")
        def _set_sqlite_pragma(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(engine)
        yield engine, session_factory
        engine.dispose()


@pytest.fixture()
def db_session(db_env):
    """Yield a SQLAlchemy session that is rolled back after each test."""
    _engine, session_factory = db_env
    with session_factory() as session:
        yield session


@pytest.fixture()
def client(db_env):
    """Yield a FastAPI TestClient with the DB dependency overridden."""
    _engine, session_factory = db_env

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: password hashing
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------

def make_user(
    db_session,
    *,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "Secret123",
    account_type: AccountType = AccountType.MANAGER,
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        account_type=account_type,
        is_active=is_active,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def make_organizer(db_session, *, username="organizer", email="organizer@example.com", **kw) -> User:
    return make_user(db_session, username=username, email=email, account_type=AccountType.ORGANIZER, **kw)


def make_manager(db_session, *, username="manager", email="manager@example.com", **kw) -> User:
    return make_user(db_session, username=username, email=email, account_type=AccountType.MANAGER, **kw)


def login(client, username: str = "organizer", password: str = "Secret123") -> dict:
    """Login and return Authorization headers."""
    resp = client.post("/auth/login", data={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def make_tournament(
    db_session,
    *,
    name: str = "Test Cup",
    slug: str = "test-cup",
    status: str = "draft",
    created_by_id: int,
    win_points: int = 3,
    draw_points: int = 1,
    loss_points: int = 0,
) -> Tournament:
    t = Tournament(
        name=name,
        slug=slug,
        status=status,
        created_by_id=created_by_id,
        win_points=win_points,
        draw_points=draw_points,
        loss_points=loss_points,
    )
    db_session.add(t)
    db_session.commit()
    db_session.refresh(t)
    return t


def make_team(
    db_session,
    *,
    tournament_id: int,
    name: str = "Team A",
    manager_id: int | None = None,
) -> Team:
    team = Team(tournament_id=tournament_id, name=name, manager_id=manager_id)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def make_player(db_session, *, team_id: int, name: str = "Player 1", jersey_number: int | None = None) -> Player:
    p = Player(team_id=team_id, name=name, jersey_number=jersey_number)
    db_session.add(p)
    db_session.commit()
    db_session.refresh(p)
    return p


def make_match(
    db_session,
    *,
    tournament_id: int,
    home_team_id: int,
    away_team_id: int,
    match_date: str = "2026-10-01T10:00:00+05:00",
    venue: str | None = "Pitch 1",
    status: str = "scheduled",
    home_score: int | None = None,
    away_score: int | None = None,
) -> Match:
    from datetime import datetime
    m = Match(
        tournament_id=tournament_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        match_date=datetime.fromisoformat(match_date),
        venue=venue,
        status=status,
        home_score=home_score,
        away_score=away_score,
    )
    db_session.add(m)
    db_session.commit()
    db_session.refresh(m)
    return m
