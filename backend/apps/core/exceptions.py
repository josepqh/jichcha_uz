"""Uniform error envelope: {"error": {"code", "message", "details"}}.

`code` is stable and machine-readable so the frontend can translate it.
"""

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class AppError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "bad_request"
    default_detail = "Bad request."

    def __init__(self, code: str, message: str, status_code: int | None = None, details: dict | None = None):
        super().__init__(detail=message, code=code)
        self.code = code
        self.details = details or {}
        if status_code is not None:
            self.status_code = status_code


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None  # Unhandled -> Django 500 page without internals (DEBUG off).

    if isinstance(exc, AppError):
        code, message, details = exc.code, str(exc.detail), exc.details
    else:
        data = response.data
        code = getattr(exc, "default_code", "error")
        if isinstance(data, dict) and set(data) == {"detail"}:
            message, details = str(data["detail"]), {}
        else:
            message, details = "Validation failed.", data
            code = "validation_error"
    response.data = {"error": {"code": code, "message": message, "details": details}}
    return response
