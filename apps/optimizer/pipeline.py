





from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from algorithms import run_algorithm
from algorithms.simplex import optimize_clusters_simplex
from algorithms.simplex_ortools import optimize_clusters_simplex_ortools
from evaluation import client_fails_business_filter, build_results
from clustering import (
    ClusteringConfig,
    ClusteringInput,
    PreprocessedClientInput,
    clusterize,
    clusters_for_persistence,
    summarize_for_simplex,
)
from clustering.models import ClusteringResult
from models import Client, ModelParameters, PortfolioResult
from ingestion import load_data, preprocess


def run_pipeline(
    path_file: str | Path | None,
    algorithm: str,
    parameters: ModelParameters,
    *,
    clients: list[Client] | None = None,
    clustering_input: ClusteringInput | None = None,
) -> PortfolioResult:


















    if clients is None and clustering_input is not None:
        clients = _clients_from_clustering_input(clustering_input)

    if clients is None:
        if path_file is None:
            raise ValueError(
                "Provide either an input file or a list of preprocessed clients."
            )
        rows = load_data(path_file)
        clients = preprocess(rows)

    if _is_clustering_enabled(parameters):
        clustering_payload = _build_clustering_payload(clients, parameters)
        clustering_result = clusterize(clustering_payload)

        if algorithm in ("simplex", "simplex_ortools"):
            summaries = _enriquecer_summaries_filter(
                summarize_for_simplex(clustering_result),
                clients,
                clustering_result,
                parameters,
            )
            if algorithm == "simplex":
                limits_clusters = optimize_clusters_simplex(summaries, parameters)
            else:
                limits_clusters = optimize_clusters_simplex_ortools(
                    summaries, parameters
                )
            limit_por_cluster_id = {
                summary.cluster_id: limit
                for summary, limit in zip(summaries, limits_clusters)
            }
            if clustering_result.client_cluster_ids:
                limits_ordenados = [
                    _limit_final_client(
                        limit_por_cluster_id[cluster_id], client, parameters
                    )
                    for cluster_id, client in zip(
                        clustering_result.client_cluster_ids, clients
                    )
                ]
            else:
                limits_por_token: dict[str, float] = {}
                for summary, limit in zip(summaries, limits_clusters):
                    for token in summary.client_tokens:
                        limits_por_token[token] = limit
                limits_ordenados = [
                    _limit_final_client(
                        limits_por_token[client.token], client, parameters
                    )
                    for client in clients
                ]
            return _build_com_clusters(
                clients,
                limits_ordenados,
                parameters,
                algorithm,
                clustering_result,
            )

        limits_por_token_list: dict[str, list[float]] = {}
        clients_por_cluster: dict[int, list[Client]] = {}
        if clustering_result.client_cluster_ids:
            for client, cluster_id in zip(
                clients, clustering_result.client_cluster_ids
            ):
                clients_por_cluster.setdefault(cluster_id, []).append(client)
        else:
            clients_por_token = {client.token: client for client in clients}
            for cluster in clustering_result.clusters:
                for member in cluster.members:
                    reference = clients_por_token.get(member.token)
                    clients_por_cluster.setdefault(cluster.cluster_id, []).append(
                        Client(
                            token=member.token,
                            product_pd=member.product_pd,
                            payment_capacity=member.payment_capacity,
                            contract_propensity_score=member.contract_propensity_score,
                            filter_flag=(
                                reference.filter_flag if reference is not None else False
                            ),
                        )
                    )

        for cluster in clustering_result.clusters:
            clients_cluster = clients_por_cluster.get(cluster.cluster_id, [])
            if not clients_cluster:
                raise ValueError(
                    f"Cluster cluster_id={cluster.cluster_id} has no clients in the clustering output."
                )
            limits_cluster = run_algorithm(algorithm, clients_cluster, parameters)
            for client_cluster, limit in zip(clients_cluster, limits_cluster):
                limits_por_token_list.setdefault(client_cluster.token, []).append(limit)

        limits_ordenados = []
        for client in clients:
            limits_client = limits_por_token_list.get(client.token)
            if not limits_client:
                raise ValueError(
                    f"Client token={client.token} was not found in the clustering output."
                )
            limits_ordenados.append(limits_client.pop(0))

        return _build_com_clusters(
            clients,
            limits_ordenados,
            parameters,
            algorithm,
            clustering_result,
        )

    limits = run_algorithm(algorithm, clients, parameters)
    return build_results(clients, limits, parameters, algorithm)


def _build_com_clusters(
    clients: list[Client],
    limits: list[float],
    parameters: ModelParameters,
    algorithm: str,
    clustering_result: ClusteringResult,
) -> PortfolioResult:


    return build_results(
        clients,
        limits,
        parameters,
        algorithm,
        clusters=clusters_for_persistence(clustering_result),
    )


def _ensure_clustered_input(clustering_input: ClusteringInput) -> ClusteringInput:


    if not clustering_input.clients:
        raise ValueError("Clustered input must contain at least one client.")
    return clustering_input


def _limit_final_client(
    limit: float,
    client: Client,
    parameters: ModelParameters,
) -> float:











    if client_fails_business_filter(client, parameters):
        return 0.0
    return limit


def _enriquecer_summaries_filter(
    summaries,
    clients: list[Client],
    clustering_result: ClusteringResult,
    parameters: ModelParameters,
):













    if not parameters.filter:
        return summaries

    por_cluster: dict[int, list[Client]] = {}
    if clustering_result.client_cluster_ids:
        for client, cluster_id in zip(clients, clustering_result.client_cluster_ids):
            por_cluster.setdefault(cluster_id, []).append(client)

    enriched = []
    for summary in summaries:
        membros = por_cluster.get(summary.cluster_id, [])
        eligible = any(not client.filter_flag for client in membros) if membros else True
        tokens = tuple(client.token for client in membros) if membros else summary.client_tokens
        enriched.append(
            replace(
                summary,
                filter_flag_eligible=eligible,
                client_tokens=tokens,
            )
        )
    return enriched


def _clients_from_clustering_input(clustering_input: ClusteringInput) -> list[Client]:


    return [
        Client(
            token=client.token,
            product_pd=client.product_pd,
            payment_capacity=client.payment_capacity,
            contract_propensity_score=client.contract_propensity_score,
            filter_flag=client.filter_flag,
        )
        for client in clustering_input.clients
    ]


def _is_clustering_enabled(parameters: ModelParameters) -> bool:


    return bool(getattr(parameters, "enabled", False))


def _build_clustering_payload(
    clients: list[Client], parameters: ModelParameters
) -> ClusteringInput:


    config = ClusteringConfig(
        enabled=bool(parameters.enabled),
        n_clusters=parameters.n_clusters,
        max_clients_per_cluster=max(1, int(parameters.max_clients_per_cluster)),
        min_clusters=max(1, int(parameters.min_clusters)),
    )
    clients = tuple(
        PreprocessedClientInput(
            token=client.token,
            product_pd=client.product_pd,
            payment_capacity=client.payment_capacity,
            contract_propensity_score=client.contract_propensity_score,
            filter_flag=client.filter_flag,
        )
        for client in clients
    )
    return ClusteringInput(clients=clients, config=config)
