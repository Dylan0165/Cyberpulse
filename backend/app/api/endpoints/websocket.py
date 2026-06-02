"""WebSocket endpoints — real-time scan output and AI analysis streaming."""

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

HEARTBEAT_INTERVAL = 25  # seconds


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
