from datetime import UTC, datetime

import pytest
from pymongo.errors import DuplicateKeyError

from app.bus import InMemoryEventBus, get_event_bus
from app.config import RunMode, Settings
from app.db import connect, ensure_indexes, get_documents
from app.models import DocumentEnvelope, DocumentSource


@pytest.fixture
async def settings() -> Settings:
    s = Settings(mongodb_uri="mongodb://localhost:27017/docflow_test?replicaSet=rs0")
    connect(s)
    await ensure_indexes()
    await get_documents().delete_many({})
    return s


async def test_document_envelope_roundtrip_and_dedup(settings: Settings) -> None:
    envelope = DocumentEnvelope(
        id="doc-1",
        source=DocumentSource.UPLOAD,
        storage_key="raw/doc-1.pdf",
        content_type="application/pdf",
        received_at=datetime.now(UTC),
        dedup_key="dedup-abc",
    )

    await get_documents().insert_one(envelope.model_dump(mode="json"))

    fetched = await get_documents().find_one({"id": "doc-1"})
    assert fetched is not None
    assert fetched["dedup_key"] == "dedup-abc"

    duplicate = envelope.model_copy(update={"id": "doc-2"})
    with pytest.raises(DuplicateKeyError):
        await get_documents().insert_one(duplicate.model_dump(mode="json"))


def test_get_event_bus_returns_in_memory_for_inline() -> None:
    settings = Settings(run_mode=RunMode.INLINE)
    assert isinstance(get_event_bus(settings), InMemoryEventBus)
