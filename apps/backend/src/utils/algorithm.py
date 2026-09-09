

from __future__ import annotations

AVAILABLE_ALGORITHMS = frozenset({"simplex", "simplex_ortools", "branch_bound"})


def normalize_algorithm(value: str) -> str:


    key = value.strip().lower().replace("-", " ").replace("_", " ")
    if key in {"simplex"}:
        return "simplex"
    if key in {"simplex ortools", "ortools simplex", "simplex or tools"}:
        return "simplex_ortools"
    if key in {"branch bound", "branch and bound"}:
        return "branch_bound"
    raise ValueError(
        f"Algorithm '{value}' is invalid. Options: simplex, simplex_ortools, branch_bound "
        "(or labels Simplex / Simplex OR-Tools / Branch and Bound)."
    )


__all__ = ["AVAILABLE_ALGORITHMS", "normalize_algorithm"]
