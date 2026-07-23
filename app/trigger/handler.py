from app.bus import EventBus
from app.config import Settings
from app.db import get_workflows
from app.errors import NotFoundError
from app.models import DocumentEnvelope, WorkflowDefinition, WorkflowNode, WorkflowRun
from app.runs.service import RunService
from app.trigger.resolver import resolve_workflow_id


class TriggerHandler:
    """Single entry point every ingestion channel funnels into once a document is
    persisted: resolve which workflow it starts, then hand off to RunService.
    """

    def __init__(self, settings: Settings, bus: EventBus) -> None:
        self._settings = settings
        self._bus = bus

    async def handle(
        self, envelope: DocumentEnvelope, workflow_id: str | None = None
    ) -> tuple[WorkflowRun, bool]:
        resolved_id = resolve_workflow_id(envelope, self._settings, workflow_id)

        workflow_doc = await get_workflows().find_one(
            {"id": resolved_id}, sort=[("version", -1)]
        )
        if workflow_doc is None:
            raise NotFoundError(f"workflow '{resolved_id}' not found")

        workflow = WorkflowDefinition(
            id=workflow_doc["id"],
            version=workflow_doc["version"],
            nodes=[WorkflowNode(**node) for node in workflow_doc["nodes"]],
        )

        return await RunService(self._bus).start_run(envelope, workflow)
