import io
import os

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

os.environ.setdefault("RUN_MODE", "inline")
os.environ.setdefault(
    "MONGODB_URI", "mongodb://localhost:27017/docflow_test?replicaSet=rs0"
)

from app.main import app  # noqa: E402

PDF_BYTES = b"%PDF-1.4 fake pdf content for testing\n%%EOF"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_collections():
    # Uses the sync driver, not app.db's AsyncMongoClient, so cleanup never
    # binds to a different event loop than the one TestClient's requests run on.
    sync_client: MongoClient = MongoClient(
        "mongodb://localhost:27017/docflow_test?replicaSet=rs0"
    )
    db = sync_client.get_default_database()
    db["documents"].delete_many({})
    db["workflows"].delete_many({})
    yield
    db["documents"].delete_many({})
    db["workflows"].delete_many({})
    sync_client.close()


def _upload(client: TestClient, filename: str = "sample.pdf"):
    return client.post(
        "/documents",
        files={"file": (filename, io.BytesIO(PDF_BYTES), "application/pdf")},
    )


def test_upload_happy_path(client: TestClient):
    response = _upload(client)
    assert response.status_code == 201
    body = response.json()
    assert body["duplicate"] is False
    assert body["status"] == "received"

    get_response = client.get(f"/documents/{body['document_id']}")
    assert get_response.status_code == 200
    doc = get_response.json()
    assert doc["source"] == "upload"
    assert doc["content_type"] == "application/pdf"
    assert doc["storage_key"]


def test_duplicate_upload_reports_duplicate_and_single_record(client: TestClient):
    first = _upload(client)
    assert first.status_code == 201

    second = _upload(client)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True

    listing = client.get("/documents").json()
    assert listing["total"] == 1


def test_unsupported_content_type_rejected(client: TestClient):
    response = client.post(
        "/documents",
        files={"file": ("evil.exe", io.BytesIO(b"binary"), "application/x-msdownload")},
    )
    assert response.status_code == 415


def test_get_unknown_document_404(client: TestClient):
    response = client.get("/documents/does-not-exist")
    assert response.status_code == 404


def test_workflow_cycle_rejected(client: TestClient):
    payload = {
        "id": "wf-cycle",
        "nodes": [
            {"id": "a", "type": "extract", "depends_on": ["b"]},
            {"id": "b", "type": "extract", "depends_on": ["a"]},
        ],
    }
    response = client.post("/workflows", json=payload)
    assert response.status_code == 422


def test_workflow_missing_dependency_rejected(client: TestClient):
    payload = {
        "id": "wf-missing-dep",
        "nodes": [
            {"id": "a", "type": "extract", "depends_on": ["ghost"]},
        ],
    }
    response = client.post("/workflows", json=payload)
    assert response.status_code == 422


def test_workflow_valid_dag_created_and_fetchable(client: TestClient):
    payload = {
        "id": "wf-valid",
        "nodes": [
            {"id": "a", "type": "extract", "depends_on": []},
            {"id": "b", "type": "classify", "depends_on": ["a"]},
        ],
    }
    create_response = client.post("/workflows", json=payload)
    assert create_response.status_code == 201
    assert create_response.json()["version"] == 1

    get_response = client.get("/workflows/wf-valid")
    assert get_response.status_code == 200
    assert len(get_response.json()["nodes"]) == 2


def test_get_unknown_run_404(client: TestClient):
    response = client.get("/runs/does-not-exist")
    assert response.status_code == 404
