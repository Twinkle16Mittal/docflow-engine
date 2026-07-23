from pymongo import ASCENDING, AsyncMongoClient
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase

from app.config import Settings

_client: AsyncMongoClient | None = None
_db: AsyncDatabase | None = None


def connect(settings: Settings) -> AsyncMongoClient:
    global _client, _db
    _client = AsyncMongoClient(settings.mongodb_uri)
    _db = _client.get_default_database(default="docflow")
    return _client


async def close() -> None:
    global _client, _db
    if _client is not None:
        await _client.close()
    _client = None
    _db = None


def _database() -> AsyncDatabase:
    if _db is None:
        raise RuntimeError("db.connect() must be called before accessing collections")
    return _db


def get_documents() -> AsyncCollection:
    return _database()["documents"]


def get_workflows() -> AsyncCollection:
    return _database()["workflows"]


def get_workflow_runs() -> AsyncCollection:
    return _database()["workflow_runs"]


async def ensure_indexes() -> None:
    await get_documents().create_index("dedup_key", unique=True)
    await get_workflow_runs().create_index(
        [("status", ASCENDING), ("updated_at", ASCENDING)]
    )
    await get_workflow_runs().create_index(
        [("workflow_id", ASCENDING), ("status", ASCENDING)]
    )
    await get_workflow_runs().create_index(
        [("document_id", ASCENDING), ("workflow_id", ASCENDING)], unique=True
    )
    await get_workflows().create_index(
        [("id", ASCENDING), ("version", ASCENDING)], unique=True
    )
