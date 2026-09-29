from fastapi import FastAPI

from app import models as models  # noqa: F401
from app.routers.auth import router as auth_router
from app.routers.matches import router as matches_router
from app.routers.teams import router as teams_router
from app.routers.tournaments import router as tournaments_router

app = FastAPI(title="Mini-Football Management API")
app.include_router(auth_router)
app.include_router(tournaments_router)
app.include_router(teams_router)
app.include_router(matches_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
