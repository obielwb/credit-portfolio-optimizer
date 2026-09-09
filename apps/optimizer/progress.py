

from __future__ import annotations

from collections.abc import Callable

ProgressCallback = Callable[[str], None]

_CALLBACK: ProgressCallback | None = None


def set_progress_callback(callback: ProgressCallback | None) -> None:







    global _CALLBACK
    _CALLBACK = callback


def notify_progress(state: str) -> None:






    if _CALLBACK is not None:
        _CALLBACK(state)


__all__ = ["ProgressCallback", "notify_progress", "set_progress_callback"]
