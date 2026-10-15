from decimal import Decimal

from app.clients.deribit import DeribitConnectionError
from app.domain.tickers import Ticker
from app.services.price_collector import PriceCollector
from tests.fakes import FakePriceProvider, InMemoryPriceRepository

NOW = 1_792_061_819


def fixed_clock() -> int:
    return NOW


async def test_saves_price_of_every_ticker_with_one_timestamp() -> None:
    provider = FakePriceProvider({"btc_usd": Decimal("80918.93"), "eth_usd": Decimal("3150.5")})
    repository = InMemoryPriceRepository()
    collector = PriceCollector(provider, repository, clock=fixed_clock)

    report = await collector.collect()

    saved = {(r.ticker, r.price, r.timestamp) for r in repository.records}
    assert saved == {
        ("btc_usd", Decimal("80918.93"), NOW),
        ("eth_usd", Decimal("3150.5"), NOW),
    }
    assert sorted(provider.requested) == ["btc_usd", "eth_usd"]
    assert report.failed == ()
    assert len(report.saved) == 2


async def test_failed_ticker_does_not_block_others() -> None:
    provider = FakePriceProvider(
        {"btc_usd": Decimal("80918.93"), "eth_usd": DeribitConnectionError("timeout")}
    )
    repository = InMemoryPriceRepository()
    collector = PriceCollector(provider, repository, clock=fixed_clock)

    report = await collector.collect()

    assert [r.ticker for r in repository.records] == ["btc_usd"]
    assert report.failed == (Ticker.ETH_USD,)


async def test_nothing_is_written_when_all_tickers_fail() -> None:
    error = DeribitConnectionError("down")
    provider = FakePriceProvider({"btc_usd": error, "eth_usd": error})
    repository = InMemoryPriceRepository()
    collector = PriceCollector(provider, repository, clock=fixed_clock)

    report = await collector.collect()

    assert repository.records == []
    assert set(report.failed) == {Ticker.BTC_USD, Ticker.ETH_USD}


async def test_collects_only_configured_tickers() -> None:
    provider = FakePriceProvider({"btc_usd": Decimal("1")})
    repository = InMemoryPriceRepository()
    collector = PriceCollector(provider, repository, tickers=[Ticker.BTC_USD], clock=fixed_clock)

    await collector.collect()

    assert provider.requested == ["btc_usd"]
