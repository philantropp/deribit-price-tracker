from app.domain.tickers import Ticker


class PriceServiceError(Exception):
    """Base error of the price query service."""


class PriceNotFoundError(PriceServiceError):
    def __init__(self, ticker: Ticker) -> None:
        super().__init__(f"No prices saved for ticker {ticker.value!r}")
        self.ticker = ticker


class InvalidDateRangeError(PriceServiceError):
    pass
