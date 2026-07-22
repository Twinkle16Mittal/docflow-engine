from abc import ABC, abstractmethod
from typing import Any, Awaitable, Callable

Event = dict[str, Any]
Handler = Callable[[Event], Awaitable[None]]


class EventBus(ABC):
    """Abstraction over the event transport. All messaging in the platform goes
    through this interface — business logic must never call Kafka (or any other
    transport) directly.
    """

    @abstractmethod
    async def start(self) -> None:
        """Start any background consumers/producers needed by the bus."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop consumers/producers and release transport resources."""

    @abstractmethod
    async def publish(self, topic: str, event: Event) -> None:
        """Publish an event to a topic."""

    @abstractmethod
    async def subscribe(self, topic: str, handler: Handler) -> None:
        """Register a handler to be invoked for every event published to a topic."""
