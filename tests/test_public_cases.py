import json
from pathlib import Path

import pandas as pd

from eu_ai_auditor import calculate_cdd

CASES = Path("data/cases")


def test_public_case_files_match_provenance_manifest():
    manifest = json.loads((CASES / "manifest.json").read_text(encoding="utf-8"))
    adult = pd.read_csv(CASES / "adult_income_sample.csv")
    credit = pd.read_csv(CASES / "south_german_credit.csv")

    assert manifest["schema"] == "eu-ai-auditor.public-datasets.v1"
    assert manifest["outputs"]["adult_income_sample.csv"]["rows"] == len(adult) == 6000
    assert manifest["outputs"]["south_german_credit.csv"]["rows"] == len(credit) == 1000
    assert manifest["sources"]["adult"]["doi"] == "10.24432/C5XW20"
    assert manifest["sources"]["south_german_credit"]["doi"] == "10.24432/C5X89F"


def test_adult_income_case_has_auditable_signal():
    adult = pd.read_csv(CASES / "adult_income_sample.csv")
    result = calculate_cdd(
        adult,
        "sex",
        "Female",
        "income",
        ">50K",
        ["education"],
        min_outcome_count=5,
    )
    assert result.gap is not None
    assert result.coverage > 0.85
    assert set(adult["income"]) == {"<=50K", ">50K"}


def test_credit_case_uses_unambiguous_age_group():
    credit = pd.read_csv(CASES / "south_german_credit.csv")
    result = calculate_cdd(
        credit,
        "age_group",
        "under_25",
        "credit_risk",
        "good",
        ["employment_duration"],
        min_outcome_count=5,
    )
    assert result.gap is not None
    assert set(credit["credit_risk"]) == {"bad", "good"}
    assert "personal_status_sex" in credit.columns
