from fastapi import FastAPI

from app.database import Base, engine
from app.routers.auth import router as auth_router


# Automatically create tables (if they don't exist)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mini-Football Management API")
app.include_router(auth_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
