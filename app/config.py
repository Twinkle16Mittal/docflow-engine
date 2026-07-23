from enum import StrEnum

from pydantic_settings import BaseSettings, SettingsConfigDict


class RunMode(StrEnum):
    INLINE = "inline"
    DISTRIBUTED = "distributed"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    run_mode: RunMode = RunMode.INLINE

    mongodb_uri: str = "mongodb://localhost:27017/?replicaSet=rs0"
    redis_url: str = "redis://localhost:6379/0"
    kafka_brokers: str = "localhost:19092"

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "docflow-raw"

    max_upload_size_bytes: int = 25 * 1024 * 1024
    allowed_content_types: list[str] = [
        "application/pdf",
        "image/png",
        "image/jpeg",
        "text/plain",
    ]
