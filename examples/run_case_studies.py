"""Generate reproducible PDF and evidence bundles for the public case studies."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from eu_ai_auditor import (
    build_evidence_bundle,
    calculate_cdd,
    calculate_proxy_matrix,
    calculate_risk_quadrants,
    compare_models,
)
from eu_ai_auditor.report_generator import generate_compliance_report


def _run_case(
    *,
    data_path: Path,
    slug: str,
    protected: str,
    protected_value: str,
    decision: str,
    favourable: str,
    conditioning: list[str],
    additional_protected: list[str],
    metadata: dict[str, str],
) -> dict[str, object]:
    data = pd.read_csv(data_path)
    protected_attributes = [protected, *additional_protected]
    candidates = [
        column for column in data.columns if column not in {*protected_attributes, decision}
    ]
    cdd = calculate_cdd(
        data,
        protected,
        protected_value,
        decision,
        favourable,
        conditioning,
        min_outcome_count=10,
        materiality_threshold=0.05,
        bootstrap_iterations=250,
        confidence_level=0.95,
        random_state=42,
    )
    proxy = calculate_proxy_matrix(data, protected_attributes, candidates, min_pairs=20)
    quadrants = calculate_risk_quadrants(data, protected_attributes, decision, favourable)
    tradeoff = compare_models(
        data,
        target_attribute=decision,
        favourable_value=favourable,
        protected_attribute=protected,
        protected_value=protected_value,
        conditioning_attributes=conditioning,
        exclude_features=additional_protected,
        random_state=42,
    )
    metadata = {**metadata, "protected_attributes": protected_attributes}
    prebundle = build_evidence_bundle(
        data,
        cdd,
        proxy,
        quadrant_result=quadrants,
        tradeoff_result=tradeoff,
        metadata=metadata,
    )
    metadata["audit_id"] = str(prebundle["audit_id"])
    pdf_path = Path("output/pdf") / f"case_{slug}.pdf"
    pdf = generate_compliance_report(
        data,
        cdd,
        proxy,
        quadrant_result=quadrants,
        tradeoff_result=tradeoff,
        metadata=metadata,
        output_path=pdf_path,
    )
    bundle = build_evidence_bundle(
        data,
        cdd,
        proxy,
        quadrant_result=quadrants,
        tradeoff_result=tradeoff,
        metadata=metadata,
        report_bytes=pdf,
    )
    evidence_path = Path("output/evidence") / f"case_{slug}.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return {
        "slug": slug,
        "rows": len(data),
        "gap": cdd.gap,
        "confidence_low": cdd.confidence_low,
        "confidence_high": cdd.confidence_high,
        "coverage": cdd.coverage,
        "high_risk_proxies": int((proxy.scores["risk"] == "Haut").sum()),
        "audit_id": bundle["audit_id"],
        "pdf": str(pdf_path),
        "evidence": str(evidence_path),
    }


def main() -> int:
    results = [
        _run_case(
            data_path=Path("data/cases/adult_income_sample.csv"),
            slug="adult_income",
            protected="sex",
            protected_value="Female",
            decision="income",
            favourable=">50K",
            conditioning=["education"],
            additional_protected=["race"],
            metadata={
                "system_name": "Adult Income - scénario d'accès socio-économique",
                "system_version": "case-study-1",
                "provider_name": "Démonstration EU AI Auditor",
                "auditor": "Exécution reproductible",
                "intended_purpose": "Démontrer un audit descriptif sur une issue de revenu; ne représente pas un système de recrutement.",
                "data_origin": "UCI Adult, extrait du Census 1994, échantillon déterministe de 6 000 lignes.",
                "dataset_license": "CC BY 4.0",
                "source_reference": "https://doi.org/10.24432/C5XW20",
                "geographic_scope": "États-Unis, données historiques; non représentatif de l'Union européenne actuelle.",
                "known_limitations": "Catégories historiques, finalité de revenu et biais de mesure; aucune conclusion de recrutement.",
            },
        ),
        _run_case(
            data_path=Path("data/cases/south_german_credit.csv"),
            slug="south_german_credit",
            protected="age_group",
            protected_value="under_25",
            decision="credit_risk",
            favourable="good",
            conditioning=["employment_duration"],
            additional_protected=["foreign_worker"],
            metadata={
                "system_name": "South German Credit - décision de crédit",
                "system_version": "case-study-1",
                "provider_name": "Démonstration EU AI Auditor",
                "auditor": "Exécution reproductible",
                "intended_purpose": "Démontrer un audit descriptif d'une décision de risque de crédit.",
                "data_origin": "UCI South German Credit, crédits de 1973-1975, 1 000 observations.",
                "dataset_license": "CC BY 4.0",
                "source_reference": "https://doi.org/10.24432/C5X89F",
                "geographic_scope": "Allemagne de l'Ouest, données historiques; non représentatif du marché actuel.",
                "known_limitations": "Échantillon ancien, mauvais crédits suréchantillonnés, catégories et montants historiques en DM.",
            },
        ),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
