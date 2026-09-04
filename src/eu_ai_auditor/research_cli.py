"""Research interoperability commands for schema inference and crate verification."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .cli import main as audit_main
from .csv_io import read_csv_flexible
from .research_bundle import verify_research_crate
from .schema_inference import infer_audit_schema
from .serialization import json_compatible


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eu-ai-auditor-research",
        description="Infer audit mappings and verify portable research RO-Crates.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    infer = subparsers.add_parser("infer", help="Suggest column roles for a CSV")
    infer.add_argument("csv", type=Path)
    infer.add_argument("--mode", choices=["classic", "oversight"], default="classic")
    infer.add_argument("--output", type=Path)
    verify = subparsers.add_parser("verify", help="Verify a research RO-Crate ZIP")
    verify.add_argument("crate", type=Path)
    run = subparsers.add_parser("run", help="Re-run an audit from a JSON recipe")
    run.add_argument("csv", type=Path)
    run.add_argument("recipe", type=Path)
    run.add_argument("--output-dir", type=Path, default=Path("output/research-run"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "infer":
        data = read_csv_flexible(args.csv)
        payload = json.dumps(
            json_compatible(infer_audit_schema(data, mode=args.mode).summary()),
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload)
        return 0

    if args.command == "verify":
        result = verify_research_crate(args.crate.read_bytes())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["valid"] else 1

    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    required = [
        "protected_attributes",
        "protected_value",
        "decision_attribute",
        "favourable_value",
    ]
    missing = [key for key in required if key not in recipe]
    if missing:
        raise ValueError("Recette incomplète: " + ", ".join(missing))
    protected = list(recipe["protected_attributes"])
    if not protected:
        raise ValueError("Recette incomplète: protected_attributes est vide")
    output_dir = args.output_dir
    command = [
        str(args.csv),
        "--protected",
        str(protected[0]),
        "--protected-value",
        str(recipe["protected_value"]),
        "--decision",
        str(recipe["decision_attribute"]),
        "--favourable-value",
        str(recipe["favourable_value"]),
        "--materiality-threshold",
        str(recipe.get("materiality_threshold", 0.05)),
        "--min-outcome-count",
        str(recipe.get("min_outcome_count", 5)),
        "--intersection-min-group-count",
        str(recipe.get("intersection_min_group_count", recipe.get("min_group_count", 30))),
        "--bootstrap-iterations",
        str(recipe.get("bootstrap_iterations", 250)),
        "--confidence-level",
        str(recipe.get("confidence_level", 0.95)),
        "--fdr-alpha",
        str(recipe.get("fdr_alpha", 0.05)),
        "--stability-max-factors",
        str(recipe.get("stability_max_factors", 2)),
        "--stability-consensus-threshold",
        str(recipe.get("stability_consensus_threshold", 0.80)),
        "--stability-min-valid-share",
        str(recipe.get("stability_min_valid_share", 0.80)),
        "--output",
        str(output_dir / "audit.pdf"),
        "--evidence",
        str(output_dir / "manifest.json"),
        "--json",
        str(output_dir / "results.json"),
        "--research-bundle",
        str(output_dir / "research-ro-crate.zip"),
    ]
    for column in protected[1:]:
        command.extend(["--additional-protected", str(column)])
    for column in recipe.get("conditioning_attributes", []):
        command.extend(["--condition", str(column)])
    return audit_main(command)


if __name__ == "__main__":
    raise SystemExit(main())
