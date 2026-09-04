"""Multiverse sensitivity analysis for Conditional Demographic Disparity."""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from itertools import combinations
from typing import Any

import numpy as np
import pandas as pd

from .cdd_engine import calculate_cdd
from .models import StabilityResult

ADVERSE_MATERIAL = "adverse_material"
REVERSE_MATERIAL = "reverse_material"
WITHIN_MATERIALITY = "within_materiality"


def _signal_class(gap: float, threshold: float) -> str:
    if gap > threshold:
        return ADVERSE_MATERIAL
    if gap < -threshold:
        return REVERSE_MATERIAL
    return WITHIN_MATERIALITY


def _specifications(candidates: list[str], maximum: int) -> list[tuple[str, ...]]:
    return [
        specification
        for size in range(maximum + 1)
        for specification in combinations(candidates, size)
    ]


def calculate_fairness_stability(
    data: pd.DataFrame,
    protected_attribute: str,
    protected_value: Any,
    decision_attribute: str,
    favourable_value: Any,
    conditioning_candidates: str | Sequence[str],
    *,
    max_conditioning_factors: int = 2,
    min_outcome_count: int = 5,
    materiality_threshold: float = 0.05,
    consensus_threshold: float = 0.80,
    minimum_coverage: float = 0.80,
    minimum_valid_share: float = 0.80,
    max_specifications: int = 256,
) -> StabilityResult:
    """Measure whether a CDD conclusion survives alternative legitimate factors.

    Every subset from zero to ``max_conditioning_factors`` is evaluated. Candidate
    factors must be justified before execution: this function measures analyst-choice
    sensitivity and never decides which conditioning variables are legally legitimate.
    """

    raw_candidates = (
        [conditioning_candidates]
        if isinstance(conditioning_candidates, str)
        else list(conditioning_candidates)
    )
    candidates = list(dict.fromkeys(raw_candidates))
    if not candidates:
        raise ValueError("Au moins un facteur R candidat est requis pour l'analyse de stabilité.")
    missing = [column for column in candidates if column not in data.columns]
    if missing:
        raise ValueError(f"Colonnes candidates absentes: {', '.join(missing)}")
    forbidden = [
        column
        for column in candidates
        if column in {protected_attribute, decision_attribute}
    ]
    if forbidden:
        raise ValueError("Un facteur R ne peut pas être la décision ou l'attribut protégé.")
    if max_conditioning_factors < 1:
        raise ValueError("max_conditioning_factors doit être supérieur ou égal à 1.")
    if max_conditioning_factors > len(candidates):
        raise ValueError("max_conditioning_factors dépasse le nombre de facteurs candidats.")
    if not 0 <= materiality_threshold <= 1:
        raise ValueError("materiality_threshold doit être compris entre 0 et 1.")
    if not 0.5 <= consensus_threshold <= 1:
        raise ValueError("consensus_threshold doit être compris entre 0.5 et 1.")
    if not 0 < minimum_coverage <= 1:
        raise ValueError("minimum_coverage doit être strictement positif et inférieur ou égal à 1.")
    if not 0 < minimum_valid_share <= 1:
        raise ValueError("minimum_valid_share doit être strictement positif et inférieur ou égal à 1.")
    if max_specifications < 2:
        raise ValueError("max_specifications doit être supérieur ou égal à 2.")

    universe = _specifications(candidates, max_conditioning_factors)
    if len(universe) > max_specifications:
        raise ValueError(
            f"Le multivers contient {len(universe)} spécifications; la limite est {max_specifications}."
        )

    records: list[dict[str, Any]] = []
    by_specification: dict[tuple[str, ...], dict[str, Any]] = {}
    for index, specification in enumerate(universe):
        record: dict[str, Any] = {
            "specification_id": f"S{index:03d}",
            "conditioning_attributes": " + ".join(specification) or "(aucun)",
            "conditioning_count": len(specification),
            **{f"uses_{candidate}": candidate in specification for candidate in candidates},
        }
        try:
            result = calculate_cdd(
                data,
                protected_attribute,
                protected_value,
                decision_attribute,
                advantaged_value=favourable_value,
                conditioning_attributes=specification,
                min_outcome_count=min_outcome_count,
                materiality_threshold=materiality_threshold,
                bootstrap_iterations=0,
            )
            if result.gap is None:
                raise ValueError("aucune strate éligible")
            record.update(
                {
                    "gap": float(result.gap),
                    "coverage": float(result.coverage),
                    "eligible_strata": int(result.strata["eligible"].sum()),
                    "signal_class": _signal_class(float(result.gap), materiality_threshold),
                    "valid": True,
                    "error": None,
                }
            )
        except ValueError as exc:
            record.update(
                {
                    "gap": np.nan,
                    "coverage": 0.0,
                    "eligible_strata": 0,
                    "signal_class": "invalid",
                    "valid": False,
                    "error": str(exc),
                }
            )
        records.append(record)
        by_specification[specification] = record

    specifications = pd.DataFrame.from_records(records)
    valid = specifications[specifications["valid"]].copy()
    if valid.empty:
        raise ValueError("Aucune spécification CDD valide dans le multivers proposé.")
    valid = valid.sort_values(["gap", "specification_id"]).copy()
    valid["curve_rank"] = np.arange(1, len(valid) + 1)
    specifications = specifications.merge(
        valid[["specification_id", "curve_rank"]], on="specification_id", how="left"
    ).sort_values(["valid", "curve_rank", "specification_id"], ascending=[False, True, True])
    specifications = specifications.reset_index(drop=True)

    counts = Counter(valid["signal_class"])
    class_order = [ADVERSE_MATERIAL, REVERSE_MATERIAL, WITHIN_MATERIALITY]
    dominant_class = max(class_order, key=lambda name: (counts[name], -class_order.index(name)))
    dominant_share = counts[dominant_class] / len(valid)
    median_coverage = float(valid["coverage"].median())
    robustness_score = float(dominant_share * median_coverage)
    gaps = valid["gap"].astype(float)
    gap_min = float(gaps.min())
    gap_median = float(gaps.median())
    gap_max = float(gaps.max())
    range_crosses_zero = bool(gap_min < 0 < gap_max)
    valid_share = len(valid) / len(specifications)

    robust = (
        valid_share >= minimum_valid_share
        and dominant_share >= consensus_threshold
        and median_coverage >= minimum_coverage
    )
    labels = {
        ADVERSE_MATERIAL: "signal défavorable matériel",
        REVERSE_MATERIAL: "signal inverse matériel",
        WITHIN_MATERIALITY: "écart sous le seuil matériel",
    }
    if robust:
        status = f"conclusion robuste: {labels[dominant_class]}"
    else:
        status = "conclusion sensible aux choix de spécification"

    candidate_position = {name: position for position, name in enumerate(candidates)}
    effects: list[dict[str, Any]] = []
    for candidate in candidates:
        deltas: list[float] = []
        class_flips = 0
        for base in universe:
            if candidate in base or len(base) >= max_conditioning_factors:
                continue
            expanded = tuple(
                sorted((*base, candidate), key=lambda name: candidate_position[name])
            )
            before = by_specification[base]
            after = by_specification[expanded]
            if not before["valid"] or not after["valid"]:
                continue
            deltas.append(float(after["gap"] - before["gap"]))
            class_flips += before["signal_class"] != after["signal_class"]
        effects.append(
            {
                "factor": candidate,
                "paired_comparisons": len(deltas),
                "median_shift": float(np.median(deltas)) if deltas else np.nan,
                "median_absolute_shift": float(np.median(np.abs(deltas))) if deltas else np.nan,
                "maximum_absolute_shift": float(np.max(np.abs(deltas))) if deltas else np.nan,
                "class_flip_rate": class_flips / len(deltas) if deltas else np.nan,
            }
        )
    factor_effects = pd.DataFrame.from_records(effects).sort_values(
        ["median_absolute_shift", "factor"], ascending=[False, True], na_position="last"
    ).reset_index(drop=True)

    notes = (
        "Toutes les spécifications doivent être plausibles et justifiées avant lecture des résultats.",
        "Le score de robustesse est le consensus de classe multiplié par la couverture médiane.",
        "Un résultat robuste n'établit ni causalité, ni légalité, ni absence de biais de mesure.",
        "L'outil n'optimise jamais le choix des facteurs R en fonction du résultat souhaité.",
    )
    return StabilityResult(
        protected_attribute=protected_attribute,
        protected_value=protected_value,
        decision_attribute=decision_attribute,
        favourable_value=favourable_value,
        conditioning_candidates=tuple(candidates),
        max_conditioning_factors=max_conditioning_factors,
        materiality_threshold=materiality_threshold,
        consensus_threshold=consensus_threshold,
        minimum_coverage=minimum_coverage,
        minimum_valid_share=minimum_valid_share,
        specifications=specifications,
        factor_effects=factor_effects,
        total_specifications=len(specifications),
        valid_specifications=len(valid),
        valid_share=float(valid_share),
        dominant_class=dominant_class,
        dominant_share=float(dominant_share),
        robustness_score=robustness_score,
        median_coverage=median_coverage,
        gap_min=gap_min,
        gap_median=gap_median,
        gap_max=gap_max,
        range_crosses_zero=range_crosses_zero,
        status=status,
        notes=notes,
    )


fairness_stability = calculate_fairness_stability
