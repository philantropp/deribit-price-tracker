from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import Database
from app.repositories.prices import PriceRepository
from app.services.price_service import PriceService


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session


def get_price_service(session: Annotated[AsyncSession, Depends(get_session)]) -> PriceService:
    return PriceService(PriceRepository(session))


@dataclass(frozen=True, slots=True)
class Pagination:
    limit: int | None
    offset: int


def get_pagination(
    limit: Annotated[int | None, Query(ge=1, description="Max records; all if omitted")] = None,
    offset: Annotated[int, Query(ge=0, description="Records to skip")] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PriceServiceDep = Annotated[PriceService, Depends(get_price_service)]
PaginationDep = Annotated[Pagination, Depends(get_pagination)]
