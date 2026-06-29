"""RQ worker entry point.

Run with:

    python -m ai_sdr.jobs.worker

On macOS, Python's fork safety can crash forking workers. Use ``--simple`` to
run a non-forking worker (recommended for local demos):

    python -m ai_sdr.jobs.worker --simple
"""

from __future__ import annotations

import argparse

from ai_sdr.jobs.queue import QUEUE_NAME, get_redis


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Start an RQ worker for AI SDR jobs.")
    parser.add_argument(
        "--simple",
        action="store_true",
        help="Use a non-forking SimpleWorker (recommended on macOS).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    from rq import Queue, SimpleWorker, Worker

    connection = get_redis()
    queues = [Queue(QUEUE_NAME, connection=connection)]
    worker_cls = SimpleWorker if args.simple else Worker
    worker = worker_cls(queues, connection=connection)
    print(f"Starting {worker_cls.__name__} on queue '{QUEUE_NAME}' (Ctrl+C to stop).")
    worker.work()


if __name__ == "__main__":
    main()
