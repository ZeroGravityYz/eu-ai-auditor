import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from eu_ai_auditor import (
    build_evidence_bundle,
    build_research_crate,
    calculate_cdd,
    calculate_intersectional_parity,
    calculate_proxy_matrix,
    verify_research_crate,
)
from eu_ai_auditor.demo import make_demo_dataset
from eu_ai_auditor.research_cli import main as research_main


def _crate(include_source_data=False):
    data = make_demo_dataset(rows=180)
    cdd = calculate_cdd(data, "genre", "Femme", "selection", "Retenu", ["diplome"])
    proxy = calculate_proxy_matrix(data, ["genre"], ["age", "diplome"], min_pairs=5)
    intersections = calculate_intersectional_parity(
        data, ["genre"], "selection", "Retenu", min_group_count=20
    )
    evidence = build_evidence_bundle(
        data,
        cdd,
        proxy,
        intersectional_result=intersections,
        metadata={"system_name": "Research test"},
        generated_at="2026-09-05T00:00:00+00:00",
    )
    payload = build_research_crate(
        data,
        evidence,
        audit_kind="test",
        config={"decision": "selection"},
        tables={"cdd": cdd.strata, "intersections": intersections.groups},
        title="Research test",
        include_source_data=include_source_data,
        generated_at="2026-09-05T00:00:00+00:00",
    )
    return payload


def test_research_crate_is_deterministic_verifiable_and_private_by_default():
    payload = _crate()
    assert payload == _crate()
    assert verify_research_crate(payload) == {"valid": True, "errors": []}

    with ZipFile(BytesIO(payload)) as archive:
        names = set(archive.namelist())
        assert "ro-crate-metadata.json" in names
        assert "metadata/croissant.json" in names
        assert "CITATION.cff" in names
        assert "data/source.csv" not in names
        metadata = json.loads(archive.read("ro-crate-metadata.json"))
        assert metadata["@context"].endswith("/1.3/context")
        croissant = json.loads(archive.read("metadata/croissant.json"))
        assert croissant["dct:conformsTo"].endswith("/croissant/1.1")
        assert b"NaN" not in archive.read("audit/manifest.json")
        assert b"Infinity" not in archive.read("audit/manifest.json")


def test_research_crate_can_explicitly_include_source_rows():
    payload = _crate(include_source_data=True)
    with ZipFile(BytesIO(payload)) as archive:
        assert "data/source.csv" in archive.namelist()


def test_research_crate_detects_checksum_tampering():
    source = _crate()
    output = BytesIO()
    with ZipFile(BytesIO(source)) as original, ZipFile(output, "w", compression=ZIP_DEFLATED) as altered:
        for name in original.namelist():
            content = original.read(name)
            if name == "results/cdd.csv":
                content += b"tampered"
            altered.writestr(name, content)

    result = verify_research_crate(output.getvalue())
    assert result["valid"] is False
    assert "checksum mismatch: results/cdd.csv" in result["errors"]


def test_research_cli_infers_schema_and_verifies_crate(tmp_path):
    inference = tmp_path / "inference.json"
    assert (
        research_main(
            [
                "infer",
                "data/recrutement_demo.csv",
                "--output",
                str(inference),
            ]
        )
        == 0
    )
    assert json.loads(inference.read_text(encoding="utf-8"))["mapping"]["decision_attribute"] == "selection"

    crate = tmp_path / "research.zip"
    crate.write_bytes(_crate())
    assert research_main(["verify", str(crate)]) == 0


def test_research_cli_replays_a_saved_recipe(tmp_path):
    recipe = tmp_path / "recipe.json"
    recipe.write_text(
        json.dumps(
            {
                "protected_attributes": ["genre"],
                "protected_value": "Femme",
                "decision_attribute": "selection",
                "favourable_value": "Retenu",
                "conditioning_attributes": ["diplome"],
                "bootstrap_iterations": 0,
                "intersection_min_group_count": 20,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "replayed"

    assert (
        research_main(
            [
                "run",
                "data/recrutement_demo.csv",
                str(recipe),
                "--output-dir",
                str(output),
            ]
        )
        == 0
    )
    assert (output / "audit.pdf").read_bytes().startswith(b"%PDF")
    assert verify_research_crate((output / "research-ro-crate.zip").read_bytes())["valid"]
