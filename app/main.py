from fastapi import FastAPI

from app.routers.auth import router as auth_router


app = FastAPI(title="Mini-Football Management API")
app.include_router(auth_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
