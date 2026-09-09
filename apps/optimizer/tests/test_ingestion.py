import math
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion import decimal_to_float, preprocess


def test_preprocess_removes_rows_with_nan_in_numeric_columns():
    clients = preprocess(
        [
            {
                "token": "ok",
                "product_pd": 0.1,
                "payment_capacity": 1000.0,
                "contract_propensity_score": 0.5,
            },
            {
                "token": "sem_pd",
                "product_pd": math.nan,
                "payment_capacity": 1000.0,
                "contract_propensity_score": 0.5,
            },
            {
                "token": "sem_score",
                "product_pd": 0.1,
                "payment_capacity": 1000.0,
                "contract_propensity_score": "nan",
            },
        ]
    )

    assert [client.token for client in clients] == ["ok"]


def test_decimal_to_float_rejects_non_finite_value():
    try:
        decimal_to_float("nan")
    except ValueError as error:
        assert "Invalid numeric value" in str(error)
    else:
        raise AssertionError("decimal_to_float deveria rejeitar NaN")
