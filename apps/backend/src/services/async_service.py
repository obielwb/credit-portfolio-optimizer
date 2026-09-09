

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from src.schema import OptimizationJobSchema
from src.utils import (
    build_rabbitmq_url,
    get_optimization_queue_name,
    get_rabbitmq_heartbeat,
)

MessageHandler = Callable[[dict[str, Any]], Awaitable[None]]


def _env_flag(name: str, default: str) -> bool:
    """Interpreta variable de ambiente como flag booleana."""
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y"}


def build_async_queue_config() -> "AsyncQueueConfig":


    return AsyncQueueConfig(
        use_mock=_env_flag("ASYNC_QUEUE_USE_MOCK", "true"),
    )


@dataclass(slots=True)
class AsyncQueueConfig:


    amqp_url: str = field(default_factory=build_rabbitmq_url)
    queue_name: str = field(default_factory=get_optimization_queue_name)
    use_mock: bool = True


class AsyncQueueService:


    def __init__(self, config: AsyncQueueConfig | None = None) -> None:

        self._config = config or build_async_queue_config()
        self._mock_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._published_messages: list[dict[str, Any]] = []

    @property
    def queue_name(self) -> str:
        """Optimization queue name."""
        return self._config.queue_name

    @property
    def amqp_url(self) -> str:
        """URL AMQP configured."""
        return self._config.amqp_url

    @property
    def published_messages(self) -> list[dict[str, Any]]:

        return list(self._published_messages)

    @property
    def use_mock(self) -> bool:
        """Whether the in-memory mock queue is active."""
        return self._config.use_mock

    async def publish_optimization_job(
        self, job: OptimizationJobSchema | dict[str, Any]
    ) -> dict[str, Any]:


        payload = (
            job.model_dump() if isinstance(job, OptimizationJobSchema) else dict(job)
        )
        message = {"queue": self.queue_name, "payload": payload}
        self._published_messages.append(message)

        if self._config.use_mock:
            await self._mock_queue.put(payload)
            return {"status": "queued", "queue": self.queue_name, "payload": payload}

        await self._publish_rabbitmq(payload)
        return {"status": "queued", "queue": self.queue_name, "payload": payload}

    async def consume_optimization_jobs(
        self,
        handler: MessageHandler,
        *,
        max_messages: int | None = None,
        block: bool = False,
    ) -> int:


        if self._config.use_mock:
            return await self._consume_mock(
                handler,
                max_messages=max_messages,
                block=block,
            )

        return await self._consume_rabbitmq(
            handler,
            max_messages=max_messages,
            block=block,
        )

    async def _publish_rabbitmq(self, payload: dict[str, Any]) -> None:
        """Publish a message to RabbitMQ."""
        import aio_pika

        connection = await aio_pika.connect_robust(
            self._config.amqp_url,
            heartbeat=get_rabbitmq_heartbeat(),
        )
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(self.queue_name, durable=True)
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(payload).encode("utf-8"),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=self.queue_name,
            )

    async def _handle_rabbitmq_message(
        self,
        message: Any,
        handler: MessageHandler,
    ) -> None:


        import aio_pika

        payload = json.loads(message.body.decode("utf-8"))
        try:
            await handler(payload)
        except Exception:
            try:
                await message.nack(requeue=False)
            except aio_pika.exceptions.AMQPError:
                pass
            raise

        try:
            await message.ack()
        except aio_pika.exceptions.AMQPError:

            pass

    async def _consume_rabbitmq(
        self,
        handler: MessageHandler,
        *,
        max_messages: int | None,
        block: bool,
    ) -> int:
        """Consume RabbitMQ messages and delegate them to the handler."""
        import aio_pika

        if block:
            return await self._consume_rabbitmq_continuous(
                handler,
                max_messages=max_messages,
            )

        connection = await aio_pika.connect_robust(
            self._config.amqp_url,
            heartbeat=get_rabbitmq_heartbeat(),
        )
        processed = 0

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)
            queue = await channel.declare_queue(self.queue_name, durable=True)

            while True:
                if max_messages is not None and processed >= max_messages:
                    break

                message = await queue.get(timeout=0.2, fail=False)
                if message is None:
                    break

                await self._handle_rabbitmq_message(message, handler)
                processed += 1

        return processed

    async def _consume_rabbitmq_continuous(
        self,
        handler: MessageHandler,
        *,
        max_messages: int | None,
    ) -> int:


        import aio_pika

        processed = 0

        while max_messages is None or processed < max_messages:
            try:
                connection = await aio_pika.connect_robust(
                    self._config.amqp_url,
                    heartbeat=get_rabbitmq_heartbeat(),
                )
                async with connection:
                    channel = await connection.channel()
                    await channel.set_qos(prefetch_count=1)
                    queue = await channel.declare_queue(self.queue_name, durable=True)

                    async with queue.iterator() as queue_iter:
                        async for message in queue_iter:
                            if max_messages is not None and processed >= max_messages:
                                return processed
                            await self._handle_rabbitmq_message(message, handler)
                            processed += 1
            except aio_pika.exceptions.AMQPError:
                await asyncio.sleep(2)
                continue

        return processed

    async def _consume_mock(
        self,
        handler: MessageHandler,
        *,
        max_messages: int | None,
        block: bool,
    ) -> int:
        """Consume messages from the in-memory mock queue."""
        processed = 0

        while True:
            if max_messages is not None and processed >= max_messages:
                break

            if block:
                payload = await self._mock_queue.get()
            elif self._mock_queue.empty():
                break
            else:
                payload = await self._mock_queue.get()

            await handler(payload)
            processed += 1

            if not block and self._mock_queue.empty():
                break

        return processed

    def snapshot(self) -> dict[str, Any]:


        snapshot: dict[str, Any] = {
            "queue_name": self.queue_name,
            "amqp_url": self.amqp_url,
            "use_mock": self._config.use_mock,
            "published_messages": self.published_messages,
        }
        if self._config.use_mock:
            snapshot["pending_messages"] = self._mock_queue.qsize()
        return snapshot


DEFAULT_ASYNC_QUEUE_SERVICE = AsyncQueueService()
