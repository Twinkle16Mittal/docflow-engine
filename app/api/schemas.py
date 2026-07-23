from datetime import datetime
from typing import Any

from pydantic import BaseModel


class WorkflowNodeIn(BaseModel):
    id: str
    type: str
    config: dict[str, Any] = {}
    depends_on: list[str] = []


class WorkflowCreateRequest(BaseModel):
    id: str
    nodes: list[WorkflowNodeIn]


class WorkflowResponse(BaseModel):
    id: str
    version: int
    nodes: list[WorkflowNodeIn]


class DocumentCreateResponse(BaseModel):
    document_id: str
    status: str
    duplicate: bool


class DocumentResponse(BaseModel):
    id: str
    source: str
    storage_key: str
    content_type: str
    received_at: datetime
    status: str
    workflow_id: str | None = None
    metadata: dict[str, Any] = {}


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class RunResponse(BaseModel):
    id: str
    workflow_id: str
    workflow_version: int
    document_id: str
    status: str
    node_states: dict[str, Any] = {}
