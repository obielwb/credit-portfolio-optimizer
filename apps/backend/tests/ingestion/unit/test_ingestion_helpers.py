import io
import os
import sys

import pytest

# Ensure project `src` package is importable during tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import pandas as pd

from src.services.ingestion_service import (
    _normalize_partner_columns,
    _parse_bytes,
    _validate_or_raise,
    to_optimization_clients,
)


def test_ingestion_helpers_parse_and_validate():
    # build a minimal dataframe using partner column names (as received from upload)
    df = pd.DataFrame(
        {
            "token": ["t1"],
            "default_probability": [0.1],
            "payment_capacity": [1000],
            "contract_propensity": [0.5],
            "filter_flag": [0],
        }
    )

    # write to csv bytes
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    contents = buf.getvalue()

    # parse + normalize (same flow as start_ingestion)
    parsed = _normalize_partner_columns(_parse_bytes(contents, "file.csv"))
    assert not parsed.empty

    # normalize partner → internal column names before validation (mirrors service flow)
    normalized = _normalize_partner_columns(parsed)

    # validate should not raise
    _validate_or_raise(normalized)

    # convert to domain clients
    clients = to_optimization_clients(normalized)
    assert len(clients) == 1
