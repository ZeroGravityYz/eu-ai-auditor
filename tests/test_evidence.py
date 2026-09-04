import json

from eu_ai_auditor import (
    build_evidence_bundle,
    build_oversight_evidence_bundle,
    calculate_cdd,
    calculate_fairness_stability,
    calculate_oversight_parity,
    calculate_proxy_matrix,
    calculate_risk_quadrants,
    dataframe_sha256,
    verify_evidence_bundle,
)
from eu_ai_auditor.demo import make_demo_dataset
from eu_ai_auditor.oversight_demo import make_oversight_demo


def _bundle(report: bytes = b"%PDF-test", signing_key: str | None = "secret"):
    data = make_demo_dataset(rows=160)
    cdd = calculate_cdd(data, "genre", "Femme", "selection", "Retenu", ["diplome"])
    proxy = calculate_proxy_matrix(data, ["genre"], ["age", "diplome"], min_pairs=5)
    quadrants = calculate_risk_quadrants(data, ["genre"], "selection", "Retenu")
    stability = calculate_fairness_stability(
        data,
        "genre",
        "Femme",
        "selection",
        "Retenu",
        ["diplome"],
        max_conditioning_factors=1,
    )
    return data, build_evidence_bundle(
        data,
        cdd,
        proxy,
        quadrant_result=quadrants,
        stability_result=stability,
        metadata={"system_name": "Test", "system_version": "1"},
        report_bytes=report,
        generated_at="2026-08-25T00:00:00+00:00",
        signing_key=signing_key,
    )


def test_evidence_bundle_survives_json_roundtrip_and_verifies():
    data, bundle = _bundle()
    serialized = json.dumps(bundle, ensure_ascii=False, allow_nan=False)
    restored = json.loads(serialized)
    result = verify_evidence_bundle(restored, report_bytes=b"%PDF-test", signing_key="secret")

    assert result["valid"] is True
    assert result["manifest_valid"] is True
    assert result["report_valid"] is True
    assert result["hmac_valid"] is True
    assert restored["dataset"]["sha256"] == dataframe_sha256(data)
    assert restored["results"]["stability"]["summary"]["total_specifications"] == 2


def test_evidence_tampering_is_detected():
    _, bundle = _bundle(signing_key=None)
    bundle["metadata"]["system_name"] = "Altéré"
    result = verify_evidence_bundle(bundle, report_bytes=b"%PDF-test")

    assert result["valid"] is False
    assert result["manifest_valid"] is False


def test_wrong_report_is_detected():
    _, bundle = _bundle(signing_key=None)
    result = verify_evidence_bundle(bundle, report_bytes=b"different")

    assert result["manifest_valid"] is True
    assert result["report_valid"] is False
    assert result["valid"] is False


def test_oversight_evidence_is_verifiable_without_source_rows():
    data = make_oversight_demo(rows=240)
    result = calculate_oversight_parity(
        data,
        protected_attribute="genre",
        protected_value="Femme",
        reference_value="Homme",
        ai_recommendation_attribute="recommandation_ia",
        human_decision_attribute="decision_humaine",
        favourable_value="Favorable",
        exposure_attribute="ia_visible",
        exposed_value="Visible",
        unexposed_value="Masquée",
        exposure_randomized=True,
        min_group_count=2,
    )
    bundle = build_oversight_evidence_bundle(
        data,
        result,
        metadata={"system_name": "Oversight test"},
        report_bytes=b"%PDF-oversight",
        generated_at="2026-08-25T00:00:00+00:00",
    )

    verification = verify_evidence_bundle(bundle, report_bytes=b"%PDF-oversight")
    assert verification["valid"] is True
    assert bundle["schema"] == "eu-ai-auditor.oversight-evidence.v1"
    assert bundle["audit_id"].startswith("oversight-")
    assert "source_rows" not in json.dumps(bundle)
