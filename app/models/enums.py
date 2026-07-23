from enum import StrEnum


class DocumentSource(StrEnum):
    UPLOAD = "upload"
    EMAIL = "email"
    DRIVE = "drive"
    S3 = "s3"


class DocumentStatus(StrEnum):
    RECEIVED = "received"
    DUPLICATE = "duplicate"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
