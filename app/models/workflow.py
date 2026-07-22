from typing import Any

from pydantic import BaseModel


class WorkflowNode(BaseModel):
    id: str
    type: str
    config: dict[str, Any] = {}
    depends_on: list[str] = []


class WorkflowDefinition(BaseModel):
    id: str
    version: int
    nodes: list[WorkflowNode]
