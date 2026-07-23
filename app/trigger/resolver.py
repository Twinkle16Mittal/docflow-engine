from app.config import Settings
from app.errors import UnresolvedWorkflowError
from app.models import DocumentEnvelope


def resolve_workflow_id(
    envelope: DocumentEnvelope, settings: Settings, workflow_id: str | None = None
) -> str:
    """Decide which workflow a document starts. Precedence:
    1. an explicit workflow_id passed with the request
    2. a static source->workflow mapping (Settings.source_workflow_map)
    3. a configured default workflow (Settings.default_workflow_id)
    Step 7 replaces (2) with match-rules stored on the workflow definition itself.
    """
    if workflow_id:
        return workflow_id

    mapped = settings.source_workflow_map.get(str(envelope.source))
    if mapped:
        return mapped

    if settings.default_workflow_id:
        return settings.default_workflow_id

    raise UnresolvedWorkflowError(
        f"no workflow could be resolved for document '{envelope.id}' "
        f"(source='{envelope.source}'); pass workflow_id explicitly, add it to "
        "SOURCE_WORKFLOW_MAP, or configure DEFAULT_WORKFLOW_ID"
    )
