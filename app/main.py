from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app import db
from app.api.documents import router as documents_router
from app.api.error_handlers import register_error_handlers
from app.api.middleware import CorrelationIdMiddleware
from app.api.runs import router as runs_router
from app.api.workflows import router as workflows_router
from app.bus import EventBus, get_event_bus
from app.config import Settings
from app.logging_config import configure_logging
from app.storage import ObjectStorage

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = Settings()
    db.connect(settings)
    await db.ensure_indexes()

    bus: EventBus = get_event_bus(settings)
    await bus.start()

    app.state.settings = settings
    app.state.bus = bus
    app.state.storage = ObjectStorage(settings)

    yield

    await bus.stop()
    await db.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)
register_error_handlers(app)

app.include_router(documents_router)
app.include_router(workflows_router)
app.include_router(runs_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
