"""Command-line entry point for OversightParity process audits."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .csv_io import read_csv_flexible
from .evidence import build_oversight_evidence_bundle
from .oversight import calculate_oversight_parity
from .oversight_report import generate_oversight_report
from .serialization import json_compatible


def _match_value(series: pd.Series, raw: str) -> Any:
    for value in series.dropna().unique():
        if str(value) == raw:
            return value
    raise ValueError(f"Valeur {raw!r} absente de la colonne {series.name!r}.")


def _optional_value(data: pd.DataFrame, column: str | None, raw: str | None) -> Any | None:
    if column is None or raw is None:
        return None
    return _match_value(data[column], raw)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eu-ai-auditor-oversight",
        description="Audit fairness de la chaîne recommandation IA, décision humaine et recours.",
    )
    parser.add_argument("csv", type=Path, help="Journal CSV à analyser")
    parser.add_argument("--protected", required=True, help="Attribut protégé")
    parser.add_argument("--protected-value", required=True, help="Groupe protégé")
    parser.add_argument("--reference-value", required=True, help="Groupe de référence")
    parser.add_argument("--ai-recommendation", required=True, help="Recommandation IA")
    parser.add_argument("--human-decision", required=True, help="Décision humaine initiale")
    parser.add_argument("--favourable-value", required=True, help="Issue favorable")
    parser.add_argument("--condition", action="append", default=[], help="Facteur légitime R")
    parser.add_argument("--ground-truth", help="Colonne de vérité terrain")
    parser.add_argument("--ground-truth-favourable-value", help="Issue favorable de vérité terrain")
    parser.add_argument("--exposure", help="Colonne indiquant si la recommandation était visible")
    parser.add_argument("--exposed-value", help="Valeur indiquant l'exposition")
    parser.add_argument("--unexposed-value", help="Valeur indiquant l'absence d'exposition")
    parser.add_argument(
        "--randomized-exposure",
        action="store_true",
        help="Déclare que l'exposition a été randomisée selon un protocole documenté",
    )
    parser.add_argument("--appeal", help="Colonne de recours")
    parser.add_argument("--appeal-value", help="Valeur indiquant un recours")
    parser.add_argument("--final-decision", help="Décision après recours ou revue")
    parser.add_argument("--decision-timestamp", help="Horodatage de la décision initiale")
    parser.add_argument("--final-timestamp", help="Horodatage de la décision finale")
    parser.add_argument("--remedy-sla-days", type=float, default=30.0)
    parser.add_argument("--bootstrap-cluster", help="Identifiant de cas pour bootstrap groupé")
    parser.add_argument("--min-group-count", type=int, default=5)
    parser.add_argument("--materiality-threshold", type=float, default=0.05)
    parser.add_argument("--bootstrap-iterations", type=int, default=100)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--system-name", default="Système de décision assistée")
    parser.add_argument("--provider-name", default="À compléter")
    parser.add_argument("--auditor", default="À compléter")
    parser.add_argument(
        "--output", type=Path, default=Path("output/pdf/rapport_oversight_parity.pdf")
    )
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("output/evidence/oversight_manifest.json"),
    )
    parser.add_argument(
        "--signing-key-env",
        help="Nom d'une variable d'environnement contenant la clé HMAC optionnelle",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    data = read_csv_flexible(args.csv)
    protected_value = _match_value(data[args.protected], args.protected_value)
    reference_value = _match_value(data[args.protected], args.reference_value)
    favourable_value = _match_value(data[args.human_decision], args.favourable_value)
    ground_truth_favourable = _optional_value(
        data, args.ground_truth, args.ground_truth_favourable_value
    )
    exposed_value = _optional_value(data, args.exposure, args.exposed_value)
    unexposed_value = _optional_value(data, args.exposure, args.unexposed_value)
    appeal_value = _optional_value(data, args.appeal, args.appeal_value)
    if args.exposure and (exposed_value is None or unexposed_value is None):
        raise ValueError("--exposed-value et --unexposed-value sont requis avec --exposure.")
    if args.appeal and appeal_value is None:
        raise ValueError("--appeal-value est requis avec --appeal.")

    result = calculate_oversight_parity(
        data,
        protected_attribute=args.protected,
        protected_value=protected_value,
        reference_value=reference_value,
        ai_recommendation_attribute=args.ai_recommendation,
        human_decision_attribute=args.human_decision,
        favourable_value=favourable_value,
        conditioning_attributes=args.condition,
        ground_truth_attribute=args.ground_truth,
        ground_truth_favourable_value=ground_truth_favourable,
        exposure_attribute=args.exposure,
        exposed_value=exposed_value,
        unexposed_value=unexposed_value,
        exposure_randomized=args.randomized_exposure,
        appeal_attribute=args.appeal,
        appeal_value=appeal_value,
        final_decision_attribute=args.final_decision,
        decision_timestamp_attribute=args.decision_timestamp,
        final_timestamp_attribute=args.final_timestamp,
        remedy_sla_days=args.remedy_sla_days,
        bootstrap_cluster_attribute=args.bootstrap_cluster,
        min_group_count=args.min_group_count,
        materiality_threshold=args.materiality_threshold,
        bootstrap_iterations=args.bootstrap_iterations,
        confidence_level=args.confidence_level,
    )
    metadata = {
        "system_name": args.system_name,
        "provider_name": args.provider_name,
        "auditor": args.auditor,
    }
    prebundle = build_oversight_evidence_bundle(data, result, metadata=metadata)
    metadata["audit_id"] = prebundle["audit_id"]
    pdf = generate_oversight_report(
        data,
        result,
        metadata=metadata,
        output_path=args.output,
    )
    signing_key = None
    if args.signing_key_env:
        signing_key = os.environ.get(args.signing_key_env)
        if signing_key is None:
            raise ValueError(
                f"Variable d'environnement absente pour la signature: {args.signing_key_env}"
            )
    evidence = build_oversight_evidence_bundle(
        data,
        result,
        metadata=metadata,
        report_bytes=pdf,
        signing_key=signing_key,
    )
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(json_compatible(evidence), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    print(f"Rapport OversightParity créé: {args.output.resolve()}")
    print(f"Manifeste créé: {args.evidence.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
