"""Command-line entry point for reproducible batch audits."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from .cdd_engine import calculate_cdd
from .data_quality import profile_dataset
from .evidence import build_evidence_bundle
from .proxy_matrix import calculate_proxy_matrix
from .report_generator import generate_compliance_report
from .risk_quadrants import calculate_risk_quadrants
from .tradeoff import compare_models


def _match_value(series: pd.Series, raw: str) -> Any:
    for value in series.dropna().unique():
        if str(value) == raw:
            return value
    raise ValueError(f"Valeur {raw!r} absente de la colonne {series.name!r}.")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="eu-ai-auditor",
        description="Audit descriptif CDD, proxys et dossier de preuves AI Act.",
    )
    parser.add_argument("csv", type=Path, help="Fichier CSV à analyser")
    parser.add_argument("--protected", required=True, help="Variable protégée principale")
    parser.add_argument("--protected-value", required=True, help="Classe protégée")
    parser.add_argument("--decision", required=True, help="Variable de décision")
    parser.add_argument("--favourable-value", required=True, help="Issue favorable")
    parser.add_argument("--condition", action="append", default=[], help="Facteur R (répétable)")
    parser.add_argument("--additional-protected", action="append", default=[], help="Autre attribut protégé")
    parser.add_argument("--output", type=Path, default=Path("output/pdf/rapport_audit.pdf"))
    parser.add_argument("--json", dest="json_output", type=Path, help="Résumé JSON optionnel")
    parser.add_argument(
        "--evidence",
        type=Path,
        default=Path("output/evidence/audit_manifest.json"),
        help="Manifeste de preuves vérifiable",
    )
    parser.add_argument("--system-name", default="Système évalué")
    parser.add_argument("--provider-name", default="À compléter")
    parser.add_argument("--intended-purpose", default="À compléter")
    parser.add_argument("--with-tradeoff", action="store_true", help="Comparer LR et CART")
    parser.add_argument("--materiality-threshold", type=float, default=0.05)
    parser.add_argument("--min-outcome-count", type=int, default=5)
    parser.add_argument("--bootstrap-iterations", type=int, default=250)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument(
        "--signing-key-env",
        help="Nom d'une variable d'environnement contenant la clé HMAC optionnelle",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    data = pd.read_csv(args.csv, sep=None, engine="python")
    protected_value = _match_value(data[args.protected], args.protected_value)
    favourable_value = _match_value(data[args.decision], args.favourable_value)
    protected_attributes = list(dict.fromkeys([args.protected, *args.additional_protected]))

    cdd_result = calculate_cdd(
        data,
        protected_attribute=args.protected,
        protected_value=protected_value,
        decision_attribute=args.decision,
        advantaged_value=favourable_value,
        conditioning_attributes=args.condition,
        materiality_threshold=args.materiality_threshold,
        min_outcome_count=args.min_outcome_count,
        bootstrap_iterations=args.bootstrap_iterations,
        confidence_level=args.confidence_level,
    )
    candidates = [
        column
        for column in data.columns
        if column not in {*protected_attributes, args.decision}
    ]
    proxy_result = calculate_proxy_matrix(data, protected_attributes, candidates, min_pairs=10)
    quadrant_result = calculate_risk_quadrants(
        data, protected_attributes, args.decision, favourable_value
    )
    tradeoff_result = None
    if args.with_tradeoff:
        tradeoff_result = compare_models(
            data,
            target_attribute=args.decision,
            favourable_value=favourable_value,
            protected_attribute=args.protected,
            protected_value=protected_value,
            conditioning_attributes=args.condition,
            exclude_features=[column for column in protected_attributes if column != args.protected],
        )

    metadata = {
        "system_name": args.system_name,
        "provider_name": args.provider_name,
        "intended_purpose": args.intended_purpose,
        "protected_attributes": protected_attributes,
    }
    prebundle = build_evidence_bundle(
        data,
        cdd_result,
        proxy_result,
        quadrant_result=quadrant_result,
        tradeoff_result=tradeoff_result,
        metadata=metadata,
    )
    metadata["audit_id"] = prebundle["audit_id"]
    pdf = generate_compliance_report(
        data,
        cdd_result,
        proxy_result,
        quadrant_result=quadrant_result,
        tradeoff_result=tradeoff_result,
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
    evidence = build_evidence_bundle(
        data,
        cdd_result,
        proxy_result,
        quadrant_result=quadrant_result,
        tradeoff_result=tradeoff_result,
        metadata=metadata,
        report_bytes=pdf,
        signing_key=signing_key,
    )
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    if args.json_output:
        quality = profile_dataset(data, protected_attributes)
        payload = {
            "cdd": cdd_result.summary(),
            "quality": quality,
            "proxy_scores": proxy_result.scores.to_dict(orient="records"),
            "quadrants": quadrant_result.features.to_dict(orient="records"),
            "tradeoff": tradeoff_result.points.to_dict(orient="records") if tradeoff_result else None,
        }
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"Rapport créé: {args.output.resolve()}")
    print(f"Manifeste créé: {args.evidence.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
