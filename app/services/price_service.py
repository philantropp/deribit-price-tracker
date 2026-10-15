from collections.abc import Sequence
from datetime import datetime

from app.db.models import PriceRecord
from app.domain.tickers import Ticker
from app.domain.time import to_unix_timestamp
from app.repositories.prices import PriceRepository
from app.services.exceptions import InvalidDateRangeError, PriceNotFoundError


class PriceService:
    """Read-side use cases of the API, independent of HTTP."""

    def __init__(self, repository: PriceRepository) -> None:
        self._repository = repository

    async def get_all(
        self, ticker: Ticker, *, limit: int | None = None, offset: int = 0
    ) -> Sequence[PriceRecord]:
        return await self._repository.find_by_ticker(ticker, limit=limit, offset=offset)

    async def get_latest(self, ticker: Ticker) -> PriceRecord:
        record = await self._repository.get_latest(ticker)
        if record is None:
            raise PriceNotFoundError(ticker)
        return record

    async def get_by_date(
        self,
        ticker: Ticker,
        *,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[PriceRecord]:
        """Prices within [date_from, date_to]; either bound may be omitted, not both."""
        if date_from is None and date_to is None:
            raise InvalidDateRangeError("At least one of date_from, date_to is required")

        start = to_unix_timestamp(date_from) if date_from is not None else None
        end = to_unix_timestamp(date_to) if date_to is not None else None
        if start is not None and end is not None and start > end:
            raise InvalidDateRangeError("date_from must not be later than date_to")

        return await self._repository.find_by_ticker(
            ticker, start=start, end=end, limit=limit, offset=offset
        )
