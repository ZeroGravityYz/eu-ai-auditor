import pandas as pd
import pytest

from eu_ai_auditor import calculate_intersectional_parity


def _intersection_frame() -> pd.DataFrame:
    rows = []
    for gender, age, total, favourable in [
        ("F", "young", 40, 10),
        ("F", "older", 40, 20),
        ("M", "young", 60, 48),
        ("M", "older", 60, 42),
    ]:
        rows.extend([(gender, age, "yes")] * favourable)
        rows.extend([(gender, age, "no")] * (total - favourable))
    return pd.DataFrame(rows, columns=["gender", "age_band", "decision"])


def test_intersectional_analysis_reports_uncertainty_and_fdr_priorities():
    result = calculate_intersectional_parity(
        _intersection_frame(),
        ["gender", "age_band"],
        "decision",
        "yes",
        min_group_count=20,
        materiality_threshold=0.05,
    )

    assert result.eligible_groups == 4
    assert result.coverage == 1
    assert result.worst_case_gap == pytest.approx(0.55)
    assert result.lowest_rate_group == "gender=F × age_band=young"
    assert result.highest_rate_group == "gender=M × age_band=young"
    assert result.flagged_groups >= 2
    assert result.groups["q_value"].notna().all()
    assert (result.groups["confidence_low"] <= result.groups["favourable_rate"]).all()
    assert (result.groups["confidence_high"] >= result.groups["favourable_rate"]).all()


def test_sparse_intersections_remain_visible_but_are_not_tested():
    data = _intersection_frame()
    sparse = pd.DataFrame(
        {"gender": ["X"] * 3, "age_band": ["other"] * 3, "decision": ["yes", "no", "no"]}
    )
    result = calculate_intersectional_parity(
        pd.concat([data, sparse], ignore_index=True),
        ["gender", "age_band"],
        "decision",
        "yes",
        min_group_count=20,
    )

    row = result.groups[result.groups["group"] == "gender=X × age_band=other"].iloc[0]
    assert bool(row["eligible"]) is False
    assert pd.isna(row["q_value"])
    assert result.coverage == pytest.approx(200 / 203)
    assert any("conservée" in note for note in result.notes)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"protected_attributes": []}, "attribut protégé"),
        ({"min_group_count": 1}, "min_group_count"),
        ({"fdr_alpha": 1.0}, "fdr_alpha"),
    ],
)
def test_intersectional_parameters_are_validated(kwargs, message):
    defaults = {
        "protected_attributes": ["gender"],
        "decision_attribute": "decision",
        "favourable_value": "yes",
        "min_group_count": 2,
        "fdr_alpha": 0.05,
    }
    defaults.update(kwargs)
    with pytest.raises(ValueError, match=message):
        calculate_intersectional_parity(_intersection_frame(), **defaults)
