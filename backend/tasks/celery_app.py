from celery import Celery
from celery.schedules import crontab
from backend.config import settings

# Create Celery instance
celery_app = Celery(
    "quantmatrix",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "backend.tasks.scanner",
        "backend.tasks.monitor",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task routing
    task_routes={
        "backend.tasks.scanner.*": {"queue": "scanner"},
        "backend.tasks.monitor.*": {"queue": "monitor"},
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
        # Morning Brew - Daily market intelligence at 7:30 AM ET
        "morning-brew": {
            "task": "backend.tasks.monitor.send_morning_brew",
            "schedule": crontab(hour=12, minute=30),  # 7:30 AM ET in UTC
            "args": (),
        },
        # Daily ATR Matrix scan at 9:15 AM and 3:15 PM ET
        "daily-atr-scan-morning": {
            "task": "backend.tasks.scanner.run_atr_matrix_scan",
            "schedule": crontab(hour=14, minute=15),  # 9:15 AM ET in UTC
            "args": (),
        },
        "daily-atr-scan-afternoon": {
            "task": "backend.tasks.scanner.run_atr_matrix_scan",
            "schedule": crontab(hour=20, minute=15),  # 3:15 PM ET in UTC
            "args": (),
        },
        # Portfolio monitoring every 5 minutes during market hours
        "portfolio-monitor": {
            "task": "backend.tasks.monitor.monitor_portfolios",
            "schedule": crontab(minute="*/5", hour="14-21"),  # 9 AM - 4 PM ET
            "args": (),
        },
        # Alert checking every minute during market hours
        "check-alerts": {
            "task": "backend.tasks.monitor.check_alerts",
            "schedule": crontab(
                minute="*", hour="14-21"
            ),  # Every minute 9 AM - 4 PM ET
            "args": (),
        },
        # Daily portfolio summary at market close
        "daily-portfolio-summary": {
            "task": "backend.tasks.monitor.send_daily_summary",
            "schedule": crontab(hour=21, minute=30),  # 4:30 PM ET
            "args": (),
        },
        # Weekly performance report on Sunday
        "weekly-performance-report": {
            "task": "backend.tasks.monitor.send_weekly_report",
            "schedule": crontab(day_of_week=0, hour=10, minute=0),  # Sunday 10 AM
            "args": (),
        },
        # Clean up old data monthly
        "cleanup-old-data": {
            "task": "backend.tasks.monitor.cleanup_old_data",
            "schedule": crontab(
                day_of_month=1, hour=2, minute=0
            ),  # 1st of month at 2 AM
            "args": (),
        },
    },
)

# Optional: Only enable beat schedule in production
if not settings.DEBUG:
    celery_app.conf.beat_schedule = celery_app.conf.beat_schedule
else:
    # Reduced schedule for development
    celery_app.conf.beat_schedule = {
        "test-scanner": {
            "task": "backend.tasks.scanner.run_atr_matrix_scan",
            "schedule": 300.0,  # Every 5 minutes
            "args": (),
        },
    }
