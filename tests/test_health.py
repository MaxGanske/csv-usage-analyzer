# Smoke test for the deployed service's liveness endpoint.
# This test deliberately avoids database access so it can run anywhere.
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    """The liveness endpoint should return a successful status payload."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
