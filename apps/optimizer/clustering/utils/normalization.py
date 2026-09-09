

from __future__ import annotations

import numpy as np


def normalize_columns_minmax(matrix: np.ndarray) -> np.ndarray:


    if matrix.size == 0:
        return np.asarray(matrix, dtype=np.float32)

    data = np.asarray(matrix, dtype=np.float64)
    mins = data.min(axis=0)
    maxs = data.max(axis=0)
    span = maxs - mins
    constant = span == 0
    span = np.where(constant, 1.0, span)
    normalized = (data - mins) / span
    normalized[:, constant] = 1.0
    return np.round(normalized, 10)


def normalize_feature_set(values: list[float]) -> list[float]:


    if not values:
        return []

    minimum = min(values)
    maximum = max(values)
    if minimum == maximum:
        return [1.0 for _ in values]

    return [round((value - minimum) / (maximum - minimum), 10) for value in values]
