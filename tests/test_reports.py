import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db_session
from app.main import app


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
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
    assert report["failure_rate"] == 0.5
    assert report["service_breakdown"] == {
        "users": {
            "request_count": 2,
            "total_tokens": 10,
            "average_latency_ms": 15.25,
            "failed_requests": 1,
            "failure_rate": 0.5,
        }
    }

    list_response = await client.get("/reports")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = await client.get(f"/reports/{report['id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == report["id"]


@pytest.mark.asyncio
async def test_create_report_rejects_invalid_csv(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/reports",
        files={"file": ("usage.csv", b"request_id,service\nreq-1,users\n", "text/csv")},
    )

    assert response.status_code == 400
    assert "Invalid CSV headers" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_report_returns_404_for_unknown_id(client: httpx.AsyncClient) -> None:
    response = await client.get("/reports/does-not-exist")

    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "latency_ms", "tokens_used", "message"),
    [
        (99, "10", "4", "status_code"),
        (600, "10", "4", "status_code"),
        (200, "10001", "4", "latency_ms"),
        (200, "10", "10001", "tokens_used"),
        (200, "NaN", "4", "latency_ms"),
    ],
)
async def test_create_report_rejects_out_of_range_values(
    client: httpx.AsyncClient,
    status_code: int,
    latency_ms: str,
    tokens_used: str,
    message: str,
) -> None:
    csv_content = (
        "request_id,service,status_code,latency_ms,tokens_used\n"
        f"req-1,users,{status_code},{latency_ms},{tokens_used}\n"
    ).encode()
    response = await client.post(
        "/reports",
        files={"file": ("usage.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 400
    assert message in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_report_accepts_validation_boundaries(client: httpx.AsyncClient) -> None:
    csv_content = (
        b"request_id,service,status_code,latency_ms,tokens_used\n"
        b"req-1,users,100,10000,10000\n"
        b"req-2,users,599,0,0\n"
    )
    response = await client.post(
        "/reports",
        files={"file": ("usage.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_report_rejects_duplicate_request_ids(client: httpx.AsyncClient) -> None:
    csv_content = (
        b"request_id,service,status_code,latency_ms,tokens_used\n"
        b"req-1,users,200,10,4\n"
        b"req-1,users,200,10,4\n"
    )
    response = await client.post(
        "/reports",
        files={"file": ("usage.csv", csv_content, "text/csv")},
    )

    assert response.status_code == 400
    assert "duplicate request_id" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_report_rejects_malformed_rows_and_duplicate_headers(
    client: httpx.AsyncClient,
) -> None:
    malformed_row = (
        b"request_id,service,status_code,latency_ms,tokens_used\n"
        b"req-1,users,200,10,4,unexpected\n"
    )
    duplicate_header = (
        b"request_id,service,status_code,latency_ms,tokens_used,tokens_used\n"
        b"req-1,users,200,10,4,4\n"
    )

    for csv_content in (malformed_row, duplicate_header):
        response = await client.post(
            "/reports",
            files={"file": ("usage.csv", csv_content, "text/csv")},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_concurrent_report_creation_preserves_all_reports(
    client: httpx.AsyncClient,
) -> None:
    csv_template = (
        "request_id,service,status_code,latency_ms,tokens_used\n"
        "{request_id},users,200,10,4\n"
    )

    async def create_report(index: int) -> httpx.Response:
        csv_content = csv_template.format(request_id=f"req-{index}").encode()
        return await client.post(
            "/reports",
            files={"file": (f"usage-{index}.csv", csv_content, "text/csv")},
        )

    responses = await asyncio.gather(*(create_report(index) for index in range(10)))

    assert all(response.status_code == 201 for response in responses)
    report_ids = {response.json()["id"] for response in responses}
    assert len(report_ids) == 10

    list_response = await client.get("/reports")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 10