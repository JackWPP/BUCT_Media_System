"""
RabbitMQ event bus for inter-service communication.

Uses pika (sync) with asyncio.to_thread wrappers for async compatibility.
Graceful degradation: if RabbitMQ is unavailable, events are logged and skipped.
"""
from __future__ import annotations

import asyncio
import enum
import json
import logging
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


class EventType(str, enum.Enum):
    """Supported event types on the bus."""
    TAG_CREATED = "tag.created"
    TAG_UPDATED = "tag.updated"
    TAG_DELETED = "tag.deleted"
    CLASSIFICATION_UPDATED = "classification.updated"
    PHOTO_UPLOADED = "photo.uploaded"


# Type alias for async handlers
AsyncHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """
    Async-friendly RabbitMQ event bus (topic exchange, durable).

    Internally uses *pika* (blocking) connections, wrapped with
    ``asyncio.to_thread`` so the FastAPI event loop is never blocked.

    Connection parameters are hard-coded for the Visual-BUCT stack.
    If RabbitMQ is unreachable, publish/subscribe calls are silently
    degraded with a warning log — the application continues normally.
    """

    # RabbitMQ connection details
    _HOST = "localhost"
    _PORT = 5672
    _USER = "visual_buct"
    _PASS = "visual_buct_2026"
    _EXCHANGE = "visual_buct_events"
    _EXCHANGE_TYPE = "topic"

    def __init__(self) -> None:
        self._connection: Optional[Any] = None  # pika.BlockingConnection
        self._channel: Optional[Any] = None      # pika.channel.Channel
        self._subscribers: dict[str, list[AsyncHandler]] = {}
        self._consumer_connection: Optional[Any] = None
        self._consumer_channel: Optional[Any] = None
        self._connected = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_connection(self) -> bool:
        """Create a blocking pika connection if one doesn't exist.

        Returns ``True`` if a usable channel is available.
        """
        if self._connected and self._channel and self._channel.is_open:
            return True
        try:
            import pika  # noqa: F811 — local import to allow module load when pika missing

            credentials = pika.PlainCredentials(self._USER, self._PASS)
            params = pika.ConnectionParameters(
                host=self._HOST,
                port=self._PORT,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300,
            )
            self._connection = pika.BlockingConnection(params)
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=self._EXCHANGE,
                exchange_type=self._EXCHANGE_TYPE,
                durable=True,
            )
            self._connected = True
            logger.info("EventBus connected to RabbitMQ at %s:%s", self._HOST, self._PORT)
            return True
        except Exception as exc:
            logger.warning("EventBus: cannot connect to RabbitMQ — %s", exc)
            self._connected = False
            return False

    def _close_connection(self) -> None:
        """Best-effort close of the blocking connection."""
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass
        self._connection = None
        self._channel = None
        self._connected = False

    # ------------------------------------------------------------------
    # Sync core (called via asyncio.to_thread from async wrappers)
    # ------------------------------------------------------------------

    def _publish_sync(self, event_type: EventType | str, data: dict[str, Any]) -> bool:
        """Publish a single message. Returns True on success."""
        routing_key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        if not self._ensure_connection():
            logger.warning("EventBus: skipping publish(%s) — no connection", routing_key)
            return False
        try:
            body = json.dumps(data, ensure_ascii=False, default=str)
            self._channel.basic_publish(
                exchange=self._EXCHANGE,
                routing_key=routing_key,
                body=body.encode("utf-8"),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent
                    content_type="application/json",
                ),
            )
            logger.debug("EventBus: published %s (%d bytes)", routing_key, len(body))
            return True
        except Exception as exc:
            logger.warning("EventBus: publish(%s) failed — %s", routing_key, exc)
            self._close_connection()
            return False

    def _subscribe_sync(self, event_type: EventType | str, queue_name: str) -> bool:
        """Declare a queue and bind it to the exchange for the given routing key."""
        routing_key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        if not self._ensure_connection():
            logger.warning("EventBus: skipping subscribe(%s) — no connection", routing_key)
            return False
        try:
            self._channel.queue_declare(queue=queue_name, durable=True)
            self._channel.queue_bind(
                exchange=self._EXCHANGE,
                queue=queue_name,
                routing_key=routing_key,
            )
            logger.info("EventBus: subscribed queue=%s to %s", queue_name, routing_key)
            return True
        except Exception as exc:
            logger.warning("EventBus: subscribe(%s) failed — %s", routing_key, exc)
            return False

    def _start_consumer_sync(self) -> None:
        """Blocking consumer loop — runs in a dedicated thread."""
        if not self._ensure_connection():
            logger.warning("EventBus: cannot start consumer — no connection")
            return
        try:
            for method, properties, body in self._connection.consume(inactivity_timeout=1):
                if method is None:
                    # Inactivity timeout — just loop again (allows graceful shutdown)
                    continue
                routing_key = method.routing_key
                try:
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    data = {"raw": body.decode("utf-8", errors="replace")}

                handlers = self._subscribers.get(routing_key, [])
                for handler in handlers:
                    try:
                        # Handlers are async coroutines; schedule them
                        asyncio.get_event_loop().create_task(handler(data))
                    except RuntimeError:
                        # No running loop (shouldn't happen in normal operation)
                        logger.warning("EventBus: no event loop for handler on %s", routing_key)
                    except Exception as exc:
                        logger.error("EventBus: handler error on %s — %s", routing_key, exc)

                self._channel.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as exc:
            logger.warning("EventBus: consumer exited — %s", exc)

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def publish(self, event_type: EventType | str, data: dict[str, Any]) -> bool:
        """Publish an event to the exchange (async wrapper)."""
        return await asyncio.to_thread(self._publish_sync, event_type, data)

    async def subscribe(
        self,
        event_type: EventType | str,
        handler: AsyncHandler,
        queue_name: str | None = None,
    ) -> bool:
        """Subscribe an async handler to an event type.

        Args:
            event_type: The event routing key.
            handler:    An async callable that receives the event data dict.
            queue_name: Explicit queue name. Defaults to ``"q.visual_buct.<routing_key>"``.
        """
        routing_key = event_type.value if isinstance(event_type, EventType) else str(event_type)
        self._subscribers.setdefault(routing_key, []).append(handler)
        q_name = queue_name or f"q.visual_buct.{routing_key}"
        return await asyncio.to_thread(self._subscribe_sync, event_type, q_name)

    async def start_consuming(self) -> None:
        """Start the consumer loop in a background thread."""
        await asyncio.to_thread(self._start_consumer_sync)

    async def close(self) -> None:
        """Close all connections gracefully."""
        await asyncio.to_thread(self._close_connection)
        self._subscribers.clear()
        logger.info("EventBus: connections closed")


# ---- Module-level singleton ----
_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Return (and lazily create) the global EventBus instance."""
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus
