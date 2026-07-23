from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.db import get_documents
from app.models import DocumentEnvelope, DocumentStatus


@dataclass
class IngestionResult:
    document: dict[str, Any]
    is_duplicate: bool


class IngestionService:
    async def ingest(
        self, envelope: DocumentEnvelope, workflow_id: str | None = None
    ) -> IngestionResult:
        now = datetime.now(UTC)
        doc: dict[str, Any] = envelope.model_dump(mode="python")
        doc["workflow_id"] = workflow_id
        doc["status"] = DocumentStatus.RECEIVED
        doc["created_at"] = now
        doc["updated_at"] = now

        try:
            await get_documents().insert_one(doc)
        except DuplicateKeyError:
            existing = await get_documents().find_one({"dedup_key": envelope.dedup_key})
            assert existing is not None
            return IngestionResult(document=existing, is_duplicate=True)

        # TODO(step-3): fire the trigger/startRun hook here (publish RUN_STARTED)
        # once the engine exists. Ingestion's responsibility stops at persisting
        # the normalized document.
        return IngestionResult(document=doc, is_duplicate=False)
