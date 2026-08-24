import pandas as pd

from eu_ai_auditor import calculate_risk_quadrants


def test_quadrants_flag_large_group_disparity():
    data = pd.DataFrame(
        {
            "group": ["A"] * 100 + ["B"] * 100,
            "decision": ["oui"] * 90 + ["non"] * 10 + ["oui"] * 10 + ["non"] * 90,
        }
    )
    result = calculate_risk_quadrants(
        data, ["group"], "decision", "oui", mean_threshold=0.10, max_threshold=0.20
    )

    row = result.features.iloc[0]
    assert row["weighted_mean_disparity"] == 0.4
    assert row["maximum_disparity"] == 0.4
    assert row["quadrant"] == "Biais extrême"

