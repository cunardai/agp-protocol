"""
AGP SDK — Exception hierarchy

Every AGP error response carries:
  { "error": { "code": "AGP_*", "message": "..." } }

This module maps HTTP status codes + AGP error codes to typed exceptions
so callers can catch specific failure modes without parsing raw JSON.
"""
from __future__ import annotations


class AGPError(Exception):
    """Base class for all AGP SDK errors."""

    def __init__(self, message: str, code: str = "AGP_ERROR",
                 http_status: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status
        self.retryable = retryable

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class AGPNotFoundError(AGPError):
    """404 — The requested resource does not exist."""
    def __init__(self, message: str):
        super().__init__(message, code="AGP_NOT_FOUND", http_status=404)


class AGPBadRequestError(AGPError):
    """400 — Request is malformed or missing required fields."""
    def __init__(self, message: str, code: str = "AGP_INVALID_REQUEST"):
        super().__init__(message, code=code, http_status=400)


class AGPConflictError(AGPError):
    """409 — Request conflicts with current resource state."""
    def __init__(self, message: str, code: str = "AGP_CONFLICT"):
        super().__init__(message, code=code, http_status=409)


class AGPUnprocessableError(AGPError):
    """422 — Semantically invalid (e.g. illegal state transition)."""
    def __init__(self, message: str, code: str = "AGP_INVALID_REQUEST"):
        super().__init__(message, code=code, http_status=422)


class AGPPolicyDeniedError(AGPUnprocessableError):
    """422 AGP_POLICY_DENIED — Execution blocked by policy verdict."""
    def __init__(self, message: str):
        super().__init__(message, code="AGP_POLICY_DENIED")


class AGPTokenRevokedError(AGPUnprocessableError):
    """422 AGP_TOKEN_REVOKED — Capability token has been revoked."""
    def __init__(self, message: str):
        super().__init__(message, code="AGP_TOKEN_REVOKED")


class AGPTokenExpiredError(AGPUnprocessableError):
    """422 AGP_TOKEN_EXPIRED — Capability token has expired."""
    def __init__(self, message: str):
        super().__init__(message, code="AGP_TOKEN_EXPIRED")


class AGPApprovalRequiredError(AGPUnprocessableError):
    """422 AGP_APPROVAL_REQUIRED — Human approval artifact missing or pending."""
    def __init__(self, message: str):
        super().__init__(message, code="AGP_APPROVAL_REQUIRED")


class AGPServerError(AGPError):
    """5xx — Server-side error, may be retryable."""
    def __init__(self, message: str, http_status: int = 500):
        super().__init__(message, code="AGP_SERVER_ERROR",
                         http_status=http_status, retryable=True)


class AGPConnectionError(AGPError):
    """Network-level failure reaching the AGP server."""
    def __init__(self, message: str):
        super().__init__(message, code="AGP_CONNECTION_ERROR", retryable=True)


# ── Error code → exception mapping ────────────────────────────────────────────

_CODE_MAP: dict[str, type[AGPError]] = {
    "AGP_NOT_FOUND":        AGPNotFoundError,
    "AGP_POLICY_DENIED":    AGPPolicyDeniedError,
    "AGP_TOKEN_REVOKED":    AGPTokenRevokedError,
    "AGP_TOKEN_EXPIRED":    AGPTokenExpiredError,
    "AGP_APPROVAL_REQUIRED": AGPApprovalRequiredError,
    "AGP_SCOPE_VIOLATION":  AGPConflictError,
}

_STATUS_MAP: dict[int, type[AGPError]] = {
    400: AGPBadRequestError,
    404: AGPNotFoundError,
    409: AGPConflictError,
    422: AGPUnprocessableError,
}


def raise_for_response(status: int, body: dict) -> None:
    """Parse an AGP error body and raise the appropriate exception."""
    error = body.get("error", {})
    code = error.get("code", "AGP_ERROR")
    message = error.get("message", f"HTTP {status}")

    # Specific code takes priority
    if code in _CODE_MAP:
        exc_cls = _CODE_MAP[code]
        if exc_cls is AGPNotFoundError:
            raise exc_cls(message)
        raise exc_cls(message)  # type: ignore[call-arg]

    # Fall back to status code
    exc_cls_by_status = _STATUS_MAP.get(status)
    if exc_cls_by_status:
        raise exc_cls_by_status(message)  # type: ignore[call-arg]

    if status >= 500:
        raise AGPServerError(message, http_status=status)

    raise AGPError(message, code=code, http_status=status)
