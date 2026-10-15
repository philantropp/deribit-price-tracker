from decimal import Decimal

from sqlalchemy import BigInteger, Identity, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class PriceRecord(Base):
    """One index price observation: ticker, price and UNIX time (seconds)."""

    __tablename__ = "prices"
    __table_args__ = (Index("ix_prices_ticker_timestamp", "ticker", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(16))
    price: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    timestamp: Mapped[int] = mapped_column(BigInteger)

    def __repr__(self) -> str:
        return f"PriceRecord({self.ticker!r}, price={self.price}, timestamp={self.timestamp})"
