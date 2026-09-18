# FastAPI application entry point and minimal health check.
from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine

app = FastAPI(title=settings.app_name)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
async def database_health() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok"}
