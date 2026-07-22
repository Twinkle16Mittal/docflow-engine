from app.bus.base import EventBus
from app.bus.kafka import KafkaEventBus
from app.bus.memory import InMemoryEventBus
from app.config import RunMode, Settings


def get_event_bus(settings: Settings) -> EventBus:
    if settings.run_mode == RunMode.INLINE:
        return InMemoryEventBus()
    return KafkaEventBus(brokers=settings.kafka_brokers)
