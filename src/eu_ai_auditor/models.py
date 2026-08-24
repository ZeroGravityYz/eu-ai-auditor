"""Typed result objects shared by the audit engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CDDResult:
    """Descriptive Conditional Demographic Disparity result."""

    protected_attribute: str
    protected_value: Any
    decision_attribute: str
    advantaged_value: Any
    conditioning_attributes: tuple[str, ...]
    advantaged_share: float | None
    disadvantaged_share: float | None
    gap: float | None
    directional_signal: bool
    material_signal: bool
    materiality_threshold: float
    coverage: float
    included_rows: int
    excluded_rows: int
    status: str
    strata: pd.DataFrame
    notes: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "protected_attribute": self.protected_attribute,
            "protected_value": self.protected_value,
            "decision_attribute": self.decision_attribute,
            "advantaged_value": self.advantaged_value,
            "conditioning_attributes": list(self.conditioning_attributes),
            "advantaged_share": self.advantaged_share,
            "disadvantaged_share": self.disadvantaged_share,
            "gap": self.gap,
            "directional_signal": self.directional_signal,
            "material_signal": self.material_signal,
            "materiality_threshold": self.materiality_threshold,
            "coverage": self.coverage,
            "included_rows": self.included_rows,
            "excluded_rows": self.excluded_rows,
            "status": self.status,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class ProxyMatrixResult:
    """Pairwise proxy-association scores and risk labels."""

    scores: pd.DataFrame
    matrix: pd.DataFrame
    methods: pd.DataFrame
    low_threshold: float
    high_threshold: float


@dataclass(frozen=True)
class QuadrantResult:
    """Deloitte-style protected-feature impact assessment."""

    features: pd.DataFrame
    subgroups: pd.DataFrame
    mean_threshold: float
    max_threshold: float
    overall_favourable_rate: float


@dataclass(frozen=True)
class TradeoffResult:
    """Model performance and fairness operating points."""

    points: pd.DataFrame
    train_rows: int
    test_rows: int
    excluded_features: tuple[str, ...]
    random_state: int

