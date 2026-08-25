import json

from eu_ai_auditor import (
    build_evidence_bundle,
    calculate_cdd,
    calculate_proxy_matrix,
    calculate_risk_quadrants,
    dataframe_sha256,
    verify_evidence_bundle,
)
from eu_ai_auditor.demo import make_demo_dataset


def _bundle(report: bytes = b"%PDF-test", signing_key: str | None = "secret"):
    data = make_demo_dataset(rows=160)
    cdd = calculate_cdd(data, "genre", "Femme", "selection", "Retenu", ["diplome"])
    proxy = calculate_proxy_matrix(data, ["genre"], ["age", "diplome"], min_pairs=5)
    quadrants = calculate_risk_quadrants(data, ["genre"], "selection", "Retenu")
    return data, build_evidence_bundle(
        data,
        cdd,
        proxy,
        quadrant_result=quadrants,
        metadata={"system_name": "Test", "system_version": "1"},
        report_bytes=report,
        generated_at="2026-08-25T00:00:00+00:00",
        signing_key=signing_key,
    )


def test_evidence_bundle_survives_json_roundtrip_and_verifies():
    data, bundle = _bundle()
    serialized = json.dumps(bundle, ensure_ascii=False, default=str)
    restored = json.loads(serialized)
    result = verify_evidence_bundle(restored, report_bytes=b"%PDF-test", signing_key="secret")

    assert result["valid"] is True
    assert result["manifest_valid"] is True
    assert result["report_valid"] is True
    assert result["hmac_valid"] is True
    assert restored["dataset"]["sha256"] == dataframe_sha256(data)


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
