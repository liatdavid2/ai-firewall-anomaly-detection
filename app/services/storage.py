from __future__ import annotations

import json
import uuid
import os
import threading
from typing import Optional, Dict, Any

# ============================================================
# File location
# ============================================================

DATA_DIR = "data"
CONNECTIONS_FILE = os.path.join(DATA_DIR, "connections.ndjson")

# Thread-safe append lock
_write_lock = threading.Lock()

# Optional in-memory index for fast lookup
_index: Dict[str, int] = {}
_index_loaded = False


# ============================================================
# Internal helpers
# ============================================================

def _ensure_file_exists() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(CONNECTIONS_FILE):
        open(CONNECTIONS_FILE, "a").close()


def _serialize_conn(conn) -> Dict[str, Any]:
    return {
        "source_ip": str(conn.source_ip),
        "destination_ip": str(conn.destination_ip),
        "destination_port": conn.destination_port,
        "protocol": conn.protocol,
        "timestamp": str(conn.timestamp),
    }


def _load_index() -> None:
    """
    Build in-memory index: connection_id -> file offset
    Fast lookup without scanning whole file every time.
    """

    global _index_loaded

    if _index_loaded:
        return

    _ensure_file_exists()

    with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:

        offset = 0

        for line in f:
            try:
                record = json.loads(line)
                _index[record["connection_id"]] = offset
            except Exception:
                pass

            offset = f.tell()

    _index_loaded = True


# ============================================================
# Public API
# ============================================================

def save_connection(
    conn,
    decision: str,
    anomaly_score: Optional[float],
    matched_policy: Optional[str],
    pending_ai: bool
) -> Dict[str, Any]:

    _ensure_file_exists()

    connection_id = str(uuid.uuid4())

    record = {
        "connection_id": connection_id,
        **_serialize_conn(conn),
        "decision": decision,
        "anomaly_score": anomaly_score,
        "matched_policy": matched_policy,
        "pending_ai": pending_ai,
    }

    line = json.dumps(record)

    with _write_lock:
        with open(CONNECTIONS_FILE, "a", encoding="utf-8") as f:

            offset = f.tell()

            f.write(line + "\n")

            _index[connection_id] = offset

    return record


def get_connection_by_id(connection_id: str) -> Optional[Dict[str, Any]]:

    _ensure_file_exists()

    _load_index()

    offset = _index.get(connection_id)

    if offset is None:
        return None

    with open(CONNECTIONS_FILE, "r", encoding="utf-8") as f:

        f.seek(offset)

        line = f.readline()

        try:
            return json.loads(line)
        except Exception:
            return None


def update_connection_decision(
    connection_id: str,
    decision: str,
    anomaly_score: Optional[float],
    pending_ai: bool
) -> Optional[Dict[str, Any]]:

    existing = get_connection_by_id(connection_id)

    if existing is None:
        return None

    updated = {
        **existing,
        "decision": decision,
        "anomaly_score": anomaly_score,
        "pending_ai": pending_ai,
    }

    # append updated version (immutable log)
    with _write_lock:
        with open(CONNECTIONS_FILE, "a", encoding="utf-8") as f:

            offset = f.tell()

            f.write(json.dumps(updated) + "\n")

            _index[connection_id] = offset

    return updated