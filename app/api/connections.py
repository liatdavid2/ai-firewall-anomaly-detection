from fastapi import APIRouter, HTTPException
import asyncio

from app.models.connection import (
    ConnectionRequest,
    ConnectionResponse,
    StoredConnection
)

from app.services.policy_engine import find_matching_policy
from app.core.decision import decide

from app.services.storage import (
    save_connection,
    get_connection_by_id,
    update_connection_decision
)

from app.services.ai_gateway import submit_for_scoring

# Redis cache (ASYNC)
from app.services.redis_cache import (
    get_cached_score,
    cache_score,
    cache_connection,
    get_cached_connection
)

router = APIRouter()


@router.post("/connections", response_model=ConnectionResponse)
async def submit_connection(conn: ConnectionRequest):

    # Run blocking policy evaluation in thread
    policy = await asyncio.to_thread(
        find_matching_policy,
        conn
    )

    # Deterministic allow/block
    if policy is not None and policy.action in ["allow", "block"]:

        decision = policy.action

        stored = await asyncio.to_thread(
            save_connection,
            conn,
            decision,
            None,
            policy.policy_id,
            False
        )

        await cache_connection(stored)

        return ConnectionResponse(**stored)

    # Save initial state (pending AI)
    stored = await asyncio.to_thread(
        save_connection,
        conn,
        "alert",
        None,
        (policy.policy_id if policy else None),
        True
    )

    # Check Redis cache first
    cached_score = await get_cached_score(conn)

    if cached_score is not None:

        final_decision = decide(policy, cached_score)

        updated = await asyncio.to_thread(
            update_connection_decision,
            stored["connection_id"],
            final_decision,
            cached_score,
            False
        )

        await cache_connection(updated)

        return ConnectionResponse(**updated)

    # Submit for AI scoring (thread-safe)
    result = await asyncio.to_thread(
        submit_for_scoring,
        stored["connection_id"],
        conn,
        (policy.policy_id if policy else None)
    )

    # Sync scoring path
    if result["mode"] == "sync":

        score = result["anomaly_score"]

        await cache_score(conn, score)

        final_decision = decide(policy, score)

        updated = await asyncio.to_thread(
            update_connection_decision,
            stored["connection_id"],
            final_decision,
            score,
            False
        )

        await cache_connection(updated)

        return ConnectionResponse(**updated)

    # Async scoring path (queued)
    await cache_connection(stored)

    return ConnectionResponse(**stored)


@router.get("/connections/{connection_id}", response_model=StoredConnection)
async def get_connection(connection_id: str):

    # Check Redis first
    cached = await get_cached_connection(connection_id)

    if cached is not None:
        return StoredConnection(**cached)

    # Load from storage (thread-safe)
    conn = await asyncio.to_thread(
        get_connection_by_id,
        connection_id
    )

    if conn is None:
        raise HTTPException(
            status_code=404,
            detail="not found"
        )

    await cache_connection(conn)

    return StoredConnection(**conn)