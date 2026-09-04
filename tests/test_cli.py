import json

from eu_ai_auditor.cli import main as audit_main
from eu_ai_auditor.evidence import verify_evidence_bundle
from eu_ai_auditor.research_bundle import verify_research_crate
from eu_ai_auditor.verify_cli import main as verify_main


def test_cli_creates_pdf_and_verifiable_manifest(tmp_path):
    pdf = tmp_path / "audit.pdf"
    evidence = tmp_path / "audit.json"
    research = tmp_path / "audit-ro-crate.zip"
    result = audit_main(
        [
            "data/recrutement_demo.csv",
            "--protected",
            "genre",
            "--protected-value",
            "Femme",
            "--decision",
            "selection",
            "--favourable-value",
            "Retenu",
            "--condition",
            "diplome",
            "--bootstrap-iterations",
            "40",
            "--output",
            str(pdf),
            "--evidence",
            str(evidence),
            "--research-bundle",
            str(research),
        ]
    )

    assert result == 0
    assert pdf.read_bytes().startswith(b"%PDF")
    bundle = json.loads(evidence.read_text(encoding="utf-8"))
    assert verify_evidence_bundle(bundle, report_bytes=pdf.read_bytes())["valid"] is True
    assert bundle["results"]["intersectional"] is not None
    assert verify_research_crate(research.read_bytes())["valid"] is True
    assert verify_main([str(evidence), "--report", str(pdf)]) == 0
