from abc import ABC, abstractmethod
from typing import Any

from app.models import DocumentEnvelope


class SourceAdapter(ABC):
    """Converts a channel-specific raw input into a normalized DocumentEnvelope.
    Every ingestion channel (upload, email, drive, s3) implements this so the
    rest of the platform only ever deals with one shape.
    """

    @abstractmethod
    async def to_envelope(self, raw: Any) -> DocumentEnvelope: ...
