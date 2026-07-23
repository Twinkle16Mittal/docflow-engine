import io

import pytest
from fastapi.testclient import TestClient

import app.db as db
from app.bus.base import Event, EventBus, Handler
from app.config import Settings
from app.constants import TOPIC_NODE_RUN, TOPIC_RUN_STARTED
from app.models import DocumentEnvelope, DocumentSource, WorkflowDefinition, WorkflowNode
from app.runs.service import RunService

PDF_BYTES = b"%PDF-1.4 fake pdf content for testing\n%%EOF"

TEST_MONGODB_URI = "mongodb://localhost:27017/docflow_test?replicaSet=rs0"


@pytest.fixture
async def connected_db():
    """RunService tests below call app.db directly instead of going through
    TestClient's HTTP layer. AsyncMongoClient binds to whichever event loop it
    first runs on, so this connects fresh on the loop the async test itself
    runs on, rather than reusing a connection bound to TestClient's loop."""
    db.connect(Settings(mongodb_uri=TEST_MONGODB_URI))
    await db.ensure_indexes()
    yield
    await db.close()


class RecordingEventBus(EventBus):
    def __init__(self) -> None:
        self.published: list[tuple[str, Event]] = []

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def publish(self, topic: str, event: Event) -> None:
        self.published.append((topic, event))

    async def subscribe(self, topic: str, handler: Handler) -> None:
        pass


def _envelope(doc_id: str = "doc-1") -> DocumentEnvelope:
    from datetime import UTC, datetime

    return DocumentEnvelope(
        id=doc_id,
        source=DocumentSource.UPLOAD,
        storage_key=f"upload/{doc_id}.pdf",
        content_type="application/pdf",
        received_at=datetime.now(UTC),
        dedup_key=f"dedup-{doc_id}",
        metadata={},
    )


def _workflow(*, two_entry_nodes: bool = False) -> WorkflowDefinition:
    if two_entry_nodes:
        nodes = [
            WorkflowNode(id="a", type="extract"),
            WorkflowNode(id="b", type="extract"),
            WorkflowNode(id="c", type="merge", depends_on=["a", "b"]),
        ]
    else:
        nodes = [
            WorkflowNode(id="a", type="extract"),
            WorkflowNode(id="b", type="classify", depends_on=["a"]),
        ]
    return WorkflowDefinition(id="wf-direct", version=1, nodes=nodes)


def _create_workflow(client: TestClient, workflow_id: str, nodes: list[dict]):
    response = client.post("/workflows", json={"id": workflow_id, "nodes": nodes})
    assert response.status_code == 201
    return response.json()


# --- Acceptance 1 & the HTTP-level wiring ---------------------------------


def test_upload_creates_document_and_run_with_node_states(client: TestClient):
    _create_workflow(
        client,
        "wf-upload",
        [
            {"id": "a", "type": "extract", "depends_on": []},
            {"id": "b", "type": "classify", "depends_on": ["a"]},
        ],
    )

    response = client.post(
        "/documents",
        params={"workflow_id": "wf-upload"},
        files={"file": ("sample.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert response.status_code == 201
    run_id = response.json()["run_id"]
    assert run_id

    run = client.get(f"/runs/{run_id}").json()
    assert run["status"] == "running"
    assert run["node_states"]["a"]["status"] == "ready"
    assert run["node_states"]["b"]["status"] == "pending"


# --- Acceptance 2: NODE_RUN published exactly once per entry node ---------


async def test_node_run_published_once_per_entry_node(connected_db):
    bus = RecordingEventBus()
    envelope = _envelope("doc-two-entry")
    workflow = _workflow(two_entry_nodes=True)

    run, created = await RunService(bus).start_run(envelope, workflow)

    assert created is True
    node_run_events = [e for topic, e in bus.published if topic == TOPIC_NODE_RUN]
    assert len(node_run_events) == 2
    assert {e["node_id"] for e in node_run_events} == {"a", "b"}
    run_started_events = [e for topic, e in bus.published if topic == TOPIC_RUN_STARTED]
    assert len(run_started_events) == 1
    assert all(e["run_id"] == run.id for e in node_run_events + run_started_events)


# --- Acceptance 3: calling start_run twice is idempotent -------------------


async def test_start_run_twice_creates_one_run_and_publishes_only_once(connected_db):
    bus = RecordingEventBus()
    envelope = _envelope("doc-idempotent")
    workflow = _workflow()

    first_run, first_created = await RunService(bus).start_run(envelope, workflow)
    assert first_created is True
    published_after_first = len(bus.published)
    assert published_after_first > 0

    second_run, second_created = await RunService(bus).start_run(envelope, workflow)
    assert second_created is False
    assert second_run.id == first_run.id
    assert len(bus.published) == published_after_first


# --- Acceptance 4: duplicate upload -> one document, one run --------------


def test_duplicate_upload_creates_one_document_and_one_run(client: TestClient):
    _create_workflow(
        client, "wf-dup", [{"id": "a", "type": "extract", "depends_on": []}]
    )

    def _upload():
        return client.post(
            "/documents",
            params={"workflow_id": "wf-dup"},
            files={"file": ("dup.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
        )

    first = _upload()
    assert first.status_code == 201
    document_id = first.json()["document_id"]

    second = _upload()
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["run_id"] is None

    runs = client.get(f"/documents/{document_id}/runs").json()
    assert len(runs) == 1


# --- Acceptance 5: unknown/unresolved workflow -> clear error, not 500 ----


def test_upload_with_unknown_workflow_id_is_not_a_500(client: TestClient):
    response = client.post(
        "/documents",
        params={"workflow_id": "does-not-exist"},
        files={"file": ("sample.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert response.status_code == 404


def test_upload_with_no_resolvable_workflow_is_422(client: TestClient):
    response = client.post(
        "/documents",
        files={"file": ("no-workflow.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert response.status_code == 422


def test_manual_run_with_unknown_workflow_id_is_404(client: TestClient):
    client.post(
        "/workflows",
        json={"id": "wf-manual", "nodes": [{"id": "a", "type": "extract"}]},
    )
    upload = client.post(
        "/documents",
        params={"workflow_id": "wf-manual"},
        files={"file": ("manual.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
    )
    assert upload.status_code == 201
    document_id = upload.json()["document_id"]

    response = client.post(
        "/runs", json={"document_id": document_id, "workflow_id": "still-missing"}
    )
    assert response.status_code == 404
