from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base
from app.dependencies import get_db
from app.main import app
from app.models.users import User


def password_hash(password: str) -> str:
    import bcrypt

    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def test_login_returns_a_bearer_token_for_valid_credentials():
    with TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'auth.db'}")
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(engine)

        def override_get_db():
            with session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with session_factory() as db:
                db.add(User(username="player", hashed_password=password_hash("Secret123")))
                db.commit()

            with TestClient(app) as client:
                response = client.post("/auth/login", data={"username": "player", "password": "Secret123"})

            assert response.status_code == 200
            body = response.json()
            assert body["token_type"] == "bearer"
            assert jwt.decode(body["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])["sub"] == "1"
        finally:
            app.dependency_overrides.clear()
            engine.dispose()


def test_login_rejects_invalid_credentials():
    with TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite:///{Path(directory) / 'auth.db'}")
        session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
        Base.metadata.create_all(engine)

        def override_get_db():
            with session_factory() as db:
                yield db

        app.dependency_overrides[get_db] = override_get_db
        try:
            with TestClient(app) as client:
                response = client.post("/auth/login", data={"username": "unknown", "password": "wrong"})
        finally:
            app.dependency_overrides.clear()
            engine.dispose()

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
