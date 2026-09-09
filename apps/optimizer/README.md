# Standalone optimizer

The optimizer converts a client portfolio into recommended credit limits while enforcing individual eligibility, portfolio default exposure, and operational limit constraints.

## Pipeline

1. Load CSV or Parquet input.
2. Validate required columns and numeric values.
3. Remove incomplete records and normalize propensity scores.
4. Apply eligibility filters.
5. Optionally group similar records with K-Means or MiniBatch K-Means.
6. Run the selected optimization strategy.
7. Apply limit floors, ceilings, and optional discretization.
8. Calculate client and portfolio metrics.

## Input contract

The required columns are:

```text
token
contract_propensity_score
product_pd
payment_capacity
filter_flag
```

`token` is an opaque identifier. `filter_flag=1` marks a record as ineligible when filtering is enabled. Extra columns are ignored.

The file in `examples/synthetic_clients.csv` contains generated demonstration values and does not represent real people or an institution's portfolio.

## Command-line usage

```bash
python -m pip install -r requirements.txt
PYTHONPATH=. python main.py \
  --input examples/synthetic_clients.csv \
  --algorithm simplex \
  --output results.csv
```

Supported algorithms:

- `simplex`: custom tableau-based linear optimization.
- `simplex_ortools`: equivalent linear model solved through OR-Tools.
- `branch_bound`: discrete search that prevents positive recommendations below the operational floor.

## Clustering behavior

Clustering reduces the optimization problem when an input contains many records. The implementation uses classic K-Means for smaller inputs and switches to MiniBatch K-Means when the estimated matrix size, client count, or available memory makes the classic fit unsuitable. A `MemoryError` during classic K-Means also triggers the MiniBatch fallback.

The clustering output preserves the contract required by the optimization stage:

- contiguous cluster identifiers;
- aggregate probability, propensity, and capacity metrics;
- assigned leverage policy;
- original member tokens for limit propagation.

## Extending the optimizer

An algorithm implements this callable shape:

```python
def optimize(clients: list[Client], parameters: ModelParameters) -> list[float]:
    ...
```

Return exactly one limit per input client in the same order, then register the callable in `algorithms/__init__.py`.

## Module layout

- `models.py`: immutable pipeline data structures.
- `ingestion.py`: input loading, validation, normalization, and CSV output.
- `evaluation.py`: financial metrics and portfolio aggregation.
- `constraints.py`: limit and eligibility rules.
- `clustering/`: features, policies, algorithms, validation, and cluster metrics.
- `algorithms/`: optimization strategies.
- `pipeline.py`: end-to-end orchestration.
- `tools/`: performance-reporting utilities.
- `tests/`: unit, integration, performance, and stress suites.
