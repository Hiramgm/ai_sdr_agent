"""Redis connection and RQ queue helpers.

Redis and RQ are imported lazily so the rest of the app (CLI, ingestion, the
synchronous API endpoints) keeps working with no queue infrastructure present.
A clean ``QueueUnavailable`` error is raised only when async features are used
without a reachable Redis server.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ai_sdr.config import SETTINGS

if TYPE_CHECKING:  # pragma: no cover - typing only.
    from redis import Redis
    from rq import Queue
    from rq.job import Job

QUEUE_NAME = "ai_sdr"
DEFAULT_JOB_TIMEOUT = 300
RESULT_TTL = 3600


class QueueUnavailable(RuntimeError):
    """Raised when the Redis-backed queue cannot be used."""


def get_redis(url: str | None = None) -> "Redis":
    """Open a Redis connection. Raises QueueUnavailable if the driver is missing."""
    try:
        from redis import Redis
    except ImportError as error:  # pragma: no cover - exercised only without redis.
        raise QueueUnavailable(
            "Install redis + rq to use async jobs: "
            ".venv/bin/python -m pip install -r requirements.txt"
        ) from error
    return Redis.from_url(url or SETTINGS.redis_url)


def get_queue(connection: "Redis" | None = None) -> "Queue":
    """Return the RQ queue bound to a Redis connection."""
    try:
        from rq import Queue
    except ImportError as error:  # pragma: no cover - exercised only without rq.
        raise QueueUnavailable(
            "Install redis + rq to use async jobs: "
            ".venv/bin/python -m pip install -r requirements.txt"
        ) from error
    return Queue(
        QUEUE_NAME,
        connection=connection or get_redis(),
        default_timeout=DEFAULT_JOB_TIMEOUT,
    )


def enqueue(func_path: str, job_kwargs: dict[str, Any]) -> "Job":
    """Enqueue a task by dotted path, normalizing connection failures.

    ``get_queue`` does not open a socket; the connection is made when the job is
    actually enqueued. We catch those failures here so callers only have to
    handle ``QueueUnavailable``.
    """
    try:
        queue = get_queue()
        return queue.enqueue(func_path, kwargs=job_kwargs)
    except QueueUnavailable:
        raise
    except Exception as error:  # noqa: BLE001 - normalize redis connection errors.
        raise QueueUnavailable(
            f"Cannot reach Redis at {SETTINGS.redis_url}. Start Redis and try again."
        ) from error


def ping() -> bool:
    """Check Redis connectivity. Raises QueueUnavailable if it cannot connect."""
    try:
        get_redis().ping()
    except QueueUnavailable:
        raise
    except Exception as error:  # noqa: BLE001 - normalize all connection failures.
        raise QueueUnavailable(
            f"Cannot reach Redis at {SETTINGS.redis_url}. Start Redis and try again."
        ) from error
    return True


def _job_result(job: "Job") -> Any:
    """Return a finished job's result across RQ versions."""
    getter = getattr(job, "return_value", None)
    if callable(getter):
        return getter()
    return getattr(job, "result", None)


def fetch_job_state(job_id: str, connection: "Redis" | None = None) -> dict[str, Any]:
    """Return a serializable snapshot of an RQ job's status and result."""
    try:
        from rq.job import Job
    except ImportError as error:  # pragma: no cover
        raise QueueUnavailable("Install redis + rq to use async jobs.") from error

    conn = connection or get_redis()
    try:
        job = Job.fetch(job_id, connection=conn)
    except Exception as error:  # noqa: BLE001 - includes NoSuchJobError.
        raise QueueUnavailable(f"Job '{job_id}' was not found.") from error

    status = job.get_status(refresh=True)
    state: dict[str, Any] = {"job_id": job.id, "status": status}
    if status == "finished":
        state["result"] = _job_result(job)
    elif status == "failed":
        state["error"] = job.latest_result().exc_string if hasattr(job, "latest_result") else "Job failed."
    return state
