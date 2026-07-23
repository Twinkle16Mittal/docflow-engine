"""Domain-level exceptions. Presentation-layer mapping to HTTP status codes lives
in app/api/error_handlers.py — kept separate so business logic never imports FastAPI.
"""


class NotFoundError(Exception):
    pass


class DAGValidationError(Exception):
    pass


class PayloadTooLargeError(Exception):
    pass


class UnsupportedContentTypeError(Exception):
    pass
