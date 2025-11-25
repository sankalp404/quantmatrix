from __future__ import annotations

import json
import functools
import traceback
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

from backend.database import SessionLocal
from backend.models import JobRun
from backend.services.market.market_data_service import market_data_service


def task_run(task_name: str, *, lock_key: Optional[Callable[..., Optional[str]]] = None, lock_ttl_seconds: int = 1800):
    """
    Decorator to standardize task execution:
    - Optional Redis lock to prevent duplicate work (by computed key)
    - Write JobRun row with status running/ok/error and counters from returned dict
    - Publish last-run status into Redis key: taskstatus:{task_name}:last
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Optional redis lock
            lock_id: Optional[str] = None
            if lock_key is not None:
                try:
                    key = lock_key(*args, **kwargs)
                    if key:
                        r = market_data_service.redis_client
                        # SETNX + expiry
                        acquired = r.set(name=f"lock:{task_name}:{key}", value="1", nx=True, ex=lock_ttl_seconds)
                        if not acquired:
                            return {"status": "skipped", "reason": "locked", "lock_key": key}
                        lock_id = key
                except Exception:
                    pass
            # Create job run
            session = SessionLocal()
            job = JobRun(
                task_name=task_name,
                params=kwargs or {},
                status="running",
                started_at=datetime.utcnow(),
            )
            session.add(job)
            session.commit()
            # Publish 'running'
            try:
                _publish_status(task_name, "running", {"id": job.id, "params": kwargs})
            except Exception:
                pass
            try:
                result = func(*args, **kwargs)
                counters = None
                if isinstance(result, dict):
                    counters = {k: v for k, v in result.items() if k not in ("status", "error")}
                job.status = "ok"
                job.finished_at = datetime.utcnow()
                if counters:
                    job.counters = counters
                session.commit()
                try:
                    _publish_status(task_name, "ok", {"id": job.id, "payload": result})
                except Exception:
                    pass
                return result
            except Exception as exc:
                job.status = "error"
                job.error = f"{exc}\n{traceback.format_exc()}"
                job.finished_at = datetime.utcnow()
                session.commit()
                try:
                    _publish_status(task_name, "error", {"id": job.id, "error": str(exc)})
                except Exception:
                    pass
                raise
            finally:
                session.close()
                if lock_id is not None:
                    try:
                        market_data_service.redis_client.delete(f"lock:{task_name}:{lock_id}")
                    except Exception:
                        pass

        return wrapper

    return decorator


def _publish_status(task: str, status: str, payload: dict | None = None) -> None:
    r = market_data_service.redis_client
    r.set(
        f"taskstatus:{task}:last",
        json.dumps({"task": task, "status": status, "ts": datetime.utcnow().isoformat(), "payload": payload or {}}),
    )



