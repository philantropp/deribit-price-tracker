"""Minimal async client for the public Deribit JSON-RPC over HTTP API.

Docs: https://docs.deribit.com/#public-get_index_price
"""

from decimal import Decimal, InvalidOperation
from typing import Any

import aiohttp


class DeribitError(Exception):
    """Base error of the Deribit client."""


class DeribitConnectionError(DeribitError):
    """The request did not reach Deribit or timed out."""


class DeribitResponseError(DeribitError):
    """Deribit answered with something that is not a valid JSON-RPC response."""


class DeribitAPIError(DeribitError):
    """Deribit answered with a JSON-RPC error object."""

    def __init__(self, code: int | None, message: str) -> None:
        super().__init__(f"Deribit API error {code}: {message}")
        self.code = code
        self.message = message


class DeribitClient:
    """Calls public Deribit methods.

    The `aiohttp.ClientSession` is injected: its lifetime (and timeouts,
    connection pool) is owned by the caller, and tests can point the client
    at a local server.
    """

    def __init__(self, http_session: aiohttp.ClientSession, base_url: str) -> None:
        self._http_session = http_session
        self._base_url = base_url.rstrip("/")

    async def get_index_price(self, index_name: str) -> Decimal:
        """Current index price, e.g. `get_index_price("btc_usd")`."""
        result = await self._call_public("get_index_price", {"index_name": index_name})
        try:
            return Decimal(str(result["index_price"]))
        except (KeyError, TypeError, InvalidOperation) as error:
            raise DeribitResponseError(f"No valid index_price in result: {result!r}") from error

    async def _call_public(self, method: str, params: dict[str, str]) -> dict[str, Any]:
        url = f"{self._base_url}/public/{method}"
        try:
            async with self._http_session.get(url, params=params) as response:
                status = response.status
                try:
                    payload = await response.json(content_type=None)
                except ValueError as error:
                    raise DeribitResponseError(f"Non-JSON response (HTTP {status})") from error
        except (aiohttp.ClientError, TimeoutError) as error:
            raise DeribitConnectionError(f"Request to {url} failed: {error!r}") from error

        if not isinstance(payload, dict):
            raise DeribitResponseError(f"Unexpected payload (HTTP {status}): {payload!r}")
        if (error_object := payload.get("error")) is not None:
            raise DeribitAPIError(error_object.get("code"), error_object.get("message", ""))
        if status != 200 or not isinstance(payload.get("result"), dict):
            raise DeribitResponseError(f"Unexpected payload (HTTP {status}): {payload!r}")
        return payload["result"]
