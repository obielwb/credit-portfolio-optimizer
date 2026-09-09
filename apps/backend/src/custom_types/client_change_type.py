"""Change types recorded in client history."""

from __future__ import annotations

import enum


class ClientChangeType(str, enum.Enum):
    """Change types recorded in client history."""

    NEW_CLIENT = "new_client"
    LIMIT_UPDATED = "updated_limit"


__all__ = ["ClientChangeType"]
