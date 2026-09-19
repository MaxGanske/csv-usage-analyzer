# Report API tests using an isolated in-memory SQLite database.
# The dependency override exercises route behavior without touching production data.
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db_session
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    """Provide an HTTP client connected to a fresh isolated report database."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()
    await engine.dispose()


CSV_CONTENT = (
    b"request_id,service,status_code,latency_ms,tokens_used\n"
    b"req-1,users,200,10.5,4\n"
    b"req-2,users,500,20,6\n"
)


@pytest.mark.asyncio
async def test_create_list_and_get_report(client: httpx.AsyncClient) -> None:
    """A valid upload should create, list, and retrieve one report."""
    response = await client.post(
        "/reports",
        files={"file": ("usage.csv", CSV_CONTENT, "text/csv")},
    )

    assert response.status_code == 201
    report = response.json()
    assert report["request_count"] == 2
    assert report["total_tokens"] == 10
    assert report["average_latency_ms"] == 15.25
    assert report["successful_requests"] == 1
    assert report["failed_requests"] == 1

    list_response = await client.get("/reports")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = await client.get(f"/reports/{report['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == report["id"]


@pytest.mark.asyncio
async def test_create_report_rejects_invalid_csv(client: httpx.AsyncClient) -> None:
    """An upload missing required headers should return a client error."""
    response = await client.post(
        "/reports",
        files={"file": ("usage.csv", b"request_id,service\nreq-1,users\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "Invalid CSV headers" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_report_returns_404_for_unknown_id(client: httpx.AsyncClient) -> None:
    """A report identifier absent from the database should return 404."""
    response = await client.get("/reports/does-not-exist")

    assert response.status_code == 404