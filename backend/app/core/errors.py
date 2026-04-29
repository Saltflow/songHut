from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AppError:
    code: str
    message: str
    details: dict | None = None
    http_status: int = 400

    def to_dict(self) -> dict:
        return {
            "ok": False,
            "error": {
                "code": self.code,
                "message": self.message,
            },
        }


def not_found(entity: str, identifier: str) -> AppError:
    code_map = {
        "user": "USER_NOT_FOUND",
        "project": "PROJECT_NOT_FOUND",
        "file": "FILE_NOT_FOUND",
        "task": "TASK_NOT_FOUND",
        "score": "SCORE_NOT_FOUND",
    }
    return AppError(
        code=code_map.get(entity.lower(), "NOT_FOUND"),
        message=f"{entity} not found: {identifier}",
        http_status=404,
    )


def forbidden(msg: str = "Insufficient permissions") -> AppError:
    return AppError(code="AUTH_FORBIDDEN", message=msg, http_status=403)


def unauthorized(msg: str = "Authentication required") -> AppError:
    return AppError(code="AUTH_UNAUTHORIZED", message=msg, http_status=401)


def invalid_credentials(msg: str = "Invalid phone or password") -> AppError:
    return AppError(code="AUTH_INVALID_CREDENTIALS", message=msg, http_status=401)


def token_expired() -> AppError:
    return AppError(code="AUTH_TOKEN_EXPIRED", message="Token expired or invalid", http_status=401)


def token_invalid() -> AppError:
    return AppError(code="AUTH_TOKEN_INVALID", message="Token is invalid", http_status=401)


def phone_exists() -> AppError:
    return AppError(code="AUTH_PHONE_EXISTS", message="Phone number already registered", http_status=409)


def validation_error(message: str, details: dict | None = None) -> AppError:
    return AppError(code="VALIDATION_ERROR", message=message, details=details, http_status=422)


def conflict(message: str) -> AppError:
    return AppError(code="CONFLICT", message=message, http_status=409)


def file_too_large(max_mb: int) -> AppError:
    return AppError(
        code="FILE_TOO_LARGE",
        message=f"File exceeds maximum size of {max_mb}MB",
        http_status=413,
    )


def file_type_unsupported(ext: str) -> AppError:
    return AppError(
        code="FILE_TYPE_UNSUPPORTED",
        message=f"Unsupported file type: {ext}",
        http_status=400,
    )


def internal_error(msg: str = "Internal server error") -> AppError:
    return AppError(code="INTERNAL_ERROR", message=msg, http_status=500)


def task_exists() -> AppError:
    return AppError(
        code="TASK_ALREADY_EXISTS",
        message="A task for this file is already in progress",
        http_status=409,
    )


def rate_limited() -> AppError:
    return AppError(code="RATE_LIMITED", message="Too many requests, please wait", http_status=429)
