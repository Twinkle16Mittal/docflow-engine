from datetime import UTC, datetime
from uuid import uuid4

from pymongo.errors import DuplicateKeyError

from app.bus import EventBus
from app.constants import TOPIC_NODE_RUN, TOPIC_RUN_STARTED
from app.db import get_workflow_runs
from app.models import (
    DocumentEnvelope,
    NodeRunEvent,
    NodeState,
    NodeStatus,
    RunStartedEvent,
    RunStatus,
    WorkflowDefinition,
    WorkflowRun,
)


class RunService:
    def __init__(self, bus: EventBus) -> None:
        self._bus = bus

    async def start_run(
        self, document: DocumentEnvelope, workflow: WorkflowDefinition
    ) -> tuple[WorkflowRun, bool]:
        """Idempotent: a duplicate (document_id, workflow_id) trigger returns the
        existing run with created=False and publishes nothing."""
        entry_node_ids = {node.id for node in workflow.nodes if not node.depends_on}
        node_states = {
            node.id: NodeState(
                status=NodeStatus.READY
                if node.id in entry_node_ids
                else NodeStatus.PENDING
            )
            for node in workflow.nodes
        }

        now = datetime.now(UTC)
        run = WorkflowRun(
            id=str(uuid4()),
            workflow_id=workflow.id,
            workflow_version=workflow.version,
            document_id=document.id,
            status=RunStatus.RUNNING,
            node_states=node_states,
            created_at=now,
            updated_at=now,
        )

        try:
            # Persist before publishing — no event may reference an unwritten run.
            await get_workflow_runs().insert_one(run.model_dump(mode="python"))
        except DuplicateKeyError:
            existing = await get_workflow_runs().find_one(
                {"document_id": document.id, "workflow_id": workflow.id}
            )
            assert existing is not None
            return WorkflowRun(**existing), False

        await self._bus.publish(
            TOPIC_RUN_STARTED,
            RunStartedEvent(
                event_id=str(uuid4()),
                run_id=run.id,
                workflow_id=run.workflow_id,
                document_id=run.document_id,
            ).model_dump(mode="json"),
        )

        node_type_by_id = {node.id: node.type for node in workflow.nodes}
        for node_id in entry_node_ids:
            await self._bus.publish(
                TOPIC_NODE_RUN,
                NodeRunEvent(
                    event_id=str(uuid4()),
                    run_id=run.id,
                    node_id=node_id,
                    node_type=node_type_by_id[node_id],
                    document_id=run.document_id,
                ).model_dump(mode="json"),
            )

        return run, True
