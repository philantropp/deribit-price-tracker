from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PriceRecord
from app.domain.tickers import Ticker


class PriceRepository:
    """Data access for `PriceRecord`. Transaction boundaries belong to the caller."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_many(self, records: Sequence[PriceRecord]) -> None:
        self._session.add_all(records)
        await self._session.flush()

    async def find_by_ticker(
        self,
        ticker: Ticker,
        *,
        start: int | None = None,
        end: int | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> Sequence[PriceRecord]:
        """Records of a ticker ordered by time; `start`/`end` are inclusive UNIX bounds."""
        query = (
            select(PriceRecord)
            .where(PriceRecord.ticker == ticker.value)
            .order_by(PriceRecord.timestamp, PriceRecord.id)
            .offset(offset)
            .limit(limit)
        )
        if start is not None:
            query = query.where(PriceRecord.timestamp >= start)
        if end is not None:
            query = query.where(PriceRecord.timestamp <= end)
        result = await self._session.scalars(query)
        return result.all()

    async def get_latest(self, ticker: Ticker) -> PriceRecord | None:
        query = (
            select(PriceRecord)
            .where(PriceRecord.ticker == ticker.value)
            .order_by(PriceRecord.timestamp.desc(), PriceRecord.id.desc())
            .limit(1)
        )
        return await self._session.scalar(query)
