"""Conditional Demographic Disparity (CDD) descriptive statistics.

The implementation follows the presentation by Wachter, Mittelstadt and
Russell: within each legitimate stratum R, compare the share of a protected
class in the disadvantaged outcome group (D_R) with its share in the
advantaged outcome group (A_R). The result is evidence for review, not a
legal pass/fail determination.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from .models import CDDResult


def _require_columns(data: pd.DataFrame, columns: Sequence[str]) -> None:
    missing = [column for column in columns if column not in data.columns]
    if missing:
        raise ValueError(f"Colonnes absentes: {', '.join(missing)}")


def _condition_frame(
    data: pd.DataFrame,
    conditioning: Sequence[str],
    *,
    numeric_bins: int,
    max_numeric_categories: int,
) -> tuple[pd.DataFrame, list[str]]:
    conditioned = pd.DataFrame(index=data.index)
    notes: list[str] = []
    for column in conditioning:
        values = data[column]
        if pd.api.types.is_numeric_dtype(values) and values.nunique(dropna=True) > max_numeric_categories:
            try:
                binned = pd.qcut(values, q=numeric_bins, duplicates="drop")
                conditioned[column] = binned.astype("string")
                notes.append(
                    f"{column}: valeurs numériques regroupées en {binned.nunique(dropna=True)} quantiles."
                )
            except (ValueError, TypeError):
                conditioned[column] = values.astype("string")
        else:
            conditioned[column] = values.astype("string")
    if not conditioning:
        conditioned["__population__"] = "Population totale"
    return conditioned, notes


def calculate_cdd(
    data: pd.DataFrame,
    protected_attribute: str,
    protected_value: Any,
    decision_attribute: str,
    advantaged_value: Any,
    conditioning_attributes: str | Sequence[str] | None = None,
    *,
    min_outcome_count: int = 5,
    numeric_bins: int = 5,
    max_numeric_categories: int = 10,
    materiality_threshold: float = 0.0,
    bootstrap_iterations: int = 0,
    confidence_level: float = 0.95,
    random_state: int = 42,
) -> CDDResult:
    """Calculate conditional demographic disparity summary statistics.

    ``A_R = P(S=protected | Y=advantaged, R)`` and
    ``D_R = P(S=protected | Y=disadvantaged, R)``.

    The aggregate summary weights every stratum by its population, as in the
    descriptive weighted approach discussed by Wachter et al. Strata with too
    few advantaged or disadvantaged observations are reported but excluded
    from the aggregate to avoid unstable ratios.
    """

    if isinstance(conditioning_attributes, str):
        conditioning = [conditioning_attributes]
    else:
        conditioning = list(conditioning_attributes or [])
    if min_outcome_count < 1:
        raise ValueError("min_outcome_count doit être supérieur ou égal à 1.")
    if numeric_bins < 2:
        raise ValueError("numeric_bins doit être supérieur ou égal à 2.")
    if not 0 <= materiality_threshold <= 1:
        raise ValueError("materiality_threshold doit être compris entre 0 et 1.")
    if bootstrap_iterations < 0:
        raise ValueError("bootstrap_iterations doit être supérieur ou égal à 0.")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level doit être strictement compris entre 0 et 1.")

    required = [protected_attribute, decision_attribute, *conditioning]
    _require_columns(data, required)
    if protected_value not in set(data[protected_attribute].dropna().unique()):
        raise ValueError(f"Valeur protégée introuvable dans {protected_attribute}: {protected_value!r}")
    if advantaged_value not in set(data[decision_attribute].dropna().unique()):
        raise ValueError(f"Issue favorable introuvable dans {decision_attribute}: {advantaged_value!r}")

    analysis = data[required].dropna().copy()
    if analysis.empty:
        raise ValueError("Aucune ligne complète pour les colonnes sélectionnées.")
    if analysis[decision_attribute].nunique() < 2:
        raise ValueError("La variable de décision doit contenir au moins deux issues.")

    condition_frame, binning_notes = _condition_frame(
        analysis,
        conditioning,
        numeric_bins=numeric_bins,
        max_numeric_categories=max_numeric_categories,
    )
    internal = condition_frame.copy()
    internal["__protected__"] = analysis[protected_attribute].eq(protected_value).astype(int)
    internal["__advantaged__"] = analysis[decision_attribute].eq(advantaged_value)

    group_columns = list(condition_frame.columns)
    records: list[dict[str, Any]] = []
    grouper: str | list[str] = group_columns[0] if len(group_columns) == 1 else group_columns
    for key, group in internal.groupby(grouper, dropna=False, observed=True, sort=True):
        keys = key if isinstance(key, tuple) else (key,)
        advantaged = group[group["__advantaged__"]]
        disadvantaged = group[~group["__advantaged__"]]
        n_advantaged = len(advantaged)
        n_disadvantaged = len(disadvantaged)
        a_r = float(advantaged["__protected__"].mean()) if n_advantaged else np.nan
        d_r = float(disadvantaged["__protected__"].mean()) if n_disadvantaged else np.nan
        eligible = n_advantaged >= min_outcome_count and n_disadvantaged >= min_outcome_count
        record: dict[str, Any] = dict(zip(group_columns, keys, strict=True))
        record.update(
            {
                "n_total": len(group),
                "n_advantaged": n_advantaged,
                "n_disadvantaged": n_disadvantaged,
                "protected_advantaged": int(advantaged["__protected__"].sum()),
                "protected_disadvantaged": int(disadvantaged["__protected__"].sum()),
                "A_R": a_r,
                "D_R": d_r,
                "gap_D_minus_A": d_r - a_r if n_advantaged and n_disadvantaged else np.nan,
                "eligible": eligible,
            }
        )
        records.append(record)

    strata = pd.DataFrame.from_records(records)
    eligible_strata = strata[strata["eligible"]].copy()
    if eligible_strata.empty:
        included_rows = 0
        a_summary = d_summary = gap = None
        directional_signal = material_signal = False
        status = "données insuffisantes"
    else:
        included_rows = int(eligible_strata["n_total"].sum())
        weights = eligible_strata["n_total"] / included_rows
        strata["weight"] = 0.0
        strata.loc[eligible_strata.index, "weight"] = weights
        a_summary = float(np.average(eligible_strata["A_R"], weights=eligible_strata["n_total"]))
        d_summary = float(np.average(eligible_strata["D_R"], weights=eligible_strata["n_total"]))
        gap = d_summary - a_summary
        directional_signal = bool(gap > 0)
        material_signal = bool(gap > materiality_threshold)
        status = "signal à examiner" if material_signal else "aucun signal matériel selon le seuil choisi"

    excluded_rows = len(data) - included_rows
    coverage = included_rows / len(data) if len(data) else 0.0
    notes = list(binning_notes)
    missing_rows = len(data) - len(analysis)
    if missing_rows:
        notes.append(f"{missing_rows} lignes exclues pour valeurs manquantes.")
    sparse_count = int((~strata["eligible"]).sum())
    if sparse_count:
        notes.append(
            f"{sparse_count} strate(s) exclue(s) de l'agrégat: moins de {min_outcome_count} "
            "observations dans une issue."
        )
    notes.append("Le seuil de matérialité est un paramètre d'audit, pas un seuil juridique.")

    confidence_low = confidence_high = None
    bootstrap_valid_iterations = 0
    if bootstrap_iterations and gap is not None:
        rng = np.random.default_rng(random_state)
        bootstrap_gaps: list[float] = []
        for _ in range(bootstrap_iterations):
            positions = rng.integers(0, len(data), size=len(data))
            sample = data.iloc[positions].reset_index(drop=True)
            try:
                sampled = calculate_cdd(
                    sample,
                    protected_attribute=protected_attribute,
                    protected_value=protected_value,
                    decision_attribute=decision_attribute,
                    advantaged_value=advantaged_value,
                    conditioning_attributes=conditioning,
                    min_outcome_count=min_outcome_count,
                    numeric_bins=numeric_bins,
                    max_numeric_categories=max_numeric_categories,
                    materiality_threshold=materiality_threshold,
                    bootstrap_iterations=0,
                    confidence_level=confidence_level,
                    random_state=random_state,
                )
            except ValueError:
                continue
            if sampled.gap is not None and np.isfinite(sampled.gap):
                bootstrap_gaps.append(sampled.gap)
        bootstrap_valid_iterations = len(bootstrap_gaps)
        minimum_valid = max(30, int(bootstrap_iterations * 0.8))
        if bootstrap_valid_iterations >= minimum_valid:
            alpha = (1 - confidence_level) / 2
            confidence_low, confidence_high = (
                float(value)
                for value in np.quantile(bootstrap_gaps, [alpha, 1 - alpha])
            )
            notes.append(
                f"Intervalle bootstrap à {confidence_level:.0%}: "
                f"[{confidence_low:.3f}, {confidence_high:.3f}] "
                f"({bootstrap_valid_iterations}/{bootstrap_iterations} réplications valides)."
            )
            if confidence_low > materiality_threshold:
                notes.append("Le signal dépasse le seuil sur l'ensemble de l'intervalle bootstrap.")
            elif confidence_high <= materiality_threshold:
                notes.append("L'intervalle bootstrap reste sous le seuil de matérialité choisi.")
            else:
                notes.append("L'intervalle bootstrap recoupe le seuil: l'interprétation reste incertaine.")
        else:
            notes.append(
                f"Intervalle non calculé: seulement {bootstrap_valid_iterations}/{bootstrap_iterations} "
                "réplications bootstrap valides."
            )

    if "weight" not in strata:
        strata["weight"] = 0.0
    display_columns = [
        *group_columns,
        "n_total",
        "n_advantaged",
        "n_disadvantaged",
        "protected_advantaged",
        "protected_disadvantaged",
        "A_R",
        "D_R",
        "gap_D_minus_A",
        "weight",
        "eligible",
    ]
    return CDDResult(
        protected_attribute=protected_attribute,
        protected_value=protected_value,
        decision_attribute=decision_attribute,
        advantaged_value=advantaged_value,
        conditioning_attributes=tuple(conditioning),
        advantaged_share=a_summary,
        disadvantaged_share=d_summary,
        gap=gap,
        directional_signal=directional_signal,
        material_signal=material_signal,
        materiality_threshold=materiality_threshold,
        confidence_level=confidence_level if bootstrap_iterations else None,
        confidence_low=confidence_low,
        confidence_high=confidence_high,
        bootstrap_iterations=bootstrap_iterations,
        bootstrap_valid_iterations=bootstrap_valid_iterations,
        coverage=coverage,
        included_rows=included_rows,
        excluded_rows=excluded_rows,
        status=status,
        strata=strata[display_columns],
        notes=tuple(notes),
    )


# A concise alias for package users.
cdd = calculate_cdd
