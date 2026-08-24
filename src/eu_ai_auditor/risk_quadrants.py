"""Protected-feature impact quadrants inspired by Deloitte's whitepaper."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import pandas as pd

from .models import QuadrantResult


def calculate_risk_quadrants(
    data: pd.DataFrame,
    protected_attributes: Sequence[str],
    decision_attribute: str,
    favourable_value: Any,
    *,
    mean_threshold: float = 0.05,
    max_threshold: float = 0.10,
) -> QuadrantResult:
    """Calculate weighted-mean and maximum absolute outcome disparity."""

    protected = list(dict.fromkeys(protected_attributes))
    required = [*protected, decision_attribute]
    missing = [column for column in required if column not in data]
    if missing:
        raise ValueError(f"Colonnes absentes: {', '.join(missing)}")
    if not protected:
        raise ValueError("Sélectionnez au moins une variable protégée.")
    if not 0 <= mean_threshold <= 1 or not 0 <= max_threshold <= 1:
        raise ValueError("Les seuils doivent être compris entre 0 et 1.")

    valid_decisions = data[decision_attribute].dropna()
    if favourable_value not in set(valid_decisions.unique()):
        raise ValueError("L'issue favorable sélectionnée est absente des données.")
    favourable = data[decision_attribute].eq(favourable_value)
    overall_rate = float(favourable[valid_decisions.index].mean())
    feature_records: list[dict[str, object]] = []
    subgroup_records: list[dict[str, object]] = []

    for attribute in protected:
        valid = data[[attribute, decision_attribute]].dropna()
        rows: list[dict[str, object]] = []
        for group_value, group in valid.groupby(attribute, observed=True, dropna=False):
            rate = float(group[decision_attribute].eq(favourable_value).mean())
            disparity = rate - overall_rate
            row = {
                "protected_attribute": attribute,
                "group": str(group_value),
                "n": len(group),
                "population_share": len(group) / len(valid),
                "favourable_rate": rate,
                "outcome_disparity": disparity,
                "absolute_disparity": abs(disparity),
            }
            rows.append(row)
            subgroup_records.append(row)
        subgroup_frame = pd.DataFrame(rows)
        mean_abs = float(
            (subgroup_frame["absolute_disparity"] * subgroup_frame["population_share"]).sum()
        )
        max_abs = float(subgroup_frame["absolute_disparity"].max())
        mean_high = mean_abs >= mean_threshold
        max_high = max_abs >= max_threshold
        if mean_high and max_high:
            quadrant = "Biais extrême"
        elif mean_high:
            quadrant = "Impact élevé"
        elif max_high:
            quadrant = "Sous-groupes marginalisés"
        else:
            quadrant = "Impact faible"
        feature_records.append(
            {
                "protected_attribute": attribute,
                "weighted_mean_disparity": mean_abs,
                "maximum_disparity": max_abs,
                "quadrant": quadrant,
                "n_groups": len(subgroup_frame),
                "n_rows": len(valid),
            }
        )

    return QuadrantResult(
        features=pd.DataFrame(feature_records),
        subgroups=pd.DataFrame(subgroup_records),
        mean_threshold=mean_threshold,
        max_threshold=max_threshold,
        overall_favourable_rate=overall_rate,
    )

