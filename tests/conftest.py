import os

os.environ.setdefault("RUN_MODE", "inline")
os.environ.setdefault(
    "MONGODB_URI", "mongodb://localhost:27017/docflow_test?replicaSet=rs0"
)

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.main import app

TEST_MONGODB_URI = "mongodb://localhost:27017/docflow_test?replicaSet=rs0"


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_collections():
    # Uses the sync driver, not app.db's AsyncMongoClient, so cleanup never
    # binds to a different event loop than the one TestClient's requests run on.
    sync_client: MongoClient = MongoClient(TEST_MONGODB_URI)
    db = sync_client.get_default_database()

    def _clean() -> None:
        db["documents"].delete_many({})
        db["workflows"].delete_many({})
        db["workflow_runs"].delete_many({})

    _clean()
    yield
    _clean()
    sync_client.close()
