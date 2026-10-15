from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.dependencies import PaginationDep, PriceServiceDep
from app.api.schemas import ErrorResponse, PriceResponse
from app.domain.tickers import Ticker

router = APIRouter(prefix="/prices", tags=["prices"])

TickerQuery = Annotated[Ticker, Query(description="Currency ticker")]
DATE_DESCRIPTION = "ISO 8601 datetime or UNIX timestamp, inclusive; naive values are UTC"


@router.get("", summary="All saved prices of a currency")
async def get_prices(
    ticker: TickerQuery, pagination: PaginationDep, service: PriceServiceDep
) -> list[PriceResponse]:
    records = await service.get_all(ticker, limit=pagination.limit, offset=pagination.offset)
    return [PriceResponse.model_validate(record) for record in records]


@router.get(
    "/latest",
    summary="Latest price of a currency",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
async def get_latest_price(ticker: TickerQuery, service: PriceServiceDep) -> PriceResponse:
    record = await service.get_latest(ticker)
    return PriceResponse.model_validate(record)


@router.get(
    "/by-date",
    summary="Prices of a currency within a date range",
    responses={status.HTTP_422_UNPROCESSABLE_ENTITY: {"model": ErrorResponse}},
)
async def get_prices_by_date(
    ticker: TickerQuery,
    pagination: PaginationDep,
    service: PriceServiceDep,
    date_from: Annotated[datetime | None, Query(description=DATE_DESCRIPTION)] = None,
    date_to: Annotated[datetime | None, Query(description=DATE_DESCRIPTION)] = None,
) -> list[PriceResponse]:
    records = await service.get_by_date(
        ticker,
        date_from=date_from,
        date_to=date_to,
        limit=pagination.limit,
        offset=pagination.offset,
    )
    return [PriceResponse.model_validate(record) for record in records]
