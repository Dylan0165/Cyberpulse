"""WebSocket endpoint for real-time scan output streaming."""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import httpx
import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

HEARTBEAT_INTERVAL = 30  # seconds


async def _verify_clerk_token(token: str) -> Optional[str]:
    """Verify a Clerk JWT token and return the user's clerk_id, or None if invalid."""
    if not token or not settings.clerk_secret_key:
        # In development / no-auth mode allow any connection
        return "anonymous"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"https://api.clerk.dev/v1/tokens/verify",
                headers={
                    "Authorization": f"Bearer {settings.clerk_secret_key}",
                    "Content-Type": "application/json",
                },
                params={"token": token},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("sub") or data.get("user_id")
    except Exception as e:
        logger.warning("Clerk token verification error: %s", e)
    return None


async def _stream_redis_to_ws(
    websocket: WebSocket,
    channel: str,
    redis_client: aioredis.Redis,
) -> None:
    """Subscribe to a Redis pub/sub channel and forward messages to the WebSocket.
    Sends a heartbeat ping every HEARTBEAT_INTERVAL seconds."""
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)

    try:
        last_msg = asyncio.get_event_loop().time()

        while True:
            now = asyncio.get_event_loop().time()

            # Heartbeat: send a ping if idle too long
            if now - last_msg >= HEARTBEAT_INTERVAL:
                try:
                    await websocket.send_json({"type": "heartbeat"})
                    last_msg = now
                except Exception:
                    break

            # Check for new Redis messages (non-blocking, 50ms timeout)
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=0.05
            )
            if message and message["type"] == "message":
                raw = message["data"]
                try:
                    data = json.loads(raw)
                    await websocket.send_json(data)
                    last_msg = asyncio.get_event_loop().time()

                    # If scan is terminal, send final message and stop streaming
                    if data.get("type") in ("scan_complete", "scan_failed", "scan_cancelled"):
                        await asyncio.sleep(0.2)
                        break
                except Exception as exc:
                    logger.debug("Failed to forward ws message: %s", exc)

            # Small sleep to avoid busy-wait
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
    """Stream real-time scan output.

    Authenticate via Clerk JWT in the `?token=` query parameter.
    Subscribes to `scan:{scan_id}:live` Redis channel.
    """
    clerk_id = await _verify_clerk_token(token)
    if clerk_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    logger.info("WS /scan/%s connected (user=%s)", scan_id, clerk_id)

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)

    # Replay last 5 minutes of messages from Redis stream (if stored)
    try:
        cached = await redis_client.lrange(f"scan:{scan_id}:log", 0, -1)
        for raw in cached:
            try:
                await websocket.send_json(json.loads(raw))
            except Exception:
                pass
    except Exception:
        pass

    try:
        stream_task = asyncio.create_task(
            _stream_redis_to_ws(websocket, f"scan:{scan_id}:live", redis_client)
        )
        # Wait for client disconnect OR stream end
        while not stream_task.done():
            try:
                # ping/pong or client-sent messages (ignore content)
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                stream_task.cancel()
                break

    except WebSocketDisconnect:
        logger.info("WS /scan/%s disconnected", scan_id)
    except Exception as exc:
        logger.error("WS /scan/%s error: %s", scan_id, exc)
    finally:
        await redis_client.aclose()


@router.websocket("/ws/analysis/{scan_id}")
async def analysis_websocket(
    websocket: WebSocket,
    scan_id: str,
    token: str = Query(default=""),
):
    """Stream AI analysis results.

    Subscribes to `scan:{scan_id}:analysis` Redis channel.
    """
    clerk_id = await _verify_clerk_token(token)
    if clerk_id is None:
        await websocket.close(code=4401, reason="Unauthorized")
        return

    await websocket.accept()
    logger.info("WS /analysis/%s connected (user=%s)", scan_id, clerk_id)

    redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
    try:
        stream_task = asyncio.create_task(
            _stream_redis_to_ws(websocket, f"scan:{scan_id}:analysis", redis_client)
        )
        while not stream_task.done():
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                stream_task.cancel()
                break
    except WebSocketDisconnect:
        logger.info("WS /analysis/%s disconnected", scan_id)
    except Exception as exc:
        logger.error("WS /analysis/%s error: %s", scan_id, exc)
    finally:
        await redis_client.aclose()



@router.websocket("/ws/scan/{scan_id}")
async def scan_websocket(websocket: WebSocket, scan_id: str):
    """
    Stream real-time scan output to the frontend via WebSocket.
    Subscribes to the Redis pub/sub channel for this scan.
    """
    await websocket.accept()

    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    channel = f"scan:{scan_id}:live"

    try:
        await pubsub.subscribe(channel)
        logger.info(f"WebSocket connected for scan {scan_id}")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await websocket.send_json(data)
                except (json.JSONDecodeError, Exception):
                    pass

            # Check if scan is complete
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for scan {scan_id}")
    except Exception as e:
        logger.error(f"WebSocket error for scan {scan_id}: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.close()


@router.websocket("/ws/analysis/{scan_id}")
async def analysis_websocket(websocket: WebSocket, scan_id: str):
    """
    Stream AI analysis results in real-time.
    Used when the backend streams Claude's response to the frontend.
    """
    await websocket.accept()

    redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    pubsub = redis.pubsub()
    channel = f"scan:{scan_id}:analysis"

    try:
        await pubsub.subscribe(channel)
        logger.info(f"Analysis WebSocket connected for scan {scan_id}")

        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                try:
                    await websocket.send_text(message["data"])
                except Exception:
                    break

            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info(f"Analysis WebSocket disconnected for scan {scan_id}")
    except Exception as e:
        logger.error(f"Analysis WebSocket error: {e}")
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.close()
        await redis.close()
