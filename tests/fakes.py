from collections.abc import Sequence
from decimal import Decimal

from app.db.models import PriceRecord
from app.domain.tickers import Ticker


class InMemoryPriceRepository:
    """Same contract as `PriceRepository`, backed by a list."""

    def __init__(self, records: Sequence[PriceRecord] = ()) -> None:
        self.records: list[PriceRecord] = list(records)

    async def add_many(self, records: Sequence[PriceRecord]) -> None:
        self.records.extend(records)

    async def find_by_ticker(
        self,
        ticker: Ticker,
        *,
        start: int | None = None,
        end: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[PriceRecord]:
        matching = sorted(
            (
                record
                for record in self.records
                if record.ticker == ticker.value
                and (start is None or record.timestamp >= start)
                and (end is None or record.timestamp <= end)
            ),
            key=lambda record: record.timestamp,
        )
        stop = None if limit is None else offset + limit
        return matching[offset:stop]

    async def get_latest(self, ticker: Ticker) -> PriceRecord | None:
        matching = await self.find_by_ticker(ticker)
        return matching[-1] if matching else None


class FakePriceProvider:
    """Returns preset prices; an Exception value is raised instead."""

    def __init__(self, prices: dict[str, Decimal | Exception]) -> None:
        self._prices = prices
        self.requested: list[str] = []

    async def get_index_price(self, index_name: str) -> Decimal:
        self.requested.append(index_name)
        price = self._prices[index_name]
        if isinstance(price, Exception):
            raise price
        return price


def make_record(ticker: Ticker, price: str, timestamp: int) -> PriceRecord:
    return PriceRecord(ticker=ticker.value, price=Decimal(price), timestamp=timestamp)
