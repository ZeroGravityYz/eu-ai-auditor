import pandas as pd
import pytest

from eu_ai_auditor import calculate_fairness_stability


def _berkeley_frame() -> pd.DataFrame:
    counts = {
        "A": (512, 89, 313, 19),
        "B": (313, 17, 207, 8),
        "C": (120, 202, 205, 391),
        "D": (138, 131, 279, 244),
        "E": (53, 94, 138, 299),
        "F": (22, 24, 351, 317),
    }
    rows = []
    for department, (male_a, female_a, male_d, female_d) in counts.items():
        rows.extend([(department, "Homme", "Admis")] * male_a)
        rows.extend([(department, "Femme", "Admis")] * female_a)
        rows.extend([(department, "Homme", "Refusé")] * male_d)
        rows.extend([(department, "Femme", "Refusé")] * female_d)
    return pd.DataFrame(rows, columns=["departement", "genre", "decision"])


def test_berkeley_conclusion_is_flagged_as_specification_sensitive():
    result = calculate_fairness_stability(
        _berkeley_frame(),
        "genre",
        "Femme",
        "decision",
        "Admis",
        ["departement"],
        max_conditioning_factors=1,
        min_outcome_count=1,
        materiality_threshold=0.05,
    )

    assert result.total_specifications == 2
    assert result.valid_specifications == 2
    assert result.gap_min < 0 < result.gap_max
    assert result.range_crosses_zero is True
    assert result.dominant_share == pytest.approx(0.5)
    assert "sensible" in result.status
    assert result.factor_effects.loc[0, "class_flip_rate"] == pytest.approx(1.0)


def test_irrelevant_conditioner_preserves_a_robust_conclusion():
    data = pd.DataFrame(
        {
            "genre": ["F"] * 60 + ["H"] * 40 + ["F"] * 20 + ["H"] * 80,
            "decision": ["non"] * 100 + ["oui"] * 100,
            "site": ["unique"] * 200,
        }
    )
    result = calculate_fairness_stability(
        data,
        "genre",
        "F",
        "decision",
        "oui",
        "site",
        max_conditioning_factors=1,
        min_outcome_count=5,
        materiality_threshold=0.05,
    )

    assert result.dominant_class == "adverse_material"
    assert result.dominant_share == pytest.approx(1.0)
    assert result.robustness_score == pytest.approx(1.0)
    assert result.factor_effects.loc[0, "median_absolute_shift"] == pytest.approx(0.0)
    assert "robuste" in result.status


@pytest.mark.parametrize(
    ("candidates", "maximum", "message"),
    [
        ([], 1, "facteur R"),
        (["genre"], 1, "attribut protégé"),
        (["site"], 2, "dépasse"),
    ],
)
def test_stability_parameters_are_validated(candidates, maximum, message):
    data = pd.DataFrame(
        {
            "genre": ["F", "H", "F", "H"],
            "decision": ["oui", "oui", "non", "non"],
            "site": ["A", "A", "A", "A"],
        }
    )
    with pytest.raises(ValueError, match=message):
        calculate_fairness_stability(
            data,
            "genre",
            "F",
            "decision",
            "oui",
            candidates,
            max_conditioning_factors=maximum,
            min_outcome_count=1,
        )


def test_stability_rejects_an_excessive_specification_universe():
    data = pd.DataFrame(
        {
            "s": [0, 1, 0, 1],
            "y": [0, 0, 1, 1],
            **{f"r{index}": ["A"] * 4 for index in range(5)},
        }
    )
    with pytest.raises(ValueError, match="limite"):
        calculate_fairness_stability(
            data,
            "s",
            1,
            "y",
            1,
            [f"r{index}" for index in range(5)],
            max_conditioning_factors=3,
            max_specifications=5,
            min_outcome_count=1,
        )
