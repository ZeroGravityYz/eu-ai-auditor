"""Intersectional outcome-parity analysis with uncertainty and FDR control."""

from __future__ import annotations

from collections.abc import Sequence
from statistics import NormalDist
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

from .models import IntersectionalResult


def _wilson_interval(successes: int, total: int, confidence_level: float) -> tuple[float, float]:
    if total <= 0:
        return (np.nan, np.nan)
    z = NormalDist().inv_cdf(0.5 + confidence_level / 2)
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = (proportion + z**2 / (2 * total)) / denominator
    margin = z * np.sqrt(proportion * (1 - proportion) / total + z**2 / (4 * total**2))
    margin /= denominator
    return (max(0.0, float(centre - margin)), min(1.0, float(centre + margin)))


def _benjamini_hochberg(values: pd.Series) -> pd.Series:
    """Return monotone Benjamini-Hochberg adjusted p-values."""

    adjusted = pd.Series(np.nan, index=values.index, dtype=float)
    finite = values.dropna().astype(float).sort_values()
    count = len(finite)
    if not count:
        return adjusted
    raw = finite.to_numpy() * count / np.arange(1, count + 1)
    corrected = np.minimum.accumulate(raw[::-1])[::-1]
    adjusted.loc[finite.index] = np.clip(corrected, 0, 1)
    return adjusted


def calculate_intersectional_parity(
    data: pd.DataFrame,
    protected_attributes: str | Sequence[str],
    decision_attribute: str,
    favourable_value: Any,
    *,
    min_group_count: int = 30,
    materiality_threshold: float = 0.05,
    confidence_level: float = 0.95,
    fdr_alpha: float = 0.05,
) -> IntersectionalResult:
    """Audit all observed intersections without choosing a privileged reference group.

    Each observed group is compared with the rest of the complete-case population by a
    two-sided Fisher exact test. Benjamini-Hochberg adjusted p-values limit the false
    discovery rate across eligible groups. The test is exploratory and does not turn a
    statistical association into a legal or causal conclusion.
    """

    attributes = [protected_attributes] if isinstance(protected_attributes, str) else list(protected_attributes)
    attributes = list(dict.fromkeys(attributes))
    if not attributes:
        raise ValueError("Au moins un attribut protégé est requis.")
    missing = [column for column in [*attributes, decision_attribute] if column not in data.columns]
    if missing:
        raise ValueError(f"Colonnes absentes: {', '.join(missing)}")
    if min_group_count < 2:
        raise ValueError("min_group_count doit être supérieur ou égal à 2.")
    if not 0 <= materiality_threshold <= 1:
        raise ValueError("materiality_threshold doit être compris entre 0 et 1.")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level doit être strictement compris entre 0 et 1.")
    if not 0 < fdr_alpha < 1:
        raise ValueError("fdr_alpha doit être strictement compris entre 0 et 1.")
    if data.empty:
        raise ValueError("Le jeu de données est vide.")
    if favourable_value not in set(data[decision_attribute].dropna().unique()):
        raise ValueError(f"Issue favorable introuvable dans {decision_attribute}: {favourable_value!r}")

    analysis = data[[*attributes, decision_attribute]].dropna().copy()
    if analysis.empty:
        raise ValueError("Aucune ligne complète pour les colonnes sélectionnées.")
    if analysis[decision_attribute].nunique(dropna=True) < 2:
        raise ValueError("La variable de décision doit contenir au moins deux issues.")
    analysis["__favourable__"] = analysis[decision_attribute].eq(favourable_value)
    total_rows = len(analysis)
    total_favourable = int(analysis["__favourable__"].sum())
    overall_rate = total_favourable / total_rows
    grouper: str | list[str] = attributes[0] if len(attributes) == 1 else attributes

    rows: list[dict[str, Any]] = []
    for key, group in analysis.groupby(grouper, observed=True, dropna=False, sort=True):
        values = key if isinstance(key, tuple) else (key,)
        count = len(group)
        favourable = int(group["__favourable__"].sum())
        adverse = count - favourable
        rest_favourable = total_favourable - favourable
        rest_adverse = (total_rows - count) - rest_favourable
        rate = favourable / count
        eligible = count >= min_group_count and total_rows - count >= min_group_count
        ci_low, ci_high = _wilson_interval(favourable, count, confidence_level)
        odds_ratio = p_value = np.nan
        if eligible:
            odds_ratio, p_value = fisher_exact(
                [[favourable, adverse], [rest_favourable, rest_adverse]], alternative="two-sided"
            )
        record = dict(zip(attributes, values, strict=True))
        label = " × ".join(f"{column}={value}" for column, value in zip(attributes, values, strict=True))
        record.update(
            {
                "group": label,
                "n": count,
                "favourable_count": favourable,
                "favourable_rate": rate,
                "confidence_low": ci_low,
                "confidence_high": ci_high,
                "gap_vs_overall": rate - overall_rate,
                "rate_ratio_vs_overall": rate / overall_rate if overall_rate else np.nan,
                "odds_ratio_vs_rest": float(odds_ratio),
                "p_value": float(p_value),
                "eligible": bool(eligible),
            }
        )
        rows.append(record)

    groups = pd.DataFrame.from_records(rows)
    if len(groups) < 2:
        raise ValueError("L'analyse intersectionnelle requiert au moins deux groupes observés.")
    groups["q_value"] = _benjamini_hochberg(groups["p_value"])
    groups["material_gap"] = groups["gap_vs_overall"].abs() >= materiality_threshold
    groups["statistically_flagged"] = groups["q_value"].le(fdr_alpha).fillna(False)
    groups["review_priority"] = groups["eligible"] & groups["material_gap"] & groups["statistically_flagged"]
    groups = groups.sort_values(
        ["review_priority", "gap_vs_overall", "n"], ascending=[False, True, False]
    ).reset_index(drop=True)

    eligible = groups[groups["eligible"]]
    if eligible.empty:
        worst_case_gap = None
        lowest = highest = None
    else:
        lowest_row = eligible.loc[eligible["favourable_rate"].idxmin()]
        highest_row = eligible.loc[eligible["favourable_rate"].idxmax()]
        worst_case_gap = float(highest_row["favourable_rate"] - lowest_row["favourable_rate"])
        lowest = str(lowest_row["group"])
        highest = str(highest_row["group"])

    included_rows = int(eligible["n"].sum())
    excluded_rows = len(data) - included_rows
    flagged_groups = int(groups["review_priority"].sum())
    if eligible.empty:
        status = "données insuffisantes pour les intersections"
    elif flagged_groups:
        status = f"{flagged_groups} intersection(s) prioritaire(s) après correction FDR"
    else:
        status = "aucune intersection prioritaire selon les seuils choisis"

    notes = [
        "Les groupes sont comparés au reste de la population, sans désigner un groupe privilégié.",
        "Les intervalles de taux utilisent la méthode de Wilson.",
        "Les q-values appliquent Benjamini-Hochberg aux groupes éligibles.",
        "Les seuils statistiques et matériels sont des paramètres de triage, pas des seuils juridiques.",
    ]
    incomplete = len(data) - len(analysis)
    if incomplete:
        notes.append(f"{incomplete} ligne(s) exclue(s) pour valeurs manquantes.")
    sparse = int((~groups["eligible"]).sum())
    if sparse:
        notes.append(f"{sparse} intersection(s) conservée(s) à titre descriptif mais non testée(s).")

    return IntersectionalResult(
        protected_attributes=tuple(attributes),
        decision_attribute=decision_attribute,
        favourable_value=favourable_value,
        overall_favourable_rate=float(overall_rate),
        materiality_threshold=materiality_threshold,
        confidence_level=confidence_level,
        fdr_alpha=fdr_alpha,
        groups=groups,
        eligible_groups=len(eligible),
        flagged_groups=flagged_groups,
        coverage=included_rows / len(data),
        included_rows=included_rows,
        excluded_rows=excluded_rows,
        worst_case_gap=worst_case_gap,
        lowest_rate_group=lowest,
        highest_rate_group=highest,
        status=status,
        notes=tuple(notes),
    )


intersectional_parity = calculate_intersectional_parity
