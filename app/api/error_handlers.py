import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.errors import (
    DAGValidationError,
    NotFoundError,
    PayloadTooLargeError,
    UnresolvedWorkflowError,
    UnsupportedContentTypeError,
)

logger = logging.getLogger("app.errors")


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def handle_not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return _error_response(404, "not_found", str(exc))

    @app.exception_handler(DAGValidationError)
    async def handle_dag_validation(request: Request, exc: DAGValidationError) -> JSONResponse:
        return _error_response(422, "invalid_workflow_definition", str(exc))

    @app.exception_handler(PayloadTooLargeError)
    async def handle_payload_too_large(
        request: Request, exc: PayloadTooLargeError
    ) -> JSONResponse:
        return _error_response(413, "payload_too_large", str(exc))

    @app.exception_handler(UnsupportedContentTypeError)
    async def handle_unsupported_content_type(
        request: Request, exc: UnsupportedContentTypeError
    ) -> JSONResponse:
        return _error_response(415, "unsupported_content_type", str(exc))

    @app.exception_handler(UnresolvedWorkflowError)
    async def handle_unresolved_workflow(
        request: Request, exc: UnresolvedWorkflowError
    ) -> JSONResponse:
        return _error_response(422, "unresolved_workflow", str(exc))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_error")
        return _error_response(500, "internal_error", "an unexpected error occurred")
