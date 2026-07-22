from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.bus.base import Event, EventBus, Handler


class KafkaEventBus(EventBus):
    """EventBus implementation over Kafka/Redpanda via aiokafka, used for
    RUN_MODE=distributed. Skeleton only — methods raise NotImplementedError
    until the distributed transport is built out.
    """

    def __init__(self, brokers: str, consumer_group: str = "docflow-engine") -> None:
        self._brokers = brokers
        self._consumer_group = consumer_group
        self._producer: AIOKafkaProducer | None = None
        self._consumers: dict[str, AIOKafkaConsumer] = {}
        self._handlers: dict[str, list[Handler]] = {}

    async def start(self) -> None:
        """Start the producer and any consumer tasks for subscribed topics."""
        raise NotImplementedError

    async def stop(self) -> None:
        """Stop the producer and all consumer tasks, releasing Kafka connections."""
        raise NotImplementedError

    async def publish(self, topic: str, event: Event) -> None:
        """Serialize and produce `event` onto `topic`."""
        raise NotImplementedError

    async def subscribe(self, topic: str, handler: Handler) -> None:
        """Register `handler` to be invoked for messages consumed from `topic`."""
        raise NotImplementedError
