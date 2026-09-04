import pandas as pd
import pytest

from eu_ai_auditor import infer_audit_schema


def test_classic_schema_inference_supports_english_research_data():
    data = pd.DataFrame(
        {
            "applicant_id": [1, 2, 3, 4],
            "gender": ["F", "M", "F", "M"],
            "education": ["BA", "MA", "PhD", "BA"],
            "approved": [True, False, True, False],
        }
    )

    result = infer_audit_schema(data)

    assert result.mapping["decision_attribute"] == "approved"
    assert result.mapping["protected_attribute"] == "gender"
    assert result.value_suggestions["favourable_value"] is True
    assert result.conditioning_candidates == ("education",)
    assert result.confidence["decision_attribute"] >= 0.9


def test_oversight_schema_inference_maps_the_full_decision_chain():
    data = pd.DataFrame(
        {
            "case_id": ["a", "b"],
            "gender": ["F", "M"],
            "ai_recommendation": ["yes", "no"],
            "human_decision": ["yes", "no"],
            "ground_truth": ["yes", "yes"],
            "ai_visible": [True, False],
            "appeal": [False, True],
            "final_decision": ["yes", "yes"],
        }
    )

    result = infer_audit_schema(data, mode="oversight")

    assert result.mapping["ai_recommendation_attribute"] == "ai_recommendation"
    assert result.mapping["human_decision_attribute"] == "human_decision"
    assert result.mapping["ground_truth_attribute"] == "ground_truth"
    assert result.mapping["appeal_attribute"] == "appeal"
    assert result.mapping["cluster_attribute"] == "case_id"


def test_schema_inference_rejects_unknown_modes():
    with pytest.raises(ValueError, match="mode"):
        infer_audit_schema(pd.DataFrame({"x": [1]}), mode="unknown")


def test_schema_inference_rejects_non_string_column_names():
    with pytest.raises(ValueError, match="noms de colonnes"):
        infer_audit_schema(pd.DataFrame({1: ["yes"], 2: ["group"]}))
