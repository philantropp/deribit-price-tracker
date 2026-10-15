import aiohttp

from app.clients.deribit import DeribitClient
from app.config import Settings
from app.db.database import Database
from app.repositories.prices import PriceRepository
from app.services.price_collector import CollectionReport, PriceCollector


class PriceCollectionError(Exception):
    def __init__(self, report: CollectionReport) -> None:
        failed = ", ".join(ticker.value for ticker in report.failed)
        super().__init__(f"Failed to collect prices for: {failed}")
        self.report = report


async def collect_index_prices(settings: Settings) -> CollectionReport:
    """Wire the collector with real dependencies and run it once.

    The engine is created per run: a Celery task calls `asyncio.run`, which
    starts a fresh event loop each time, and asyncpg connections cannot be
    reused across event loops.
    """
    database = Database(settings.database_url)
    timeout = aiohttp.ClientTimeout(total=settings.deribit_timeout_seconds)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as http_session:
            client = DeribitClient(http_session, settings.deribit_base_url)
            async with database.session() as session:
                collector = PriceCollector(client, PriceRepository(session))
                report = await collector.collect()
    finally:
        await database.dispose()

    if report.failed:
        # Raised after the commit: prices that were fetched are already saved,
        # but the task is marked as failed and visible in monitoring.
        raise PriceCollectionError(report)
    return report
