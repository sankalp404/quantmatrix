from celery import Celery
from celery.schedules import crontab
from backend.config import settings

celery_app = Celery(
    "quantmatrix",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.account_sync",
        "backend.tasks.market_data_tasks",
    ],
)

# Use values provided by settings (from .env/docker-compose)
celery_app.conf.broker_url = settings.CELERY_BROKER_URL
celery_app.conf.result_backend = settings.CELERY_RESULT_BACKEND

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "backend.tasks.account_sync.*": {"queue": "account_sync"},
    },
    # Worker configuration
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Task execution
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Results
    result_expires=3600,  # 1 hour
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Beat schedule for periodic tasks
    beat_schedule={
        # Nightly (ordered chronologically, UTC):
        # 1) IBKR Flex sync
        "ibkr-daily-flex-sync": {
            "task": "backend.tasks.account_sync.sync_all_ibkr_accounts",
            "schedule": crontab(hour=2, minute=15),  # 10:15 PM ET
            "args": (),
        },
        # 2) Build tracked set and delta in Redis
        "update-tracked-symbol-cache": {
            "task": "backend.tasks.market_data_tasks.update_tracked_symbol_cache",
            "schedule": crontab(hour=2, minute=30),  # 10:30 PM ET
            "args": (),
        },
        # 3) Backfill only newly tracked symbols
        "backfill-new-tracked": {
            "task": "backend.tasks.market_data_tasks.backfill_new_tracked",
            "schedule": crontab(hour=2, minute=45),  # 10:45 PM ET
            "args": (),
        },
        # 4) Delta backfill for all tracked symbols (indices ∪ portfolio)
        "backfill-last-200": {
            "task": "backend.tasks.market_data_tasks.backfill_last_200_bars",
            "schedule": crontab(hour=3, minute=0),  # 11:00 PM ET
            "args": (),
        },
        # 5) Record immutable daily history before final recompute (captures end-of-day state)
        "record-daily-history": {
            "task": "backend.tasks.market_data_tasks.record_daily_history",
            "schedule": crontab(hour=3, minute=20),  # 11:20 PM ET
            "args": (),
        },
        # 6) Recompute indicators last for next-day use/performance (freshest cache)
        "recompute-indicators-universe": {
            "task": "backend.tasks.market_data_tasks.recompute_indicators_universe",
            "schedule": crontab(hour=3, minute=35),  # 11:35 PM ET
            "args": (),
        },
    },
)

# Optional: Only enable beat schedule in production
celery_app.conf.beat_schedule = celery_app.conf.beat_schedule
