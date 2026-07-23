from pydantic import BaseModel


class RunStartedEvent(BaseModel):
    event_id: str
    run_id: str
    workflow_id: str
    document_id: str


class NodeRunEvent(BaseModel):
    event_id: str
    run_id: str
    node_id: str
    node_type: str
    document_id: str
