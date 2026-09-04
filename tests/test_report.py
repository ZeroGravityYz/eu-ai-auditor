from io import BytesIO

from pypdf import PdfReader

from eu_ai_auditor import (
    calculate_cdd,
    calculate_fairness_stability,
    calculate_proxy_matrix,
    calculate_risk_quadrants,
)
from eu_ai_auditor.demo import make_demo_dataset
from eu_ai_auditor.report_generator import generate_compliance_report


def test_report_is_readable_and_contains_guardrails():
    data = make_demo_dataset(rows=180)
    cdd = calculate_cdd(
        data,
        "genre",
        "Femme",
        "selection",
        "Retenu",
        ["diplome"],
        min_outcome_count=2,
    )
    proxy = calculate_proxy_matrix(
        data,
        ["genre"],
        ["age", "diplome", "anciennete_annees", "zone_postale", "secteur"],
        min_pairs=5,
    )
    quadrants = calculate_risk_quadrants(data, ["genre"], "selection", "Retenu")
    stability = calculate_fairness_stability(
        data,
        "genre",
        "Femme",
        "selection",
        "Retenu",
        ["diplome", "anciennete_annees"],
        max_conditioning_factors=2,
        min_outcome_count=2,
    )
    payload = generate_compliance_report(
        data,
        cdd,
        proxy,
        quadrant_result=quadrants,
        stability_result=stability,
        metadata={
            "system_name": "Test recrutement",
            "provider_name": "Organisation test",
            "system_version": "1.0",
            "intended_purpose": "Test de non-régression",
            "protected_attributes": ["genre"],
        },
    )

    assert payload.startswith(b"%PDF")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) >= 6
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Article 10" in text
    assert "ne constitue ni une certification" in text
    assert "Article 14" in text
    assert "Robustesse multivers" in text
    assert "Spécifications valides" in text
