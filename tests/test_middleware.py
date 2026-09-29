from __future__ import annotations

import re

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.middleware import CorrelationIdMiddleware


def _client() -> TestClient:
    test_app = FastAPI()
    test_app.add_middleware(CorrelationIdMiddleware)

    @test_app.get("/")
    async def echo_correlation(request: Request) -> dict[str, str]:
        return {"correlation_id": request.state.correlation_id}

    return TestClient(test_app)


def test_request_id_is_preserved_and_returned() -> None:
    with _client() as client:
        response = client.get("/", headers={"x-request-id": "req-a1b2c3d4"})

    assert response.json()["correlation_id"] == "req-a1b2c3d4"
    assert response.headers["x-request-id"] == "req-a1b2c3d4"
    assert float(response.headers["x-response-time-ms"]) >= 0


def test_missing_or_invalid_request_id_is_replaced() -> None:
    with _client() as client:
        response = client.get("/", headers={"x-request-id": "bad-id"})

    correlation_id = response.headers["x-request-id"]
    assert re.fullmatch(r"req-[0-9a-f]{8}", correlation_id)
    assert response.json()["correlation_id"] == correlation_id
