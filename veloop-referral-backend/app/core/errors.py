"""Structured error codes + handlers.

Every failure returns:
  {"success": false, "code": "...", "message": "...", ...extra}
so the frontend can branch on `code` (e.g. render the self-referral modal).
"""
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode:
    INVALID_REFERRAL_CODE = "INVALID_REFERRAL_CODE"
    REFERRAL_ALREADY_ASSIGNED = "REFERRAL_ALREADY_ASSIGNED"
    SELF_REFERRAL_DETECTED = "SELF_REFERRAL_DETECTED"
    DEVICE_ALREADY_ASSOCIATED = "DEVICE_ALREADY_ASSOCIATED"
    REFERRAL_NOT_ELIGIBLE = "REFERRAL_NOT_ELIGIBLE"
    REWARD_ALREADY_CREDITED = "REWARD_ALREADY_CREDITED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    FRAUD_REVIEW = "FRAUD_REVIEW"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    EMAIL_ALREADY_REGISTERED = "EMAIL_ALREADY_REGISTERED"
    INVALID_DEVICE_TOKEN = "INVALID_DEVICE_TOKEN"
    AD_EVENT_REJECTED = "AD_EVENT_REJECTED"
    DUPLICATE_EVENT = "DUPLICATE_EVENT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppError(Exception):
    """Domain error carrying an HTTP status, a stable code and safe extras."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = status.HTTP_400_BAD_REQUEST,
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http_status = http_status
        self.extra = extra or {}

    def to_response(self) -> JSONResponse:
        body = {"success": False, "code": self.code, "message": self.message}
        body.update(self.extra)
        return JSONResponse(status_code=self.http_status, content=body)


def register_exception_handlers(app) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return exc.to_response()

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "code": ErrorCode.VALIDATION_ERROR,
                "message": "Request validation failed.",
                "details": [
                    {"field": ".".join(str(p) for p in e["loc"][1:]), "issue": e["msg"]}
                    for e in exc.errors()
                ],
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {
            401: ErrorCode.UNAUTHORIZED,
            403: ErrorCode.FORBIDDEN,
            404: ErrorCode.NOT_FOUND,
            409: ErrorCode.CONFLICT,
            429: ErrorCode.RATE_LIMITED,
        }.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "code": code, "message": str(exc.detail)},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):  # pragma: no cover
        # Never leak internals (stack traces, SQL, fraud signals) to the client.
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "code": ErrorCode.INTERNAL_ERROR,
                "message": "Something went wrong. Please try again.",
            },
        )
