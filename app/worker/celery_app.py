"""Celery entry point: `celery -A app.worker.celery_app worker|beat`."""

import asyncio

from celery import Celery

from app.config import Settings, get_settings
from app.worker.jobs import collect_index_prices

COLLECT_PRICES_TASK = "prices.collect_index_prices"


def create_celery_app(settings: Settings) -> Celery:
    app = Celery("deribit_price_tracker", broker=settings.celery_broker_url)
    interval = settings.price_collection_interval_seconds
    app.conf.update(
        timezone="UTC",
        task_ignore_result=True,
        broker_connection_retry_on_startup=True,
        beat_schedule={
            "collect-index-prices": {
                "task": COLLECT_PRICES_TASK,
                "schedule": interval,
                # A price fetched later than the next tick is useless:
                # drop the task instead of letting a backlog build up.
                "options": {"expires": interval},
            },
        },
    )

    @app.task(name=COLLECT_PRICES_TASK)
    def collect_prices() -> int:
        report = asyncio.run(collect_index_prices(settings))
        return len(report.saved)

    return app


# The Celery CLI (`-A`) needs a module attribute holding the app instance.
celery_app = create_celery_app(get_settings())
