import pandas as pd
import pytest

from eu_ai_auditor import calculate_cdd


def test_positive_cdd_signal_is_computed_from_group_composition():
    data = pd.DataFrame(
        {
            "genre": ["F", "F", "F", "F", "H", "H", "H", "H", "H", "H"],
            "decision": ["non", "non", "non", "oui", "non", "oui", "oui", "oui", "oui", "non"],
            "niveau": ["A"] * 10,
        }
    )

    result = calculate_cdd(
        data,
        protected_attribute="genre",
        protected_value="F",
        decision_attribute="decision",
        advantaged_value="oui",
        conditioning_attributes="niveau",
        min_outcome_count=1,
        materiality_threshold=0.10,
    )

    assert result.disadvantaged_share == pytest.approx(3 / 5)
    assert result.advantaged_share == pytest.approx(1 / 5)
    assert result.gap == pytest.approx(0.4)
    assert result.directional_signal is True
    assert result.material_signal is True


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


def test_berkeley_example_reverses_after_conditioning():
    data = _berkeley_frame()
    unconditioned = calculate_cdd(
        data, "genre", "Femme", "decision", "Admis", min_outcome_count=1
    )
    conditioned = calculate_cdd(
        data,
        "genre",
        "Femme",
        "decision",
        "Admis",
        conditioning_attributes="departement",
        min_outcome_count=1,
    )

    assert unconditioned.gap > 0.10
    assert conditioned.advantaged_share == pytest.approx(0.42, abs=0.01)
    assert conditioned.disadvantaged_share == pytest.approx(0.40, abs=0.01)
    assert conditioned.gap < 0


def test_sparse_strata_are_reported_and_excluded():
    data = pd.DataFrame(
        {
            "s": [0, 1, 0, 1, 0, 1],
            "y": [0, 1, 0, 1, 0, 1],
            "r": ["large", "large", "large", "large", "small", "small"],
        }
    )
    result = calculate_cdd(data, "s", 1, "y", 1, "r", min_outcome_count=2)

    assert result.strata.loc[result.strata["r"] == "small", "eligible"].item() is False
    assert result.coverage == pytest.approx(4 / 6)
    assert any("exclue" in note for note in result.notes)


def test_bootstrap_interval_is_reproducible_and_contains_point_estimate():
    data = pd.DataFrame(
        {
            "genre": ["F"] * 60 + ["H"] * 40 + ["F"] * 20 + ["H"] * 80,
            "decision": ["non"] * 100 + ["oui"] * 100,
            "niveau": ["A"] * 200,
        }
    )
    kwargs = {
        "protected_attribute": "genre",
        "protected_value": "F",
        "decision_attribute": "decision",
        "advantaged_value": "oui",
        "conditioning_attributes": "niveau",
        "min_outcome_count": 5,
        "bootstrap_iterations": 100,
        "confidence_level": 0.95,
        "random_state": 7,
    }
    first = calculate_cdd(data, **kwargs)
    second = calculate_cdd(data, **kwargs)

    assert first.confidence_low is not None
    assert first.confidence_high is not None
    assert first.confidence_low < first.gap < first.confidence_high
    assert first.confidence_low == pytest.approx(second.confidence_low)
    assert first.confidence_high == pytest.approx(second.confidence_high)
    assert first.bootstrap_valid_iterations == 100


def test_bootstrap_parameters_are_validated():
    data = pd.DataFrame({"s": [0, 1], "y": [0, 1]})
    with pytest.raises(ValueError, match="bootstrap_iterations"):
        calculate_cdd(data, "s", 1, "y", 1, bootstrap_iterations=-1)
    with pytest.raises(ValueError, match="confidence_level"):
        calculate_cdd(data, "s", 1, "y", 1, confidence_level=1.0)
