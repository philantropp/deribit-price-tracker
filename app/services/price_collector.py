import asyncio
import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.db.models import PriceRecord
from app.domain.tickers import Ticker
from app.domain.time import current_unix_timestamp
from app.repositories.prices import PriceRepository

logger = logging.getLogger(__name__)


class IndexPriceProvider(Protocol):
    """Anything that can tell the current index price (DeribitClient, a fake in tests)."""

    async def get_index_price(self, index_name: str) -> Decimal: ...


@dataclass(frozen=True, slots=True)
class CollectionReport:
    saved: tuple[PriceRecord, ...]
    failed: tuple[Ticker, ...]


class PriceCollector:
    """Fetches index prices of all tickers and stores them in one batch.

    All records of one run share a single timestamp: it marks the moment of
    the collection, so prices of different tickers stay comparable.
    A failure of one ticker does not prevent saving the others.
    """

    def __init__(
        self,
        price_provider: IndexPriceProvider,
        repository: PriceRepository,
        *,
        tickers: Iterable[Ticker] = tuple(Ticker),
        clock: Callable[[], int] = current_unix_timestamp,
    ) -> None:
        self._price_provider = price_provider
        self._repository = repository
        self._tickers = tuple(tickers)
        self._clock = clock

    async def collect(self) -> CollectionReport:
        timestamp = self._clock()
        results = await asyncio.gather(
            *(self._price_provider.get_index_price(ticker.value) for ticker in self._tickers),
            return_exceptions=True,
        )

        saved: list[PriceRecord] = []
        failed: list[Ticker] = []
        for ticker, result in zip(self._tickers, results, strict=True):
            if isinstance(result, Exception):
                logger.error("Failed to fetch %s index price: %s", ticker.value, result)
                failed.append(ticker)
            elif isinstance(result, BaseException):
                raise result  # cancellation and the like must propagate
            else:
                saved.append(PriceRecord(ticker=ticker.value, price=result, timestamp=timestamp))

        if saved:
            await self._repository.add_many(saved)
        logger.info("Saved %d prices at %d, failed: %s", len(saved), timestamp, failed or "none")
        return CollectionReport(saved=tuple(saved), failed=tuple(failed))
