from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.services.exceptions import InvalidDateRangeError, PriceNotFoundError


async def handle_price_not_found(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(error)})


async def handle_invalid_date_range(request: Request, error: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(error)}
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Map domain errors of the service layer to HTTP responses."""
    app.add_exception_handler(PriceNotFoundError, handle_price_not_found)
    app.add_exception_handler(InvalidDateRangeError, handle_invalid_date_range)
