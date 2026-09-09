"""Locate the optimizer package across deployment layouts."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def resolve_algorithm_root() -> Path:


    env_root = os.getenv("ALGORITHM_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if _is_algorithm_root(candidate):
            return candidate

    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir.parents[3] / "optimizer",
        module_dir.parents[4] / "apps" / "optimizer",
        module_dir.parents[2] / "optimizer",
    ]

    for candidate in candidates:
        if _is_algorithm_root(candidate):
            return candidate

    raise RuntimeError(
        "Optimizer package not found. Set ALGORITHM_ROOT to apps/optimizer."
    )


def ensure_algorithm_path() -> Path:


    root = resolve_algorithm_root()
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root


def _is_algorithm_root(path: Path) -> bool:
    """Check whether a directory contains the optimizer modules."""
    return (path / "ingestion.py").is_file() and (path / "pipeline.py").is_file()


__all__ = ["ensure_algorithm_path", "resolve_algorithm_root"]
