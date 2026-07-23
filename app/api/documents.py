from typing import Any

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import JSONResponse

from app.api.runs import run_to_response
from app.api.schemas import DocumentListResponse, DocumentResponse, RunResponse
from app.bus import EventBus
from app.config import Settings
from app.db import get_documents, get_workflow_runs
from app.errors import NotFoundError, UnsupportedContentTypeError
from app.ingestion.service import IngestionService
from app.ingestion.upload import UploadAdapter
from app.storage import ObjectStorage
from app.trigger.handler import TriggerHandler

router = APIRouter(prefix="/documents", tags=["documents"])


def _to_response(doc: dict[str, Any]) -> DocumentResponse:
    return DocumentResponse(
        id=doc["id"],
        source=doc["source"],
        storage_key=doc["storage_key"],
        content_type=doc["content_type"],
        received_at=doc["received_at"],
        status=doc["status"],
        workflow_id=doc.get("workflow_id"),
        metadata=doc.get("metadata", {}),
    )


@router.post("", status_code=201)
async def create_document(
    request: Request, file: UploadFile, workflow_id: str | None = None
) -> JSONResponse:
    settings: Settings = request.app.state.settings
    if file.content_type not in settings.allowed_content_types:
        raise UnsupportedContentTypeError(
            f"content type '{file.content_type}' is not allowed"
        )

    storage: ObjectStorage = request.app.state.storage
    adapter = UploadAdapter(storage, max_bytes=settings.max_upload_size_bytes)
    envelope = await adapter.to_envelope(file)

    bus: EventBus = request.app.state.bus
    trigger_handler = TriggerHandler(settings, bus)
    result = await IngestionService(trigger_handler).ingest(
        envelope, workflow_id=workflow_id
    )

    status_code = 200 if result.is_duplicate else 201
    return JSONResponse(
        status_code=status_code,
        content={
            "document_id": result.document["id"],
            "status": str(result.document["status"]),
            "duplicate": result.is_duplicate,
            "run_id": result.run.id if result.run else None,
        },
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str) -> DocumentResponse:
    doc = await get_documents().find_one({"id": document_id})
    if doc is None:
        raise NotFoundError(f"document '{document_id}' not found")
    return _to_response(doc)


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    status: str | None = None,
    source: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> DocumentListResponse:
    query: dict[str, Any] = {}
    if status is not None:
        query["status"] = status
    if source is not None:
        query["source"] = source

    collection = get_documents()
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("received_at", -1).skip(offset).limit(limit)
    items = [_to_response(doc) async for doc in cursor]

    return DocumentListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{document_id}/runs", response_model=list[RunResponse])
async def list_document_runs(document_id: str) -> list[RunResponse]:
    cursor = get_workflow_runs().find({"document_id": document_id})
    return [run_to_response(run) async for run in cursor]
