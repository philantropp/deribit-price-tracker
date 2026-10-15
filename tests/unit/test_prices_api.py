from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.dependencies import get_price_service
from app.api.main import create_app
from app.config import Settings
from app.domain.tickers import Ticker
from app.services.price_service import PriceService
from tests.fakes import InMemoryPriceRepository, make_record

JAN_1 = 1_767_225_600
DAY = 86_400
PRICE_ENDPOINTS = ["/api/v1/prices", "/api/v1/prices/latest", "/api/v1/prices/by-date"]


@pytest.fixture
def repository() -> InMemoryPriceRepository:
    return InMemoryPriceRepository(
        [
            make_record(Ticker.BTC_USD, "80000.5", JAN_1),
            make_record(Ticker.BTC_USD, "81000.25", JAN_1 + DAY),
            make_record(Ticker.ETH_USD, "3100", JAN_1),
        ]
    )


@pytest.fixture
def app(repository: InMemoryPriceRepository) -> FastAPI:
    # The lifespan (and so the database) is not started by ASGITransport;
    # the service is replaced with one backed by the in-memory repository.
    app = create_app(Settings(database_url="postgresql+asyncpg://unused/unused"))
    app.dependency_overrides[get_price_service] = lambda: PriceService(repository)
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_get_prices_returns_all_records_of_ticker(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert response.json() == [
        {"ticker": "btc_usd", "price": 80000.5, "timestamp": JAN_1},
        {"ticker": "btc_usd", "price": 81000.25, "timestamp": JAN_1 + DAY},
    ]


async def test_get_prices_supports_limit_and_offset(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/prices", params={"ticker": "btc_usd", "limit": 1, "offset": 1}
    )

    assert [item["timestamp"] for item in response.json()] == [JAN_1 + DAY]


async def test_get_latest_price(client: AsyncClient) -> None:
    response = await client.get("/api/v1/prices/latest", params={"ticker": "btc_usd"})

    assert response.status_code == 200
    assert response.json() == {"ticker": "btc_usd", "price": 81000.25, "timestamp": JAN_1 + DAY}


async def test_get_latest_price_returns_404_without_data(
    client: AsyncClient, repository: InMemoryPriceRepository
) -> None:
    repository.records.clear()

    response = await client.get("/api/v1/prices/latest", params={"ticker": "eth_usd"})

    assert response.status_code == 404
    assert "eth_usd" in response.json()["detail"]


@pytest.mark.parametrize(
    ("params", "expected_timestamps"),
    [
        ({"date_from": "2026-01-02T00:00:00Z"}, [JAN_1 + DAY]),
        ({"date_to": "2026-01-01T12:00:00"}, [JAN_1]),
        ({"date_from": str(JAN_1), "date_to": str(JAN_1 + DAY)}, [JAN_1, JAN_1 + DAY]),
        ({"date_from": "2026-01-01T03:00:00+03:00", "date_to": "2026-01-01"}, [JAN_1]),
    ],
    ids=["iso-from", "naive-to", "unix", "with-offset"],
)
async def test_get_prices_by_date(
    client: AsyncClient, params: dict[str, str], expected_timestamps: list[int]
) -> None:
    response = await client.get("/api/v1/prices/by-date", params={"ticker": "btc_usd", **params})

    assert response.status_code == 200
    assert [item["timestamp"] for item in response.json()] == expected_timestamps


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"date_from": "2026-01-02", "date_to": "2026-01-01"},
        {"date_from": "not-a-date"},
    ],
    ids=["no-bounds", "inverted", "malformed"],
)
async def test_get_prices_by_date_rejects_bad_range(
    client: AsyncClient, params: dict[str, str]
) -> None:
    response = await client.get("/api/v1/prices/by-date", params={"ticker": "btc_usd", **params})

    assert response.status_code == 422


@pytest.mark.parametrize("path", PRICE_ENDPOINTS)
async def test_ticker_is_required(client: AsyncClient, path: str) -> None:
    response = await client.get(path)

    assert response.status_code == 422


@pytest.mark.parametrize("path", PRICE_ENDPOINTS)
async def test_unknown_ticker_is_rejected(client: AsyncClient, path: str) -> None:
    response = await client.get(path, params={"ticker": "doge_usd"})

    assert response.status_code == 422


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.json() == {"status": "ok"}
