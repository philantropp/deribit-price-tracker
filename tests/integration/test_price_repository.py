"""Repository tests against a real PostgreSQL.

Run with TEST_DATABASE_URL set (the `tests` compose service does it). Every
test creates its own schema inside a transaction and rolls it back, so tests
neither see nor leave data in the real `prices` table.
"""

import os
from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.models import Base
from app.domain.tickers import Ticker
from app.repositories.prices import PriceRepository
from tests.fakes import make_record

TEST_SCHEMA = "repository_tests"


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    database_url = os.environ.get("TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is not set")

    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.execute(text(f"CREATE SCHEMA {TEST_SCHEMA}"))
        await connection.execute(text(f"SET LOCAL search_path TO {TEST_SCHEMA}"))
        await connection.run_sync(Base.metadata.create_all)
        session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint")
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
async def repository(session: AsyncSession) -> PriceRepository:
    repository = PriceRepository(session)
    await repository.add_many(
        [
            make_record(Ticker.BTC_USD, "300.12345678", 300),
            make_record(Ticker.BTC_USD, "100", 100),
            make_record(Ticker.BTC_USD, "200", 200),
            make_record(Ticker.ETH_USD, "10", 400),
        ]
    )
    return repository


async def test_find_by_ticker_orders_by_time(repository: PriceRepository) -> None:
    records = await repository.find_by_ticker(Ticker.BTC_USD)

    assert [r.timestamp for r in records] == [100, 200, 300]
    assert records[-1].price == Decimal("300.12345678")


async def test_find_by_ticker_filters_by_inclusive_bounds(repository: PriceRepository) -> None:
    records = await repository.find_by_ticker(Ticker.BTC_USD, start=200, end=300)

    assert [r.timestamp for r in records] == [200, 300]


async def test_find_by_ticker_paginates(repository: PriceRepository) -> None:
    records = await repository.find_by_ticker(Ticker.BTC_USD, limit=1, offset=1)

    assert [r.timestamp for r in records] == [200]


async def test_get_latest(repository: PriceRepository) -> None:
    latest = await repository.get_latest(Ticker.BTC_USD)

    assert latest is not None
    assert latest.timestamp == 300


async def test_get_latest_returns_none_for_empty_ticker(session: AsyncSession) -> None:
    assert await PriceRepository(session).get_latest(Ticker.ETH_USD) is None
