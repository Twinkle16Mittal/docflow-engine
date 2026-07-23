import asyncio
from datetime import UTC, datetime
from typing import IO
from uuid import uuid4

import boto3
from botocore.client import Config

from app.config import Settings


class ObjectStorage:
    """Thin async wrapper over boto3 S3, configured to work against MinIO locally
    and unchanged against real S3 in other environments."""

    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name="us-east-1",
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def generate_key(self, source: str, ext: str) -> str:
        now = datetime.now(UTC)
        return f"{source}/{now:%Y}/{now:%m}/{uuid4().hex}{ext}"

    async def put_object(self, key: str, fileobj: IO[bytes], content_type: str) -> str:
        """Stream fileobj to `key`; boto3 reads it in chunks, so the caller never
        needs to buffer the whole upload in memory."""
        await asyncio.to_thread(
            self._client.upload_fileobj,
            fileobj,
            self._bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        return key

    async def get_object(self, key: str) -> IO[bytes]:
        response = await asyncio.to_thread(
            self._client.get_object, Bucket=self._bucket, Key=key
        )
        return response["Body"]
