

from __future__ import annotations

import os


def _truthy(value: str | None, *, default: bool = False) -> bool:
    """Interpret an environment string as a Boolean value."""
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_cors_allowed_origins() -> list[str]:


    raw = os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def get_cors_allow_credentials() -> bool:
    """Indica se credenciais CORS sao permitidas."""
    return _truthy(os.getenv("CORS_ALLOW_CREDENTIALS"), default=True)


__all__ = ["get_cors_allowed_origins", "get_cors_allow_credentials"]
