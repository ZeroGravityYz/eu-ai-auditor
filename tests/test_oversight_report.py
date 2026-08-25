from io import BytesIO

from pypdf import PdfReader

from eu_ai_auditor import calculate_oversight_parity
from eu_ai_auditor.oversight_demo import make_oversight_demo
from eu_ai_auditor.oversight_report import generate_oversight_report


def test_oversight_report_is_readable_and_preserves_causal_guardrail():
    data = make_oversight_demo(rows=320)
    result = calculate_oversight_parity(
        data,
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="recommandation_ia",
        human_decision_attribute="decision_humaine",
        favourable_value="Favorable",
        conditioning_attributes=["diplome"],
        ground_truth_attribute="verite_terrain",
        exposure_attribute="ia_visible",
        exposed_value="Visible",
        unexposed_value="Masquée",
        exposure_randomized=True,
        appeal_attribute="recours",
        appeal_value="Oui",
        final_decision_attribute="decision_finale",
        decision_timestamp_attribute="decision_at",
        final_timestamp_attribute="final_at",
        min_group_count=2,
    )
    payload = generate_oversight_report(
        data,
        result,
        metadata={"system_name": "Processus de recrutement test", "audit_id": "oversight-test"},
    )

    assert payload.startswith(b"%PDF")
    reader = PdfReader(BytesIO(payload))
    assert len(reader.pages) >= 6
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Causal Automation Bias Gap" in text
    assert "ne constitue ni une" in text
    assert "Article 14" in text
    assert "Article 86" in text
