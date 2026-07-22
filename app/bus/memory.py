import asyncio

from app.bus.base import Event, EventBus, Handler


class InMemoryEventBus(EventBus):
    """Single-process EventBus backed by asyncio queues, used for RUN_MODE=inline.

    Each topic gets its own queue and dispatch loop; every event is delivered to
    every handler subscribed to that topic, in-process.
    """

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Event]] = {}
        self._handlers: dict[str, list[Handler]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running = False

    def _queue_for(self, topic: str) -> asyncio.Queue[Event]:
        return self._queues.setdefault(topic, asyncio.Queue())

    async def start(self) -> None:
        self._running = True
        for topic in self._handlers:
            self._ensure_dispatch_loop(topic)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        for task in self._tasks.values():
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._tasks.clear()

    async def publish(self, topic: str, event: Event) -> None:
        await self._queue_for(topic).put(event)

    async def subscribe(self, topic: str, handler: Handler) -> None:
        self._handlers.setdefault(topic, []).append(handler)
        if self._running:
            self._ensure_dispatch_loop(topic)

    def _ensure_dispatch_loop(self, topic: str) -> None:
        if topic not in self._tasks:
            self._tasks[topic] = asyncio.create_task(self._dispatch_loop(topic))

    async def _dispatch_loop(self, topic: str) -> None:
        queue = self._queue_for(topic)
        while True:
            event = await queue.get()
            for handler in self._handlers.get(topic, []):
                await handler(event)
