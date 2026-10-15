from pydantic import BaseModel, ConfigDict, Field

from app.domain.tickers import Ticker


class PriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: Ticker = Field(examples=["btc_usd"])
    price: float = Field(description="Index price in USD", examples=[80918.93])
    timestamp: int = Field(description="UNIX time in seconds", examples=[1792061819])


class ErrorResponse(BaseModel):
    detail: str
