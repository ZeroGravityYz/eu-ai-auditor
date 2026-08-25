import pandas as pd
import pytest

from eu_ai_auditor import calculate_oversight_parity


def _experimental_frame(repeats: int = 12) -> pd.DataFrame:
    rows = []
    patterns = {
        ("Femme", False): [1, 0, 1, 0],
        ("Femme", True): [1, 0, 0, 0],
        ("Homme", False): [1, 0, 1, 0],
        ("Homme", True): [1, 1, 1, 0],
    }
    for (group, exposed), outcomes in patterns.items():
        for index in range(repeats):
            human = outcomes[index % len(outcomes)]
            ai = 0 if group == "Femme" else 1
            truth = index % 2
            adverse = human == 0
            appeal = adverse and index % 3 == 0
            final = 1 if appeal and truth == 1 else human
            rows.append(
                {
                    "genre": group,
                    "qualification": "A" if index % 2 else "B",
                    "ai_decision": ai,
                    "human_decision": human,
                    "truth": truth,
                    "ai_visible": exposed,
                    "appeal": appeal,
                    "final_decision": final,
                    "decision_at": "2026-01-01",
                    "final_at": "2026-01-10" if appeal else "2026-02-15",
                }
            )
    return pd.DataFrame(rows)


def test_oversight_detects_differential_automation_response():
    result = calculate_oversight_parity(
        _experimental_frame(),
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="ai_decision",
        human_decision_attribute="human_decision",
        favourable_value=1,
        exposure_attribute="ai_visible",
        exposed_value=True,
        unexposed_value=False,
        exposure_randomized=True,
        min_group_count=2,
    )

    assert result.metrics["automation_effect_protected"] == pytest.approx(-0.25)
    assert result.metrics["automation_effect_reference"] == pytest.approx(0.25)
    assert result.metrics["automation_bias_gap"] == pytest.approx(-0.5)
    assert "randomisée" in result.causal_interpretation
    assert "réponse à l'assistance IA" in result.status


def test_oversight_measures_corrections_appeals_and_timeliness():
    result = calculate_oversight_parity(
        _experimental_frame(),
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="ai_decision",
        human_decision_attribute="human_decision",
        favourable_value=1,
        conditioning_attributes=["qualification"],
        ground_truth_attribute="truth",
        ground_truth_favourable_value=1,
        appeal_attribute="appeal",
        appeal_value=True,
        final_decision_attribute="final_decision",
        decision_timestamp_attribute="decision_at",
        final_timestamp_attribute="final_at",
        remedy_sla_days=30,
        min_group_count=1,
    )

    metrics = set(result.comparisons["metric"])
    assert {"helpful_override_rate", "harmful_override_rate"} <= metrics
    assert {"appeal_access_rate", "remedy_rate", "timely_remedy_rate"} <= metrics
    assert result.group_metrics["rows"].sum() == len(_experimental_frame())
    assert result.coverage == pytest.approx(1.0)
    assert "Non estimé" in result.causal_interpretation


def test_oversight_bootstrap_is_reproducible():
    data = pd.concat([_experimental_frame(20)] * 3, ignore_index=True)
    kwargs = dict(
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="ai_decision",
        human_decision_attribute="human_decision",
        favourable_value=1,
        exposure_attribute="ai_visible",
        exposure_randomized=True,
        min_group_count=2,
        bootstrap_iterations=40,
        random_state=7,
    )
    first = calculate_oversight_parity(data, **kwargs)
    second = calculate_oversight_parity(data, **kwargs)

    assert first.intervals["automation_bias_gap"] == second.intervals["automation_bias_gap"]
    assert first.intervals["automation_bias_gap"] is not None
    assert first.bootstrap_valid_iterations == 40


def test_oversight_rejects_ambiguous_reference_group():
    data = _experimental_frame()
    data.loc[0, "genre"] = "Non-binaire"
    with pytest.raises(ValueError, match="reference_value"):
        calculate_oversight_parity(
            data,
            protected_attribute="genre",
            protected_value="Femme",
            ai_recommendation_attribute="ai_decision",
            human_decision_attribute="human_decision",
            favourable_value=1,
        )


def test_missing_optional_process_stages_are_not_fabricated():
    result = calculate_oversight_parity(
        _experimental_frame().drop(columns=["appeal", "final_decision", "decision_at", "final_at"]),
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="ai_decision",
        human_decision_attribute="human_decision",
        favourable_value=1,
        min_group_count=2,
    )

    assert result.metrics["appeal_access_gap"] is None
    assert result.metrics["remedy_gap"] is None
    assert result.group_metrics["remedy_rate"].isna().all()


def test_cluster_bootstrap_preserves_paired_arms():
    data = _experimental_frame(16)
    data["case_id"] = data.groupby(["genre", data.groupby(["genre", "ai_visible"]).cumcount()]).ngroup()
    result = calculate_oversight_parity(
        data,
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="ai_decision",
        human_decision_attribute="human_decision",
        favourable_value=1,
        exposure_attribute="ai_visible",
        exposure_randomized=True,
        bootstrap_cluster_attribute="case_id",
        min_group_count=2,
        bootstrap_iterations=40,
        random_state=9,
    )

    assert result.bootstrap_valid_iterations == 40
    assert result.bootstrap_cluster_attribute == "case_id"
    assert any("Bootstrap par cluster" in note for note in result.notes)


def test_timestamps_require_a_final_decision():
    with pytest.raises(ValueError, match="décision finale"):
        calculate_oversight_parity(
            _experimental_frame(),
            protected_attribute="genre",
            protected_value="Femme",
            reference_value="Homme",
            ai_recommendation_attribute="ai_decision",
            human_decision_attribute="human_decision",
            favourable_value=1,
            decision_timestamp_attribute="decision_at",
            final_timestamp_attribute="final_at",
        )
