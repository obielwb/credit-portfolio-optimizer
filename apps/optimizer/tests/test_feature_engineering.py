import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from clustering import ClusteringConfig, ClusteringInput, PreprocessedClientInput, engineer_features


def test_engineer_features_selects_and_normalizes_custom_features():
    config = ClusteringConfig(
        enabled=True,
        max_clients_per_cluster=3,
        feature_set=("product_pd", "contract_propensity_score", "income"),
    )
    payload = ClusteringInput(
        clients=(
            PreprocessedClientInput(
                token="t1",
                product_pd=0.10,
                payment_capacity=1000.0,
                contract_propensity_score=0.20,
                extra_features={"income": 500.0},
            ),
            PreprocessedClientInput(
                token="t2",
                product_pd=0.20,
                payment_capacity=900.0,
                contract_propensity_score=0.40,
                extra_features={"income": 750.0},
            ),
            PreprocessedClientInput(
                token="t3",
                product_pd=0.30,
                payment_capacity=800.0,
                contract_propensity_score=0.60,
                extra_features={"income": 1000.0},
            ),
        ),
        config=config,
        run_id=7,
        source_file_id=11,
    )

    result = engineer_features(payload)

    assert result.feature_names == ("product_pd", "contract_propensity_score", "income")
    assert len(result.clients) == 3
    assert result.feature_matrix[0] == (0.0, 0.0, 0.0)
    assert result.feature_matrix[1] == (0.5, 0.5, 0.5)
    assert result.feature_matrix[2] == (1.0, 1.0, 1.0)
    assert result.clients[0].priority_score == 0.0
    assert result.clients[-1].priority_score == 1.0
