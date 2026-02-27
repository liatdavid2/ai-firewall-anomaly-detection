from __future__ import annotations

import time
import threading
import queue
from typing import Dict, Any, Optional

from app.services.anomaly_service import score_connection
from app.services.storage import update_connection_decision, get_connection_by_id
from app.services.policy_engine import find_matching_policy
from app.core.decision import decide
from app.services.redis_cache import cache_connection


# ============================================================
# Token Bucket (used ONLY by worker now)
# ============================================================

class TokenBucket:
    def __init__(self, rate_per_sec: float, capacity: float) -> None:
        self.rate = rate_per_sec
        self.capacity = capacity
        self.tokens = capacity
        self.last_refill = time.monotonic()
        self._lock = threading.Lock()

    def try_consume(self, amount: float = 1.0) -> bool:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.last_refill = now

            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.rate
            )

            if self.tokens >= amount:
                self.tokens -= amount
                return True

            return False


# limit ONLY background worker
_bucket = TokenBucket(rate_per_sec=100.0, capacity=100.0)

# large queue
_scoring_queue: "queue.Queue[str]" = queue.Queue(maxsize=50000)

_worker_started = False
_worker_lock = threading.Lock()


# ============================================================
# Public API
# ============================================================

def submit_for_scoring(
    connection_id: str,
    conn,
    policy_id: Optional[str]
) -> Dict[str, Any]:
    """
    NEVER blocks API request.
    Always async.
    """

    try:
        _scoring_queue.put_nowait(connection_id)

        return {
            "mode": "async",
            "queued": True
        }

    except queue.Full:

        # extreme case
        return {
            "mode": "async",
            "queued": False
        }


# ============================================================
# Background Worker
# ============================================================

def _worker_loop() -> None:

    while True:

        connection_id = _scoring_queue.get()

        try:

            # throttle worker rate
            while not _bucket.try_consume(1.0):
                time.sleep(0.002)

            stored = get_connection_by_id(connection_id)

            if stored is None:
                continue

            class _ConnObj:
                source_ip = stored["source_ip"]
                destination_ip = stored["destination_ip"]
                destination_port = stored["destination_port"]
                protocol = stored["protocol"]

            score = score_connection(_ConnObj)

            policy = None

            try:
                from app.models.connection import ConnectionRequest
                from datetime import datetime

                policy_eval_conn = ConnectionRequest(
                    source_ip=stored["source_ip"],
                    destination_ip=stored["destination_ip"],
                    destination_port=stored["destination_port"],
                    protocol=stored["protocol"],
                    timestamp=datetime.fromisoformat(stored["timestamp"]),
                )

                policy = find_matching_policy(policy_eval_conn)

            except Exception:
                policy = None

            final_decision = decide(policy, score)

            updated = update_connection_decision(
                connection_id=connection_id,
                decision=final_decision,
                anomaly_score=score,
                pending_ai=False
            )

            # update Redis cache
            try:
                import asyncio
                asyncio.run(cache_connection(updated))
            except Exception:
                pass

        finally:

            _scoring_queue.task_done()


# ============================================================
# Startup
# ============================================================

def start_background_workers() -> None:

    global _worker_started

    with _worker_lock:

        if _worker_started:
            return

        worker = threading.Thread(
            target=_worker_loop,
            daemon=True
        )

        worker.start()

        _worker_started = True