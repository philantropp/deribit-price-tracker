from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.tickers import Ticker
from app.services.exceptions import InvalidDateRangeError, PriceNotFoundError
from app.services.price_service import PriceService
from tests.fakes import InMemoryPriceRepository, make_record

# 2026-01-01 00:00:00 UTC
JAN_1 = 1_767_225_600
DAY = 86_400


@pytest.fixture
def service() -> PriceService:
    repository = InMemoryPriceRepository(
        [
            make_record(Ticker.BTC_USD, "100", JAN_1),
            make_record(Ticker.BTC_USD, "200", JAN_1 + DAY),
            make_record(Ticker.BTC_USD, "300", JAN_1 + 2 * DAY),
            make_record(Ticker.ETH_USD, "10", JAN_1 + DAY),
        ]
    )
    return PriceService(repository)


async def test_get_all_returns_only_requested_ticker_in_time_order(service: PriceService) -> None:
    records = await service.get_all(Ticker.BTC_USD)

    assert [r.timestamp for r in records] == [JAN_1, JAN_1 + DAY, JAN_1 + 2 * DAY]
    assert {r.ticker for r in records} == {"btc_usd"}


async def test_get_all_paginates(service: PriceService) -> None:
    records = await service.get_all(Ticker.BTC_USD, limit=1, offset=1)

    assert [r.timestamp for r in records] == [JAN_1 + DAY]


async def test_get_latest_returns_most_recent(service: PriceService) -> None:
    record = await service.get_latest(Ticker.BTC_USD)

    assert record.timestamp == JAN_1 + 2 * DAY


async def test_get_latest_raises_when_no_data() -> None:
    service = PriceService(InMemoryPriceRepository())

    with pytest.raises(PriceNotFoundError):
        await service.get_latest(Ticker.BTC_USD)


async def test_get_by_date_includes_both_bounds(service: PriceService) -> None:
    records = await service.get_by_date(
        Ticker.BTC_USD,
        date_from=datetime(2026, 1, 1, tzinfo=UTC),
        date_to=datetime(2026, 1, 2, tzinfo=UTC),
    )

    assert [r.timestamp for r in records] == [JAN_1, JAN_1 + DAY]


async def test_get_by_date_with_open_end(service: PriceService) -> None:
    records = await service.get_by_date(Ticker.BTC_USD, date_from=datetime(2026, 1, 2, tzinfo=UTC))

    assert [r.timestamp for r in records] == [JAN_1 + DAY, JAN_1 + 2 * DAY]


async def test_get_by_date_treats_naive_datetime_as_utc(service: PriceService) -> None:
    records = await service.get_by_date(Ticker.BTC_USD, date_to=datetime(2026, 1, 1))

    assert [r.timestamp for r in records] == [JAN_1]


async def test_get_by_date_respects_timezone(service: PriceService) -> None:
    # 2026-01-02 03:00 at UTC+3 is 2026-01-02 00:00 UTC
    moscow = timezone(timedelta(hours=3))
    records = await service.get_by_date(
        Ticker.BTC_USD, date_from=datetime(2026, 1, 2, 3, 0, tzinfo=moscow)
    )

    assert records[0].timestamp == JAN_1 + DAY


async def test_get_by_date_requires_a_bound(service: PriceService) -> None:
    with pytest.raises(InvalidDateRangeError):
        await service.get_by_date(Ticker.BTC_USD)


async def test_get_by_date_rejects_inverted_range(service: PriceService) -> None:
    with pytest.raises(InvalidDateRangeError):
        await service.get_by_date(
            Ticker.BTC_USD,
            date_from=datetime(2026, 1, 2, tzinfo=UTC),
            date_to=datetime(2026, 1, 1, tzinfo=UTC),
        )
