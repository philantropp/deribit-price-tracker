from collections.abc import AsyncIterator, Awaitable, Callable
from decimal import Decimal

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from app.clients.deribit import (
    DeribitAPIError,
    DeribitClient,
    DeribitConnectionError,
    DeribitResponseError,
)

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]
ClientFactory = Callable[[Handler], Awaitable[DeribitClient]]


@pytest.fixture
async def make_client() -> AsyncIterator[ClientFactory]:
    """Start a local server that plays Deribit and return a client pointed at it."""
    servers: list[TestServer] = []
    http_session = aiohttp.ClientSession()

    async def factory(handler: Handler) -> DeribitClient:
        app = web.Application()
        app.router.add_get("/api/v2/public/get_index_price", handler)
        server = TestServer(app)
        await server.start_server()
        servers.append(server)
        return DeribitClient(http_session, str(server.make_url("/api/v2")))

    yield factory

    await http_session.close()
    for server in servers:
        await server.close()


async def test_returns_index_price_and_sends_index_name(make_client: ClientFactory) -> None:
    received_params = {}

    async def handler(request: web.Request) -> web.Response:
        received_params.update(request.query)
        return web.json_response(
            {"jsonrpc": "2.0", "result": {"index_price": 80918.93, "estimated_delivery_price": 1}}
        )

    client = await make_client(handler)

    price = await client.get_index_price("btc_usd")

    assert price == Decimal("80918.93")
    assert received_params == {"index_name": "btc_usd"}


async def test_raises_api_error_on_json_rpc_error(make_client: ClientFactory) -> None:
    async def handler(request: web.Request) -> web.Response:
        error = {"code": -32602, "message": "Invalid params"}
        return web.json_response({"jsonrpc": "2.0", "error": error}, status=400)

    client = await make_client(handler)

    with pytest.raises(DeribitAPIError) as error_info:
        await client.get_index_price("unknown")
    assert error_info.value.code == -32602


@pytest.mark.parametrize(
    "response",
    [
        web.Response(text="<html>Bad gateway</html>", status=502),
        web.json_response({"jsonrpc": "2.0", "result": {}}),
        web.json_response({"jsonrpc": "2.0", "result": {"index_price": None}}),
        web.json_response(["not", "an", "object"]),
    ],
    ids=["non-json", "no-index-price", "null-index-price", "not-an-object"],
)
async def test_raises_response_error_on_malformed_response(
    make_client: ClientFactory, response: web.Response
) -> None:
    async def handler(request: web.Request) -> web.Response:
        return response

    client = await make_client(handler)

    with pytest.raises(DeribitResponseError):
        await client.get_index_price("btc_usd")


async def test_raises_connection_error_when_server_unreachable() -> None:
    async with aiohttp.ClientSession() as http_session:
        client = DeribitClient(http_session, "http://127.0.0.1:1/api/v2")

        with pytest.raises(DeribitConnectionError):
            await client.get_index_price("btc_usd")
