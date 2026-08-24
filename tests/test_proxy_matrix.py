import numpy as np
import pandas as pd

from eu_ai_auditor import calculate_proxy_matrix


def test_proxy_matrix_supports_mixed_types_and_risk_labels():
    rng = np.random.default_rng(5)
    protected = np.array(["A", "B"] * 100)
    data = pd.DataFrame(
        {
            "protected": protected,
            "exact_proxy": protected.copy(),
            "numeric_proxy": (protected == "B").astype(float) + rng.normal(0, 0.02, 200),
            "noise": rng.normal(size=200),
        }
    )

    result = calculate_proxy_matrix(
        data,
        protected_attributes=["protected"],
        candidate_features=["exact_proxy", "numeric_proxy", "noise"],
    )

    exact = result.scores.set_index("feature").loc["exact_proxy"]
    numeric = result.scores.set_index("feature").loc["numeric_proxy"]
    assert exact["score"] > 0.95
    assert exact["risk"] == "Haut"
    assert numeric["score"] > 0.95
    assert numeric["method"] == "rapport de corrélation eta"
    assert result.matrix.shape == (3, 1)

