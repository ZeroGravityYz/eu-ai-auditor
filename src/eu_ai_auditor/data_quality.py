"""Article 10-oriented descriptive data quality evidence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd


def profile_dataset(
    data: pd.DataFrame,
    protected_attributes: Sequence[str] = (),
    *,
    rare_group_fraction: float = 0.05,
    rare_group_count: int = 30,
) -> dict[str, Any]:
    """Return JSON-safe data quality and representativeness indicators."""

    if data.empty:
        raise ValueError("Le jeu de données est vide.")
    missing_protected = [column for column in protected_attributes if column not in data]
    if missing_protected:
        raise ValueError(f"Colonnes protégées absentes: {', '.join(missing_protected)}")

    columns: list[dict[str, Any]] = []
    for column in data.columns:
        values = data[column]
        record: dict[str, Any] = {
            "column": column,
            "dtype": str(values.dtype),
            "missing_count": int(values.isna().sum()),
            "missing_rate": float(values.isna().mean()),
            "unique_count": int(values.nunique(dropna=True)),
        }
        if pd.api.types.is_numeric_dtype(values):
            numeric = pd.to_numeric(values, errors="coerce")
            record.update(
                {
                    "minimum": _finite_or_none(numeric.min()),
                    "maximum": _finite_or_none(numeric.max()),
                    "mean": _finite_or_none(numeric.mean()),
                }
            )
        columns.append(record)

    representation: list[dict[str, Any]] = []
    warnings: list[str] = []
    for attribute in protected_attributes:
        counts = data[attribute].fillna("<manquant>").value_counts(dropna=False)
        for value, count in counts.items():
            share = count / len(data)
            rare = count < rare_group_count or share < rare_group_fraction
            representation.append(
                {
                    "protected_attribute": attribute,
                    "group": str(value),
                    "count": int(count),
                    "share": float(share),
                    "rare": bool(rare),
                }
            )
            if rare:
                warnings.append(
                    f"{attribute}={value}: sous-groupe peu représenté ({count} lignes, {share:.1%})."
                )

    duplicate_count = int(data.duplicated().sum())
    if duplicate_count:
        warnings.append(f"{duplicate_count} ligne(s) dupliquée(s) détectée(s).")
    high_missing = [item["column"] for item in columns if item["missing_rate"] > 0.20]
    if high_missing:
        warnings.append("Plus de 20 % de valeurs manquantes: " + ", ".join(high_missing) + ".")

    return {
        "rows": len(data),
        "columns_count": len(data.columns),
        "duplicate_count": duplicate_count,
        "overall_missing_rate": float(data.isna().sum().sum() / data.size),
        "columns": columns,
        "representation": representation,
        "warnings": warnings,
    }


def _finite_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if np.isfinite(number) else None

