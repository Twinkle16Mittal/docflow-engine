from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import NodeStatus, RunStatus


class NodeState(BaseModel):
    status: NodeStatus = NodeStatus.PENDING
    output: Any | None = None
    attempts: int = 0
    completed_deps: list[str] = []


class WorkflowRun(BaseModel):
    id: str
    workflow_id: str
    workflow_version: int
    document_id: str
    status: RunStatus = RunStatus.PENDING
    node_states: dict[str, NodeState] = {}
    created_at: datetime
    updated_at: datetime
