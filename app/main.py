import secrets
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, matches, players, standings, teams, tournaments, web

# Importing the model package registers every table for Alembic and tests.
from app import models as models  # noqa: F401

app = FastAPI(
    title=settings.APP_NAME,
    description="API for managing mini-football tournaments",
    version="2.0.0",
)
app.state.timezone = settings.APP_TIMEZONE

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=settings.ENVIRONMENT == "production",
    same_site="lax",
)


@app.middleware("http")
async def provide_csrf_cookie(request: Request, call_next):
    csrf_token = request.cookies.get("csrf_token") or secrets.token_urlsafe(32)
    request.state.csrf_token = csrf_token
    response = await call_next(request)
    if "csrf_token" not in request.cookies:
        response.set_cookie(
            "csrf_token",
            csrf_token,
            httponly=True,
            secure=settings.ENVIRONMENT == "production",
            samesite="lax",
        )
    return response

app.include_router(auth.router)
app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(matches.router)
app.include_router(standings.router)
app.include_router(web.router)

static_directory = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=static_directory), name="static")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}
