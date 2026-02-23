import redis.asyncio as redis
import json
from typing import Optional


# Create async Redis client (connection pool automatically managed)
redis_client = redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
    max_connections=100
)


# ---------- SCORE CACHE ----------

def make_score_key(conn) -> str:
    return f"score:{conn.source_ip}:{conn.destination_ip}:{conn.destination_port}:{conn.protocol}"


async def get_cached_score(conn) -> Optional[float]:

    key = make_score_key(conn)

    score = await redis_client.get(key)

    if score is not None:
        return float(score)

    return None


async def cache_score(conn, score: float):

    key = make_score_key(conn)

    await redis_client.set(
        key,
        score,
        ex=600
    )


# ---------- CONNECTION CACHE ----------

def make_connection_key(connection_id: str) -> str:
    return f"connection:{connection_id}"


async def cache_connection(connection: dict):

    key = make_connection_key(connection["connection_id"])

    await redis_client.set(
        key,
        json.dumps(connection),
        ex=3600
    )


async def get_cached_connection(connection_id: str):

    key = make_connection_key(connection_id)

    data = await redis_client.get(key)

    if data:
        return json.loads(data)

    return None