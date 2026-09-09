





from __future__ import annotations

import argparse
from pathlib import Path

from algorithms import ALGORITHMS
from ingestion import save_result_csv
from models import ModelParameters, PortfolioResult
from pipeline import run_pipeline


def print_result(result: PortfolioResult) -> None:





    print("\n=== Portfolio summary ===")
    print(f"Algorithm utilizado: {result.algorithm}")
    print(f"Total clients: {len(result.clients)}")
    print(f"Limit total sugerido: R$ {result.total_limit:,.2f}")
    print(f"Income expected total: R$ {result.total_income:,.2f}")
    print(f"Loss expected total: R$ {result.total_loss:,.2f}")
    print(f"Return expected total: R$ {result.total_return:,.2f}")
    print(f"Estimated financial default rate: {result.financial_default_rate:.4%}")
    print(f"Baseline financeiro permitido: {result.baseline_default_rate:.4%}")

    print("\n=== Limits by client ===")
    for client in result.clients:
        print(
            f"{client.client.token}: limit=R$ {client.suggested_limit:,.2f} | "
            f"PD={client.client.product_pd:.2%} | "
            f"propensity={client.client.contract_propensity_score:.2f} | "
            f"return=R$ {client.expected_return:,.2f}"
        )


def create_parser() -> argparse.ArgumentParser:





    parser = argparse.ArgumentParser(
        description="Modular pipeline for pre-approved credit-limit recommendations."
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV or Parquet file containing client data.")
    parser.add_argument("--output", type=Path, help="Optional CSV output file for results.")
    parser.add_argument(
        "--algorithm",
        choices=sorted(ALGORITHMS),
        default="simplex",
        help="Algorithm used to choose limits (default: simplex).",
    )
    parser.add_argument("--interchange", type=float, default=0.0175, help="Interchange rate (default: 0.0175).")
    parser.add_argument("--lgd", type=float, default=0.80, help="Loss Given Default (default: 0.80).")
    parser.add_argument("--min-limit", type=float, default=200.0, help="Minimum operational limit (default: 200.0).")
    parser.add_argument("--max-rejected-limit", type=float, default=200.0, help="Maximum limit for rejected records (default: 200.0).")
    parser.add_argument("--max-limit", type=float, default=25000.0, help="Global maximum limit (default: 25000.0).")
    parser.add_argument("--baseline-default-rate", type=float, default=0.0553, help="Financial default-rate baseline (default: 0.0553).")
    parser.add_argument("--limit-step", type=float, default=50.0, help="Limit rounding step (default: 50.0).")
    parser.add_argument("--utilization-rate", type=float, default=0.70, help="Expected limit utilization rate (default: 0.70).")
    parser.add_argument(
        "--filter",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply the filter_flag business constraint (enabled by default).",
    )

    # parser.add_argument("--min-clusters", type=int, default=100)
    # parser.add_argument("--clients-max-cluster", type=int, default=1000)
    # parser.add_argument("--n-clusters", type=int, default=None)
    return parser


def create_parameters(args: argparse.Namespace) -> ModelParameters:








    return ModelParameters(
        interchange=args.interchange,
        lgd=args.lgd,
        min_limit=args.min_limit,
        max_rejected_limit=args.max_rejected_limit,
        max_limit=args.max_limit,
        baseline_default_rate=args.baseline_default_rate,
        limit_step=args.limit_step,
        utilization_rate=args.utilization_rate,
        filter=args.filter,
        # enabled=not args.sem_clustering,
        # min_clusters=args.min_clusters,
        # max_clients_per_cluster=args.max_clients_per_cluster,
        # n_clusters=args.n_clusters,
    )


def main() -> None:

    args = create_parser().parse_args()
    parameters = create_parameters(args)

    result = run_pipeline(args.input, args.algorithm, parameters)
    print_result(result)

    if args.output:
        save_result_csv(result, args.output)
        print(f"\nResult salvo em: {args.output}")


if __name__ == "__main__":
    main()
