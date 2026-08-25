"""OversightParity: fairness of AI-assisted human decision processes.

The engine follows the full decision chain instead of treating the model output
as the final outcome. It compares AI recommendations, human decisions, error
correction, appeals and remedies between a protected and a reference group.

An exposure effect is labelled causal only when the caller explicitly declares
that access to the AI recommendation was randomized. Otherwise it is reported
as a conditional association.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from .models import OversightResult

METRIC_LABELS = {
    "ai_favourable_rate": "Décisions favorables recommandées par l'IA",
    "human_favourable_rate": "Décisions humaines favorables",
    "final_favourable_rate": "Décisions finales favorables",
    "agreement_rate": "Concordance humain-IA",
    "override_rate": "Modification de la recommandation IA",
    "helpful_override_rate": "Correction utile d'une erreur IA",
    "harmful_override_rate": "Erreur introduite par l'intervention humaine",
    "appeal_access_rate": "Accès au recours après décision défavorable",
    "remedy_rate": "Correction après décision défavorable",
    "timely_remedy_rate": "Correction dans le délai cible",
}


def _require_columns(data: pd.DataFrame, columns: Sequence[str | None]) -> None:
    required = [column for column in columns if column]
    missing = [column for column in required if column not in data.columns]
    if missing:
        raise ValueError(f"Colonnes absentes: {', '.join(missing)}")


def _require_value(series: pd.Series, value: Any, label: str) -> None:
    if value not in set(series.dropna().unique()):
        raise ValueError(f"{label} introuvable dans {series.name}: {value!r}")


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
            except (TypeError, ValueError):
                conditioned[column] = values.astype("string")
        else:
            conditioned[column] = values.astype("string")
    if not conditioning:
        conditioned["__population__"] = "Population totale"
    return conditioned, notes


def _safe_rate(numerator: pd.Series, denominator: pd.Series) -> float | None:
    selected = numerator[denominator]
    return float(selected.mean()) if len(selected) else None


def _standardized_comparison(
    internal: pd.DataFrame,
    *,
    outcome: str,
    denominator: str,
    strata: Sequence[str],
    min_group_count: int,
) -> dict[str, float | int | None]:
    eligible_rows = internal[internal[denominator] & internal[outcome].notna()].copy()
    total_denominator = len(eligible_rows)
    if total_denominator == 0:
        return {
            "protected_rate": None,
            "reference_rate": None,
            "gap": None,
            "coverage": 0.0,
            "eligible_strata": 0,
        }

    records: list[dict[str, float | int]] = []
    grouper: str | list[str] = strata[0] if len(strata) == 1 else list(strata)
    for _, frame in eligible_rows.groupby(grouper, dropna=False, observed=True, sort=False):
        protected = frame[frame["__group__"] == "protected"]
        reference = frame[frame["__group__"] == "reference"]
        if len(protected) < min_group_count or len(reference) < min_group_count:
            continue
        records.append(
            {
                "n": len(protected) + len(reference),
                "protected_rate": float(protected[outcome].mean()),
                "reference_rate": float(reference[outcome].mean()),
            }
        )
    if not records:
        return {
            "protected_rate": None,
            "reference_rate": None,
            "gap": None,
            "coverage": 0.0,
            "eligible_strata": 0,
        }
    frame = pd.DataFrame(records)
    included = int(frame["n"].sum())
    weights = frame["n"] / included
    protected_rate = float(np.average(frame["protected_rate"], weights=weights))
    reference_rate = float(np.average(frame["reference_rate"], weights=weights))
    return {
        "protected_rate": protected_rate,
        "reference_rate": reference_rate,
        "gap": protected_rate - reference_rate,
        "coverage": included / total_denominator,
        "eligible_strata": len(frame),
    }


def _exposure_effect(
    internal: pd.DataFrame,
    *,
    strata: Sequence[str],
    min_group_count: int,
) -> dict[str, float | int | None]:
    eligible_rows = internal[
        internal["__exposed__"].notna() & internal["__human_positive__"].notna()
    ]
    total = len(eligible_rows)
    if total == 0:
        return {
            "protected": None,
            "reference": None,
            "gap": None,
            "coverage": 0.0,
            "eligible_strata": 0,
        }

    records: list[dict[str, float | int]] = []
    grouper: str | list[str] = strata[0] if len(strata) == 1 else list(strata)
    for _, frame in eligible_rows.groupby(grouper, dropna=False, observed=True, sort=False):
        cells: dict[tuple[str, bool], pd.DataFrame] = {}
        valid = True
        for role in ("protected", "reference"):
            for exposed in (False, True):
                cell = frame[
                    (frame["__group__"] == role) & (frame["__exposed__"] == exposed)
                ]
                cells[(role, exposed)] = cell
                if len(cell) < min_group_count:
                    valid = False
        if not valid:
            continue
        records.append(
            {
                "n": sum(len(cell) for cell in cells.values()),
                "protected_unexposed": float(cells[("protected", False)]["__human_positive__"].mean()),
                "protected_exposed": float(cells[("protected", True)]["__human_positive__"].mean()),
                "reference_unexposed": float(cells[("reference", False)]["__human_positive__"].mean()),
                "reference_exposed": float(cells[("reference", True)]["__human_positive__"].mean()),
            }
        )
    if not records:
        return {
            "protected": None,
            "reference": None,
            "gap": None,
            "coverage": 0.0,
            "eligible_strata": 0,
        }
    frame = pd.DataFrame(records)
    included = int(frame["n"].sum())
    weights = frame["n"] / included
    protected_effect = float(
        np.average(frame["protected_exposed"] - frame["protected_unexposed"], weights=weights)
    )
    reference_effect = float(
        np.average(frame["reference_exposed"] - frame["reference_unexposed"], weights=weights)
    )
    return {
        "protected": protected_effect,
        "reference": reference_effect,
        "gap": protected_effect - reference_effect,
        "coverage": included / total,
        "eligible_strata": len(frame),
    }


def _group_summary(internal: pd.DataFrame, protected_value: Any, reference_value: Any) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for role, value in (("protected", protected_value), ("reference", reference_value)):
        group = internal[internal["__group__"] == role]
        adverse = ~group["__human_positive__"]
        ai_incorrect = group.get("__ai_correct__", pd.Series(False, index=group.index)).eq(False)
        ai_correct = group.get("__ai_correct__", pd.Series(False, index=group.index)).eq(True)
        rows.append(
            {
                "group_role": role,
                "group_value": value,
                "rows": len(group),
                "ai_favourable_rate": _safe_rate(group["__ai_positive__"], pd.Series(True, index=group.index)),
                "human_favourable_rate": _safe_rate(
                    group["__human_positive__"], pd.Series(True, index=group.index)
                ),
                "final_favourable_rate": _safe_rate(
                    group["__final_positive__"], group["__final_positive__"].notna()
                ),
                "agreement_rate": _safe_rate(group["__agreement__"], pd.Series(True, index=group.index)),
                "helpful_override_rate": (
                    _safe_rate(group["__human_correct__"], ai_incorrect)
                    if "__human_correct__" in group
                    else None
                ),
                "harmful_override_rate": (
                    _safe_rate(~group["__human_correct__"], ai_correct)
                    if "__human_correct__" in group
                    else None
                ),
                "appeal_access_rate": (
                    _safe_rate(group["__appealed__"], adverse)
                    if "__appealed__" in group
                    else None
                ),
                "remedy_rate": (
                    _safe_rate(group["__final_positive__"], adverse)
                    if "__remedy_available__" in group
                    else None
                ),
                "timely_remedy_rate": (
                    _safe_rate(group["__timely_remedy__"], adverse)
                    if "__timely_remedy__" in group
                    else None
                ),
            }
        )
    return pd.DataFrame(rows)


def _comparison_specs(internal: pd.DataFrame) -> list[tuple[str, str, str]]:
    specs = [
        ("ai_favourable_rate", "__ai_positive__", "__all__"),
        ("human_favourable_rate", "__human_positive__", "__all__"),
        ("final_favourable_rate", "__final_positive__", "__final_available__"),
        ("agreement_rate", "__agreement__", "__all__"),
        ("override_rate", "__override__", "__all__"),
    ]
    if "__ai_correct__" in internal:
        specs.extend(
            [
                ("helpful_override_rate", "__human_correct__", "__ai_incorrect__"),
                ("harmful_override_rate", "__human_incorrect__", "__ai_correct__"),
            ]
        )
    if "__appealed__" in internal:
        specs.append(("appeal_access_rate", "__appealed__", "__human_adverse__"))
    if "__remedy_available__" in internal:
        specs.append(("remedy_rate", "__final_positive__", "__human_adverse__"))
    if "__timely_remedy__" in internal:
        specs.append(("timely_remedy_rate", "__timely_remedy__", "__human_adverse__"))
    return specs


def calculate_oversight_parity(
    data: pd.DataFrame,
    protected_attribute: str,
    protected_value: Any,
    ai_recommendation_attribute: str,
    human_decision_attribute: str,
    favourable_value: Any,
    *,
    reference_value: Any | None = None,
    conditioning_attributes: str | Sequence[str] | None = None,
    ground_truth_attribute: str | None = None,
    ground_truth_favourable_value: Any | None = None,
    exposure_attribute: str | None = None,
    exposed_value: Any = True,
    unexposed_value: Any = False,
    exposure_randomized: bool = False,
    appeal_attribute: str | None = None,
    appeal_value: Any = True,
    final_decision_attribute: str | None = None,
    decision_timestamp_attribute: str | None = None,
    final_timestamp_attribute: str | None = None,
    remedy_sla_days: float = 30.0,
    bootstrap_cluster_attribute: str | None = None,
    min_group_count: int = 5,
    numeric_bins: int = 5,
    max_numeric_categories: int = 10,
    materiality_threshold: float = 0.05,
    bootstrap_iterations: int = 0,
    confidence_level: float = 0.95,
    random_state: int = 42,
) -> OversightResult:
    """Audit fairness across AI recommendation, human decision and remedy stages.

    Rates are standardized over the pooled distribution of the legitimate
    conditioning strata. Sparse strata are excluded. The exposure contrast is
    a causal estimate only if ``exposure_randomized=True`` is substantively
    justified by the study design.
    """

    if isinstance(conditioning_attributes, str):
        conditioning = [conditioning_attributes]
    else:
        conditioning = list(conditioning_attributes or [])
    if min_group_count < 1:
        raise ValueError("min_group_count doit être supérieur ou égal à 1.")
    if numeric_bins < 2:
        raise ValueError("numeric_bins doit être supérieur ou égal à 2.")
    if not 0 <= materiality_threshold <= 1:
        raise ValueError("materiality_threshold doit être compris entre 0 et 1.")
    if bootstrap_iterations < 0:
        raise ValueError("bootstrap_iterations doit être supérieur ou égal à 0.")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level doit être strictement compris entre 0 et 1.")
    if remedy_sla_days <= 0:
        raise ValueError("remedy_sla_days doit être strictement positif.")

    _require_columns(
        data,
        [
            protected_attribute,
            ai_recommendation_attribute,
            human_decision_attribute,
            *conditioning,
            ground_truth_attribute,
            exposure_attribute,
            appeal_attribute,
            final_decision_attribute,
            decision_timestamp_attribute,
            final_timestamp_attribute,
            bootstrap_cluster_attribute,
        ],
    )
    _require_value(data[protected_attribute], protected_value, "Valeur protégée")
    available_groups = list(data[protected_attribute].dropna().unique())
    if reference_value is None:
        others = [value for value in available_groups if value != protected_value]
        if len(others) != 1:
            raise ValueError("reference_value est requis lorsque l'attribut protégé a plus de deux groupes.")
        reference_value = others[0]
    _require_value(data[protected_attribute], reference_value, "Valeur de référence")
    if reference_value == protected_value:
        raise ValueError("Les valeurs protégée et de référence doivent être différentes.")
    _require_value(data[ai_recommendation_attribute], favourable_value, "Issue favorable IA")
    _require_value(data[human_decision_attribute], favourable_value, "Issue favorable humaine")
    if ground_truth_attribute:
        ground_truth_favourable_value = (
            favourable_value if ground_truth_favourable_value is None else ground_truth_favourable_value
        )
        _require_value(
            data[ground_truth_attribute], ground_truth_favourable_value, "Issue favorable de vérité terrain"
        )
    if exposure_attribute:
        _require_value(data[exposure_attribute], exposed_value, "Valeur exposée")
        _require_value(data[exposure_attribute], unexposed_value, "Valeur non exposée")
    if appeal_attribute:
        _require_value(data[appeal_attribute], appeal_value, "Valeur de recours")
    if bool(decision_timestamp_attribute) != bool(final_timestamp_attribute):
        raise ValueError("Les deux colonnes temporelles doivent être fournies ensemble.")
    if decision_timestamp_attribute and not final_decision_attribute:
        raise ValueError("Une décision finale est requise pour mesurer le délai de correction.")
    if bootstrap_cluster_attribute and data[bootstrap_cluster_attribute].isna().any():
        raise ValueError("La colonne de cluster bootstrap ne doit pas contenir de valeur manquante.")

    required_complete = [
        protected_attribute,
        ai_recommendation_attribute,
        human_decision_attribute,
        *conditioning,
    ]
    analysis = data[data[protected_attribute].isin([protected_value, reference_value])].copy()
    analysis = analysis.dropna(subset=required_complete)
    if analysis.empty:
        raise ValueError("Aucune ligne complète pour les groupes et colonnes sélectionnés.")

    conditioned, notes = _condition_frame(
        analysis,
        conditioning,
        numeric_bins=numeric_bins,
        max_numeric_categories=max_numeric_categories,
    )
    internal = conditioned.copy()
    internal["__group__"] = np.where(
        analysis[protected_attribute].eq(protected_value), "protected", "reference"
    )
    internal["__ai_positive__"] = analysis[ai_recommendation_attribute].eq(favourable_value)
    internal["__human_positive__"] = analysis[human_decision_attribute].eq(favourable_value)
    internal["__agreement__"] = internal["__ai_positive__"].eq(internal["__human_positive__"])
    internal["__override__"] = ~internal["__agreement__"]
    internal["__all__"] = True
    internal["__human_adverse__"] = ~internal["__human_positive__"]

    if ground_truth_attribute:
        truth_available = analysis[ground_truth_attribute].notna()
        truth_positive = analysis[ground_truth_attribute].eq(ground_truth_favourable_value)
        internal["__ai_correct__"] = internal["__ai_positive__"].eq(truth_positive).where(truth_available)
        internal["__human_correct__"] = internal["__human_positive__"].eq(truth_positive).where(truth_available)
        internal["__ai_incorrect__"] = internal["__ai_correct__"].eq(False)
        internal["__human_incorrect__"] = internal["__human_correct__"].eq(False)

    if appeal_attribute:
        internal["__appealed__"] = analysis[appeal_attribute].eq(appeal_value).where(
            analysis[appeal_attribute].notna()
        )

    if final_decision_attribute:
        final_available = analysis[final_decision_attribute].notna()
        final_positive = analysis[final_decision_attribute].eq(favourable_value).where(final_available)
        internal["__final_positive__"] = final_positive.where(
            final_available, internal["__human_positive__"]
        )
        internal["__remedy_available__"] = True
    else:
        internal["__final_positive__"] = internal["__human_positive__"]
    internal["__final_available__"] = internal["__final_positive__"].notna()

    if decision_timestamp_attribute and final_timestamp_attribute:
        started = pd.to_datetime(analysis[decision_timestamp_attribute], errors="coerce", utc=True)
        finished = pd.to_datetime(analysis[final_timestamp_attribute], errors="coerce", utc=True)
        delay_days = (finished - started).dt.total_seconds() / 86400
        internal["__timely_remedy__"] = (
            internal["__final_positive__"] & delay_days.le(remedy_sla_days)
        ).where(started.notna() & finished.notna(), False)

    if exposure_attribute:
        internal["__exposed__"] = np.where(
            analysis[exposure_attribute].eq(exposed_value),
            True,
            np.where(analysis[exposure_attribute].eq(unexposed_value), False, np.nan),
        )

    strata = list(conditioned.columns)
    comparison_rows: list[dict[str, Any]] = []
    comparison_lookup: dict[str, dict[str, float | int | None]] = {}
    for metric, outcome, denominator in _comparison_specs(internal):
        comparison = _standardized_comparison(
            internal,
            outcome=outcome,
            denominator=denominator,
            strata=strata,
            min_group_count=min_group_count,
        )
        comparison_lookup[metric] = comparison
        comparison_rows.append(
            {
                "metric": metric,
                "label": METRIC_LABELS[metric],
                **comparison,
            }
        )

    ai_gap = comparison_lookup["ai_favourable_rate"]["gap"]
    human_gap = comparison_lookup["human_favourable_rate"]["gap"]
    fairness_transfer = (
        float(human_gap) - float(ai_gap) if human_gap is not None and ai_gap is not None else None
    )
    disparity_amplification = (
        abs(float(human_gap)) - abs(float(ai_gap))
        if human_gap is not None and ai_gap is not None
        else None
    )
    exposure = (
        _exposure_effect(internal, strata=strata, min_group_count=min_group_count)
        if exposure_attribute
        else {"protected": None, "reference": None, "gap": None, "coverage": 0.0, "eligible_strata": 0}
    )

    metrics: dict[str, float | None] = {
        "ai_gap": float(ai_gap) if ai_gap is not None else None,
        "human_gap": float(human_gap) if human_gap is not None else None,
        "final_gap": (
            float(comparison_lookup["final_favourable_rate"]["gap"])
            if comparison_lookup["final_favourable_rate"]["gap"] is not None
            else None
        ),
        "fairness_transfer_signed": fairness_transfer,
        "disparity_amplification": disparity_amplification,
        "agreement_gap": (
            float(comparison_lookup["agreement_rate"]["gap"])
            if comparison_lookup["agreement_rate"]["gap"] is not None
            else None
        ),
        "helpful_override_gap": (
            float(comparison_lookup.get("helpful_override_rate", {}).get("gap"))
            if comparison_lookup.get("helpful_override_rate", {}).get("gap") is not None
            else None
        ),
        "harmful_override_gap": (
            float(comparison_lookup.get("harmful_override_rate", {}).get("gap"))
            if comparison_lookup.get("harmful_override_rate", {}).get("gap") is not None
            else None
        ),
        "appeal_access_gap": (
            float(comparison_lookup.get("appeal_access_rate", {}).get("gap"))
            if comparison_lookup.get("appeal_access_rate", {}).get("gap") is not None
            else None
        ),
        "remedy_gap": (
            float(comparison_lookup.get("remedy_rate", {}).get("gap"))
            if comparison_lookup.get("remedy_rate", {}).get("gap") is not None
            else None
        ),
        "timely_remedy_gap": (
            float(comparison_lookup.get("timely_remedy_rate", {}).get("gap"))
            if comparison_lookup.get("timely_remedy_rate", {}).get("gap") is not None
            else None
        ),
        "automation_effect_protected": (
            float(exposure["protected"]) if exposure["protected"] is not None else None
        ),
        "automation_effect_reference": (
            float(exposure["reference"]) if exposure["reference"] is not None else None
        ),
        "automation_bias_gap": float(exposure["gap"]) if exposure["gap"] is not None else None,
    }

    intervals: dict[str, tuple[float, float] | None] = {key: None for key in metrics}
    bootstrap_valid_iterations = 0
    if bootstrap_iterations:
        rng = np.random.default_rng(random_state)
        samples: dict[str, list[float]] = {key: [] for key in metrics}
        valid_runs = 0
        cluster_codes: np.ndarray | None = None
        cluster_count = 0
        if bootstrap_cluster_attribute:
            cluster_codes, unique_clusters = pd.factorize(
                data[bootstrap_cluster_attribute], sort=False
            )
            cluster_count = len(unique_clusters)
        for _ in range(bootstrap_iterations):
            if cluster_codes is not None:
                sampled_codes = rng.integers(0, cluster_count, size=cluster_count)
                multiplicities = np.bincount(sampled_codes, minlength=cluster_count)
                positions = np.repeat(np.arange(len(data)), multiplicities[cluster_codes])
                sample = data.iloc[positions].reset_index(drop=True)
            else:
                positions = rng.integers(0, len(data), size=len(data))
                sample = data.iloc[positions].reset_index(drop=True)
            try:
                result = calculate_oversight_parity(
                    sample,
                    protected_attribute=protected_attribute,
                    protected_value=protected_value,
                    reference_value=reference_value,
                    ai_recommendation_attribute=ai_recommendation_attribute,
                    human_decision_attribute=human_decision_attribute,
                    favourable_value=favourable_value,
                    conditioning_attributes=conditioning,
                    ground_truth_attribute=ground_truth_attribute,
                    ground_truth_favourable_value=ground_truth_favourable_value,
                    exposure_attribute=exposure_attribute,
                    exposed_value=exposed_value,
                    unexposed_value=unexposed_value,
                    exposure_randomized=exposure_randomized,
                    appeal_attribute=appeal_attribute,
                    appeal_value=appeal_value,
                    final_decision_attribute=final_decision_attribute,
                    decision_timestamp_attribute=decision_timestamp_attribute,
                    final_timestamp_attribute=final_timestamp_attribute,
                    remedy_sla_days=remedy_sla_days,
                    bootstrap_cluster_attribute=bootstrap_cluster_attribute,
                    min_group_count=min_group_count,
                    numeric_bins=numeric_bins,
                    max_numeric_categories=max_numeric_categories,
                    materiality_threshold=materiality_threshold,
                    bootstrap_iterations=0,
                    confidence_level=confidence_level,
                    random_state=random_state,
                )
            except ValueError:
                continue
            valid_runs += 1
            for key, value in result.metrics.items():
                if value is not None and np.isfinite(value):
                    samples[key].append(float(value))
        bootstrap_valid_iterations = valid_runs
        minimum_valid = max(30, int(bootstrap_iterations * 0.8))
        alpha = (1 - confidence_level) / 2
        for key, values in samples.items():
            if len(values) >= minimum_valid:
                low, high = np.quantile(values, [alpha, 1 - alpha])
                intervals[key] = (float(low), float(high))
        if valid_runs < minimum_valid:
            notes.append(
                f"Intervalles fragiles: {valid_runs}/{bootstrap_iterations} réplications complètes valides."
            )

    comparisons = pd.DataFrame(comparison_rows)
    interval_keys = {
        "ai_favourable_rate": "ai_gap",
        "human_favourable_rate": "human_gap",
        "final_favourable_rate": "final_gap",
        "agreement_rate": "agreement_gap",
        "helpful_override_rate": "helpful_override_gap",
        "harmful_override_rate": "harmful_override_gap",
        "appeal_access_rate": "appeal_access_gap",
        "remedy_rate": "remedy_gap",
        "timely_remedy_rate": "timely_remedy_gap",
    }
    comparisons["gap_ci_low"] = comparisons["metric"].map(
        lambda metric: (intervals.get(interval_keys.get(metric, "")) or (None, None))[0]
    )
    comparisons["gap_ci_high"] = comparisons["metric"].map(
        lambda metric: (intervals.get(interval_keys.get(metric, "")) or (None, None))[1]
    )
    group_metrics = _group_summary(internal, protected_value, reference_value)

    included_rows = len(analysis)
    coverage = included_rows / len(data) if len(data) else 0.0
    excluded_rows = len(data) - included_rows
    if excluded_rows:
        notes.append(f"{excluded_rows} lignes exclues des comparaisons principales.")
    if bootstrap_iterations and bootstrap_cluster_attribute:
        notes.append(
            f"Bootstrap par cluster sur {bootstrap_cluster_attribute}: les lignes d'un même cas restent groupées."
        )
    notes.append(
        "Les écarts sont standardisés sur les strates R communes; les strates trop petites sont exclues."
    )
    if exposure_attribute:
        if exposure_randomized:
            causal_interpretation = (
                "Effet causal sous l'hypothèse que l'exposition à la recommandation IA a été randomisée "
                "et que le protocole a été respecté."
            )
        else:
            causal_interpretation = (
                "Association conditionnelle uniquement: l'exposition à l'IA n'est pas déclarée randomisée."
            )
        notes.append(causal_interpretation)
    else:
        causal_interpretation = "Non estimé: aucune variable d'exposition à l'IA n'a été fournie."
    notes.append("Le seuil de matérialité est un paramètre d'audit, pas un seuil juridique.")

    alerts: list[str] = []
    if disparity_amplification is not None and disparity_amplification > materiality_threshold:
        interval = intervals.get("disparity_amplification")
        if interval is not None and interval[0] <= materiality_threshold:
            alerts.append(
                "l'estimation ponctuelle suggère une amplification humaine, avec une incertitude qui recoupe le seuil"
            )
        else:
            alerts.append("la décision humaine amplifie la disparité du modèle")
    automation_gap = metrics["automation_bias_gap"]
    if automation_gap is not None and abs(automation_gap) > materiality_threshold:
        interval = intervals.get("automation_bias_gap")
        interval_crosses_threshold = interval is not None and not (
            interval[0] > materiality_threshold or interval[1] < -materiality_threshold
        )
        if interval_crosses_threshold:
            alerts.append(
                "l'estimation ponctuelle de réponse à l'assistance IA est matérielle, mais incertaine"
            )
        else:
            alerts.append("la réponse à l'assistance IA diffère matériellement entre les groupes")
    remedy_gap = metrics["remedy_gap"]
    if remedy_gap is not None and remedy_gap < -materiality_threshold:
        interval = intervals.get("remedy_gap")
        if interval is not None and interval[1] >= -materiality_threshold:
            alerts.append(
                "l'estimation ponctuelle suggère moins de corrections pour le groupe protégé, avec une incertitude qui recoupe le seuil"
            )
        else:
            alerts.append("le groupe protégé obtient moins souvent une correction")
    status = "; ".join(alerts) if alerts else "aucun écart procédural matériel selon le seuil choisi"

    return OversightResult(
        protected_attribute=protected_attribute,
        protected_value=protected_value,
        reference_value=reference_value,
        ai_recommendation_attribute=ai_recommendation_attribute,
        human_decision_attribute=human_decision_attribute,
        favourable_value=favourable_value,
        conditioning_attributes=tuple(conditioning),
        ground_truth_attribute=ground_truth_attribute,
        exposure_attribute=exposure_attribute,
        exposure_randomized=exposure_randomized,
        causal_interpretation=causal_interpretation,
        appeal_attribute=appeal_attribute,
        final_decision_attribute=final_decision_attribute,
        bootstrap_cluster_attribute=bootstrap_cluster_attribute,
        materiality_threshold=materiality_threshold,
        metrics=metrics,
        intervals=intervals,
        group_metrics=group_metrics,
        comparisons=comparisons,
        coverage=coverage,
        included_rows=included_rows,
        excluded_rows=excluded_rows,
        bootstrap_iterations=bootstrap_iterations,
        bootstrap_valid_iterations=bootstrap_valid_iterations,
        confidence_level=confidence_level if bootstrap_iterations else None,
        status=status,
        notes=tuple(notes),
    )


oversight_parity = calculate_oversight_parity
