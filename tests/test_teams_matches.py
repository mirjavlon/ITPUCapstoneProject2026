from pathlib import Path
from tempfile import TemporaryDirectory

import bcrypt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.player import Player
from app.models.tournament import Tournament
from app.models.user import AccountType, User


def password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def test_team_and_match_lifecycle():
    with TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'teams-matches.db'}")
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(engine)

        def override_get_db():
            with session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with session_factory() as db:
                organizer = User(
                    username="organizer", email="organizer@example.com", hashed_password=password_hash("Secret123"),
                    account_type=AccountType.ORGANIZER,
                )
                manager = User(
                    username="manager", email="manager@example.com", hashed_password=password_hash("Secret123"),
                    account_type=AccountType.MANAGER,
                )
                db.add_all([organizer, manager])
                db.flush()
                db.add(Tournament(name="Campus Cup", slug="campus-cup", created_by_id=organizer.id))
                db.commit()

            with TestClient(app) as client:
                login = client.post("/auth/login", data={"username": "organizer", "password": "Secret123"})
                assert login.status_code == 200
                headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

                home = client.post("/api/teams/", headers=headers, json={
                    "tournament_id": 1, "name": "Home FC", "manager_id": 2, "contact_info": "private",
                })
                away = client.post("/api/teams/", headers=headers, json={"tournament_id": 1, "name": "Away FC"})
                assert home.status_code == 201, home.text
                assert away.status_code == 201, away.text
                assert client.get(f"/api/teams/{home.json()['id']}").status_code == 404  # tournament is draft

                fixture = client.post("/api/matches/", headers=headers, json={
                    "tournament_id": 1, "home_team_id": home.json()["id"], "away_team_id": away.json()["id"],
                    "match_date": "2026-10-01T10:00:00+05:00", "venue": "Pitch 1",
                })
                assert fixture.status_code == 201, fixture.text

                completed = client.put(f"/api/matches/{fixture.json()['id']}/score", headers=headers, json={
                    "home_score": 1, "away_score": 0, "expected_version": fixture.json()["version"],
                })
                assert completed.status_code == 200, completed.text

                with session_factory() as db:
                    db.add(Player(name="Scorer", team_id=home.json()["id"]))
                    db.commit()
                goal = client.post(f"/api/matches/{fixture.json()['id']}/goals", headers=headers, json={
                    "scorer_id": 1, "minute": 12,
                })
                assert goal.status_code == 201, goal.text
                assert client.post(f"/api/matches/{fixture.json()['id']}/goals", headers=headers, json={
                    "scorer_id": 1, "minute": 20,
                }).status_code == 409

                corrected = client.put(f"/api/matches/{fixture.json()['id']}/score", headers=headers, json={
                    "home_score": 0, "away_score": 0, "expected_version": completed.json()["version"], "reason": "Review",
                })
                assert corrected.status_code == 409  # remove attribution before lowering the official score
                revisions = client.get(f"/api/matches/{fixture.json()['id']}/revisions", headers=headers)
                assert revisions.status_code == 200
                assert len(revisions.json()) == 1
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


def test_organizer_can_create_publish_and_read_a_tournament():
    with TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'tournaments.db'}")
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(engine)

        def override_get_db():
            with session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                registered = client.post("/auth/register", json={
                    "username": "cupowner", "email": "cupowner@example.com", "password": "Secret123",
                    "account_type": "organizer",
                })
                assert registered.status_code == 201, registered.text
                token = client.post("/auth/login", data={"username": "cupowner", "password": "Secret123"})
                headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
                created = client.post("/api/tournaments/", headers=headers, json={
                    "name": "Autumn Cup", "slug": "autumn-cup", "win_points": 3,
                })
                assert created.status_code == 201, created.text
                assert client.get("/api/tournaments/").json() == []
                published = client.patch(
                    f"/api/tournaments/{created.json()['id']}/status", headers=headers, json={"status": "published"}
                )
                assert published.status_code == 200, published.text
                assert [row["slug"] for row in client.get("/api/tournaments/").json()] == ["autumn-cup"]
        finally:
            app.dependency_overrides.clear()
            engine.dispose()
