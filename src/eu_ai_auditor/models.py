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
    confidence_level: float | None
    confidence_low: float | None
    confidence_high: float | None
    bootstrap_iterations: int
    bootstrap_valid_iterations: int
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
            "confidence_level": self.confidence_level,
            "confidence_low": self.confidence_low,
            "confidence_high": self.confidence_high,
            "bootstrap_iterations": self.bootstrap_iterations,
            "bootstrap_valid_iterations": self.bootstrap_valid_iterations,
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


@dataclass(frozen=True)
class OversightResult:
    """Fairness audit of an AI recommendation, human decision and remedy chain."""

    protected_attribute: str
    protected_value: Any
    reference_value: Any
    ai_recommendation_attribute: str
    human_decision_attribute: str
    favourable_value: Any
    conditioning_attributes: tuple[str, ...]
    ground_truth_attribute: str | None
    exposure_attribute: str | None
    exposure_randomized: bool
    causal_interpretation: str
    appeal_attribute: str | None
    final_decision_attribute: str | None
    bootstrap_cluster_attribute: str | None
    materiality_threshold: float
    metrics: dict[str, float | None]
    intervals: dict[str, tuple[float, float] | None]
    group_metrics: pd.DataFrame
    comparisons: pd.DataFrame
    coverage: float
    included_rows: int
    excluded_rows: int
    bootstrap_iterations: int
    bootstrap_valid_iterations: int
    confidence_level: float | None
    status: str
    notes: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "protected_attribute": self.protected_attribute,
            "protected_value": self.protected_value,
            "reference_value": self.reference_value,
            "ai_recommendation_attribute": self.ai_recommendation_attribute,
            "human_decision_attribute": self.human_decision_attribute,
            "favourable_value": self.favourable_value,
            "conditioning_attributes": list(self.conditioning_attributes),
            "ground_truth_attribute": self.ground_truth_attribute,
            "exposure_attribute": self.exposure_attribute,
            "exposure_randomized": self.exposure_randomized,
            "causal_interpretation": self.causal_interpretation,
            "appeal_attribute": self.appeal_attribute,
            "final_decision_attribute": self.final_decision_attribute,
            "bootstrap_cluster_attribute": self.bootstrap_cluster_attribute,
            "materiality_threshold": self.materiality_threshold,
            "metrics": self.metrics,
            "intervals": {
                key: list(value) if value is not None else None
                for key, value in self.intervals.items()
            },
            "coverage": self.coverage,
            "included_rows": self.included_rows,
            "excluded_rows": self.excluded_rows,
            "bootstrap_iterations": self.bootstrap_iterations,
            "bootstrap_valid_iterations": self.bootstrap_valid_iterations,
            "confidence_level": self.confidence_level,
            "status": self.status,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class IntersectionalResult:
    """Outcome-parity audit across one or more intersecting attributes."""

    protected_attributes: tuple[str, ...]
    decision_attribute: str
    favourable_value: Any
    overall_favourable_rate: float
    materiality_threshold: float
    confidence_level: float
    fdr_alpha: float
    groups: pd.DataFrame
    eligible_groups: int
    flagged_groups: int
    coverage: float
    included_rows: int
    excluded_rows: int
    worst_case_gap: float | None
    lowest_rate_group: str | None
    highest_rate_group: str | None
    status: str
    notes: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "protected_attributes": list(self.protected_attributes),
            "decision_attribute": self.decision_attribute,
            "favourable_value": self.favourable_value,
            "overall_favourable_rate": self.overall_favourable_rate,
            "materiality_threshold": self.materiality_threshold,
            "confidence_level": self.confidence_level,
            "fdr_alpha": self.fdr_alpha,
            "eligible_groups": self.eligible_groups,
            "flagged_groups": self.flagged_groups,
            "coverage": self.coverage,
            "included_rows": self.included_rows,
            "excluded_rows": self.excluded_rows,
            "worst_case_gap": self.worst_case_gap,
            "lowest_rate_group": self.lowest_rate_group,
            "highest_rate_group": self.highest_rate_group,
            "status": self.status,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class StabilityResult:
    """Sensitivity of a CDD conclusion across defensible conditioning choices."""

    protected_attribute: str
    protected_value: Any
    decision_attribute: str
    favourable_value: Any
    conditioning_candidates: tuple[str, ...]
    max_conditioning_factors: int
    materiality_threshold: float
    consensus_threshold: float
    minimum_coverage: float
    minimum_valid_share: float
    specifications: pd.DataFrame
    factor_effects: pd.DataFrame
    total_specifications: int
    valid_specifications: int
    valid_share: float
    dominant_class: str
    dominant_share: float
    robustness_score: float
    median_coverage: float
    gap_min: float
    gap_median: float
    gap_max: float
    range_crosses_zero: bool
    status: str
    notes: tuple[str, ...] = ()

    def summary(self) -> dict[str, Any]:
        return {
            "protected_attribute": self.protected_attribute,
            "protected_value": self.protected_value,
            "decision_attribute": self.decision_attribute,
            "favourable_value": self.favourable_value,
            "conditioning_candidates": list(self.conditioning_candidates),
            "max_conditioning_factors": self.max_conditioning_factors,
            "materiality_threshold": self.materiality_threshold,
            "consensus_threshold": self.consensus_threshold,
            "minimum_coverage": self.minimum_coverage,
            "minimum_valid_share": self.minimum_valid_share,
            "total_specifications": self.total_specifications,
            "valid_specifications": self.valid_specifications,
            "valid_share": self.valid_share,
            "dominant_class": self.dominant_class,
            "dominant_share": self.dominant_share,
            "robustness_score": self.robustness_score,
            "median_coverage": self.median_coverage,
            "gap_min": self.gap_min,
            "gap_median": self.gap_median,
            "gap_max": self.gap_max,
            "range_crosses_zero": self.range_crosses_zero,
            "status": self.status,
            "notes": list(self.notes),
        }
