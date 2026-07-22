from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app import db
from app.bus import EventBus, get_event_bus
from app.config import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    db.connect(settings)
    await db.ensure_indexes()

    bus: EventBus = get_event_bus(settings)
    await bus.start()

    app.state.settings = settings
    app.state.bus = bus

    yield

    await bus.stop()
    await db.close()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
