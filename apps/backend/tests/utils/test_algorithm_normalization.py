"""Algorithm-normalization tests."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest

from src.utils.algorithm import normalize_algorithm


def test_normalize_simplex():
    assert normalize_algorithm("simplex") == "simplex"
    assert normalize_algorithm("Simplex") == "simplex"


def test_normalize_branch_bound_aliases():
    assert normalize_algorithm("branch_bound") == "branch_bound"
    assert normalize_algorithm("Branch and Bound") == "branch_bound"


def test_normalize_simplex_ortools_aliases():
    assert normalize_algorithm("simplex_ortools") == "simplex_ortools"
    assert normalize_algorithm("Simplex OR-Tools") == "simplex_ortools"


def test_normalize_rejects_unknown():
    with pytest.raises(ValueError):
        normalize_algorithm("genetic")
