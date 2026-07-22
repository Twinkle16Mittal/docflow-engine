from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.enums import DocumentSource


class DocumentEnvelope(BaseModel):
    id: str
    source: DocumentSource
    storage_key: str
    content_type: str
    received_at: datetime
    dedup_key: str
    metadata: dict[str, Any] = {}
