from enum import StrEnum


class Ticker(StrEnum):
    """Currencies whose index price is tracked.

    The value doubles as the Deribit `index_name`, so adding a currency is a
    one-line change here.
    """

    BTC_USD = "btc_usd"
    ETH_USD = "eth_usd"
