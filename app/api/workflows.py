from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter

from app.api.schemas import WorkflowCreateRequest, WorkflowNodeIn, WorkflowResponse
from app.dag import validate_dag
from app.db import get_workflows
from app.errors import NotFoundError
from app.models import WorkflowNode

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _to_response(doc: dict[str, Any]) -> WorkflowResponse:
    return WorkflowResponse(
        id=doc["id"],
        version=doc["version"],
        nodes=[WorkflowNodeIn(**node) for node in doc["nodes"]],
    )


@router.post("", status_code=201, response_model=WorkflowResponse)
async def create_workflow(payload: WorkflowCreateRequest) -> WorkflowResponse:
    nodes = [WorkflowNode(**node.model_dump()) for node in payload.nodes]
    validate_dag(nodes)

    collection = get_workflows()
    latest = await collection.find_one({"id": payload.id}, sort=[("version", -1)])
    version = (latest["version"] + 1) if latest else 1

    doc = {
        "id": payload.id,
        "version": version,
        "nodes": [node.model_dump() for node in nodes],
        "created_at": datetime.now(UTC),
    }
    await collection.insert_one(doc)

    return _to_response(doc)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str) -> WorkflowResponse:
    doc = await get_workflows().find_one(
        {"id": workflow_id}, sort=[("version", -1)]
    )
    if doc is None:
        raise NotFoundError(f"workflow '{workflow_id}' not found")
    return _to_response(doc)


@router.get("", response_model=list[WorkflowResponse])
async def list_workflows() -> list[WorkflowResponse]:
    cursor = get_workflows().find().sort([("id", 1), ("version", -1)])
    return [_to_response(doc) async for doc in cursor]
