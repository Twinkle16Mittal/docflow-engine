import hashlib
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import IO
from uuid import uuid4

from fastapi import UploadFile

from app.errors import PayloadTooLargeError
from app.ingestion.base import SourceAdapter
from app.models import DocumentEnvelope, DocumentSource
from app.storage import ObjectStorage


class _LimitedHashingReader:
    """Wraps a sync file object: forwards reads through untouched while hashing
    the content and enforcing a byte-count limit, so the upload can be streamed
    to storage without ever being buffered in memory."""

    def __init__(self, fileobj: IO[bytes], max_bytes: int) -> None:
        self._fileobj = fileobj
        self._hash = hashlib.sha256()
        self._max_bytes = max_bytes
        self._total = 0

    def read(self, size: int = -1) -> bytes:
        chunk = self._fileobj.read(size)
        if chunk:
            self._total += len(chunk)
            if self._total > self._max_bytes:
                raise PayloadTooLargeError(
                    f"upload exceeds {self._max_bytes} byte limit"
                )
            self._hash.update(chunk)
        return chunk

    def hexdigest(self) -> str:
        return self._hash.hexdigest()


def _compute_dedup_key(source: DocumentSource, identifier: str, content_hash: str) -> str:
    return hashlib.sha256(f"{source}:{identifier}:{content_hash}".encode()).hexdigest()


class UploadAdapter(SourceAdapter):
    def __init__(self, storage: ObjectStorage, max_bytes: int) -> None:
        self._storage = storage
        self._max_bytes = max_bytes

    async def to_envelope(self, raw: UploadFile) -> DocumentEnvelope:
        filename = raw.filename or "upload"
        ext = PurePosixPath(filename).suffix
        content_type = raw.content_type or "application/octet-stream"
        storage_key = self._storage.generate_key(DocumentSource.UPLOAD, ext)

        reader = _LimitedHashingReader(raw.file, self._max_bytes)
        await self._storage.put_object(storage_key, reader, content_type)

        dedup_key = _compute_dedup_key(DocumentSource.UPLOAD, filename, reader.hexdigest())

        return DocumentEnvelope(
            id=str(uuid4()),
            source=DocumentSource.UPLOAD,
            storage_key=storage_key,
            content_type=content_type,
            received_at=datetime.now(UTC),
            dedup_key=dedup_key,
            metadata={"filename": filename},
        )
