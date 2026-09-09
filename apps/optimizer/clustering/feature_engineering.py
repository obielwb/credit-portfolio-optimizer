

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

import numpy as np

from .contracts import ClusteringInput, PreprocessedClientInput
from .utils.normalization import normalize_feature_set


DEFAULT_FEATURE_NAMES: tuple[str, ...] = (
    "product_pd",
    "contract_propensity_score",
    "payment_capacity",
)


@dataclass(frozen=True)
class EngineeredClient:


    token: str
    source: PreprocessedClientInput
    feature_names: tuple[str, ...]
    raw_values: tuple[float, ...]
    normalized_values: tuple[float, ...]
    priority_score: float


@dataclass(frozen=True)
class FeatureEngineeringResult:
    """Feature-engineering stage result."""

    feature_names: tuple[str, ...]
    clients: tuple[EngineeredClient, ...]
    feature_matrix: tuple[tuple[float, ...], ...]
    feature_matrix_ndarray: np.ndarray


def engineer_features(payload: ClusteringInput) -> FeatureEngineeringResult:


    feature_names = _resolve_feature_names(payload)
    raw_matrix = [_extract_raw_values(client, feature_names) for client in payload.clients]
    normalized_columns = _normalize_columns(raw_matrix)

    engineered_clients: list[EngineeredClient] = []
    for index, client in enumerate(payload.clients):
        normalized_values = tuple(column[index] for column in normalized_columns)
        raw_values = tuple(raw_matrix[index])
        priority_score = fmean(normalized_values) if normalized_values else 0.0
        engineered_clients.append(
            EngineeredClient(
                token=client.token,
                source=client,
                feature_names=feature_names,
                raw_values=raw_values,
                normalized_values=normalized_values,
                priority_score=priority_score,
            )
        )

    feature_matrix = tuple(
        tuple(column[index] for column in normalized_columns)
        for index in range(len(payload.clients))
    )
    feature_matrix_ndarray = np.asarray(feature_matrix, dtype=np.float32)

    return FeatureEngineeringResult(
        feature_names=feature_names,
        clients=tuple(engineered_clients),
        feature_matrix=feature_matrix,
        feature_matrix_ndarray=feature_matrix_ndarray,
    )


def _resolve_feature_names(payload: ClusteringInput) -> tuple[str, ...]:


    if payload.config.feature_set:
        return payload.config.feature_set
    return DEFAULT_FEATURE_NAMES


def _extract_raw_values(
    client: PreprocessedClientInput, feature_names: tuple[str, ...]
) -> list[float]:













    values: list[float] = []
    for feature_name in feature_names:
        if feature_name == "product_pd":
            values.append(client.product_pd)
        elif feature_name == "contract_propensity_score":
            values.append(client.contract_propensity_score)
        elif feature_name == "payment_capacity":
            values.append(client.payment_capacity)
        else:
            if feature_name not in client.extra_features:
                raise ValueError(f"Missing feature for client {client.token}: {feature_name}")
            values.append(client.extra_features[feature_name])
    return values


def _normalize_columns(raw_matrix: list[list[float]]) -> list[list[float]]:









    if not raw_matrix:
        return []

    columns: list[list[float]] = []
    for column_values in zip(*raw_matrix):
        columns.append(normalize_feature_set(list(column_values)))
    return columns


__all__ = ["EngineeredClient", "FeatureEngineeringResult", "engineer_features"]
