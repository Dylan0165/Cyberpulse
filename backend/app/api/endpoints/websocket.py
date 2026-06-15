"""WebSocket endpoints — real-time scan output and AI analysis streaming."""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import redis.asyncio as aioredis
from sqlalchemy import select

from app.core.config import get_settings
from app.core.auth import _decode_token
from app.core.database import async_session
from app.models.scan import Scan

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

HEARTBEAT_INTERVAL = 25  # seconds

# Demo/student bucket — scans here are public (keeps the live demo working).
_STUDENT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _authorize_scan_ws(websocket: WebSocket, scan_id: str, token: str) -> bool:
    """Reject the WS unless the caller may watch this scan.

    Auth source: the `?token=` query param, else the httpOnly `cp_token`
    cookie sent automatically with the same-origin WS handshake.

    Policy:
      - scan not found            → close 4004
      - demo/student scan (NULL or _STUDENT_USER_ID) → always allowed
      - private scan, owner match → allowed
      - private scan, no/wrong owner → close 4003

    Fails OPEN on unexpected errors (transient DB issues must not lock out a
    legitimate viewer; the REST layer already gates the sensitive report data).
    """
    try:
        try:
            sid = uuid.UUID(scan_id)
        except (ValueError, TypeError):
            await websocket.close(code=4004)
            return False

        async with async_session() as db:
            result = await db.execute(select(Scan).where(Scan.id == sid))
            scan = result.scalar_one_or_none()

        if scan is None:
            await websocket.close(code=4004)
            return False

        # Demo/student scans are public — anyone may watch.
        if scan.user_id is None or scan.user_id == _STUDENT_USER_ID:
            return True

        # Private scan: require a token whose subject matches the owner.
        jwt_token = token or websocket.cookies.get("cp_token", "")
        payload = _decode_token(jwt_token) if jwt_token else None
        sub = payload.get("sub") if payload else None
        if sub and str(sub) == str(scan.user_id):
            return True

        await websocket.close(code=4003)
        return False
    except Exception as exc:  # noqa: BLE001 — fail open, never lock out on errors
        logger.warning("WS auth check errored for scan %s (allowing): %s", scan_id, exc)
        return True


async def _relay(websocket: WebSocket, channel: str, redis_client: aioredis.Redis):
    """Subscribe to a Redis pub/sub channel and relay messages to the WebSocket."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    last_msg = asyncio.get_event_loop().time()
    try:
        while True:
            now = asyncio.get_event_loop().time()
            if now - last_msg >= HEARTBEAT_INTERVAL:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                    last_msg = now
                except Exception:
                    break

            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.05)
            if msg and msg["type"] == "message":
                try:
                    data = json.loads(msg["data"])
                    await websocket.send_json(data)
                    last_msg = asyncio.get_event_loop().time()
                    if data.get("type") in ("scan_complete", "scan_failed", "scan_cancelled"):
                        await asyncio.sleep(0.3)
                        break
                except Exception:
                    pass

            await asyncio.sleep(0.02)
    finally:
        await pubsub.unsubscribe(channel)
        try:
            await pubsub.aclose()
        except Exception:
            pass


@router.websocket("/ws/scan/{scan_id}")
async def scan_websocket(
    websocket: WebSocket,
    scan_id: str,
    token: str = Query(default=""),
):
    """
    Stream real-time scan events to the frontend.

    Events published by scan_tasks.py to `scan:{scan_id}:live`:
      scan_start, phase_start, phase_skip, tool_start, tool_done,
      phase_complete, scan_complete, error, heartbeat
    """
    if not await _authorize_scan_ws(websocket, scan_id, token):
        return
    await websocket.accept()
    logger.info("WS /scan/%s connected", scan_id)

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    # Replay existing log on connect (so page refresh shows history)
    try:
        cached = await redis_client.lrange(f"scan:{scan_id}:log", 0, -1)
        for raw in cached[-50:]:  # last 50 events max
            try:
                await websocket.send_json(json.loads(raw))
            except Exception:
                pass
    except Exception:
        pass

    stream = asyncio.create_task(
        _relay(websocket, f"scan:{scan_id}:live", redis_client)
    )
    try:
        while not stream.done():
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                stream.cancel()
                break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WS /scan/%s error: %s", scan_id, exc)
    finally:
        stream.cancel()
        await redis_client.aclose()
        logger.info("WS /scan/%s closed", scan_id)


@router.websocket("/ws/analysis/{scan_id}")
async def analysis_websocket(
    websocket: WebSocket,
    scan_id: str,
    token: str = Query(default=""),
):
    """
    Stream AI analysis tokens to the frontend.
    Publishes from `scan:{scan_id}:analysis` — {"type":"token","token":"..."}.
    """
    if not await _authorize_scan_ws(websocket, scan_id, token):
        return
    await websocket.accept()
    logger.info("WS /analysis/%s connected", scan_id)

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    stream = asyncio.create_task(
        _relay(websocket, f"scan:{scan_id}:analysis", redis_client)
    )
    try:
        while not stream.done():
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                stream.cancel()
                break
    except WebSocketDisconnect:
        pass
    finally:
        stream.cancel()
        await redis_client.aclose()
