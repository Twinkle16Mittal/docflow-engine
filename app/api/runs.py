from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.api.schemas import ManualRunRequest, ManualRunResponse, RunResponse
from app.bus import EventBus
from app.config import Settings
from app.db import get_documents, get_workflow_runs
from app.errors import NotFoundError
from app.models import DocumentEnvelope
from app.trigger.handler import TriggerHandler

router = APIRouter(prefix="/runs", tags=["runs"])


def run_to_response(run: dict[str, Any]) -> RunResponse:
    return RunResponse(
        id=run["id"],
        workflow_id=run["workflow_id"],
        workflow_version=run["workflow_version"],
        document_id=run["document_id"],
        status=run["status"],
        node_states=run.get("node_states", {}),
    )


@router.post("", status_code=201)
async def create_run(request: Request, payload: ManualRunRequest) -> JSONResponse:
    doc = await get_documents().find_one({"id": payload.document_id})
    if doc is None:
        raise NotFoundError(f"document '{payload.document_id}' not found")

    envelope = DocumentEnvelope(
        id=doc["id"],
        source=doc["source"],
        storage_key=doc["storage_key"],
        content_type=doc["content_type"],
        received_at=doc["received_at"],
        dedup_key=doc["dedup_key"],
        metadata=doc.get("metadata", {}),
    )

    settings: Settings = request.app.state.settings
    bus: EventBus = request.app.state.bus
    run, created = await TriggerHandler(settings, bus).handle(
        envelope, workflow_id=payload.workflow_id
    )

    body = ManualRunResponse(run_id=run.id, created=created)
    return JSONResponse(status_code=201 if created else 200, content=body.model_dump())


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: str) -> RunResponse:
    run = await get_workflow_runs().find_one({"id": run_id})
    if run is None:
        raise NotFoundError(f"run '{run_id}' not found")
    return run_to_response(run)
