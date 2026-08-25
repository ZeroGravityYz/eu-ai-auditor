import json

from pypdf import PdfReader

from eu_ai_auditor.oversight_cli import main
from eu_ai_auditor.oversight_demo import make_oversight_demo


def test_oversight_cli_creates_report_and_verifiable_manifest(tmp_path):
    csv_path = tmp_path / "oversight.csv"
    pdf_path = tmp_path / "oversight.pdf"
    evidence_path = tmp_path / "oversight.json"
    make_oversight_demo(rows=260).to_csv(csv_path, index=False)

    exit_code = main(
        [
            str(csv_path),
            "--protected",
            "genre",
            "--protected-value",
            "Femme",
            "--reference-value",
            "Homme",
            "--ai-recommendation",
            "recommandation_ia",
            "--human-decision",
            "decision_humaine",
            "--favourable-value",
            "Favorable",
            "--condition",
            "diplome",
            "--ground-truth",
            "verite_terrain",
            "--ground-truth-favourable-value",
            "Favorable",
            "--exposure",
            "ia_visible",
            "--exposed-value",
            "Visible",
            "--unexposed-value",
            "Masquée",
            "--randomized-exposure",
            "--appeal",
            "recours",
            "--appeal-value",
            "Oui",
            "--final-decision",
            "decision_finale",
            "--decision-timestamp",
            "decision_at",
            "--final-timestamp",
            "final_at",
            "--bootstrap-iterations",
            "0",
            "--min-group-count",
            "2",
            "--output",
            str(pdf_path),
            "--evidence",
            str(evidence_path),
        ]
    )

    assert exit_code == 0
    assert len(PdfReader(pdf_path).pages) >= 6
    bundle = json.loads(evidence_path.read_text(encoding="utf-8"))
    assert bundle["schema"] == "eu-ai-auditor.oversight-evidence.v1"
    assert bundle["artifacts"]["report_pdf"]["bytes"] == pdf_path.stat().st_size
