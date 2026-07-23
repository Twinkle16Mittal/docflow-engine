from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.db import get_documents
from app.models import DocumentEnvelope, DocumentStatus, WorkflowRun
from app.trigger.handler import TriggerHandler


@dataclass
class IngestionResult:
    document: dict[str, Any]
    is_duplicate: bool
    run: WorkflowRun | None = None


class IngestionService:
    def __init__(self, trigger_handler: TriggerHandler | None = None) -> None:
        self._trigger_handler = trigger_handler

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
            # A duplicate document must never trigger a new run.
            return IngestionResult(document=existing, is_duplicate=True)

        run = None
        if self._trigger_handler is not None:
            run, _ = await self._trigger_handler.handle(envelope, workflow_id=workflow_id)

        return IngestionResult(document=doc, is_duplicate=False, run=run)
