"""EU AI Auditor public API."""

from .cdd_engine import calculate_cdd, cdd
from .data_quality import profile_dataset
from .evidence import (
    build_evidence_bundle,
    build_oversight_evidence_bundle,
    dataframe_sha256,
    verify_evidence_bundle,
)
from .models import CDDResult, OversightResult, ProxyMatrixResult, QuadrantResult, TradeoffResult
from .oversight import calculate_oversight_parity, oversight_parity
from .proxy_matrix import association_score, calculate_proxy_matrix
from .risk_quadrants import calculate_risk_quadrants
from .tradeoff import compare_models
from .version import __version__

__all__ = [
    "CDDResult",
    "OversightResult",
    "ProxyMatrixResult",
    "QuadrantResult",
    "TradeoffResult",
    "association_score",
    "build_evidence_bundle",
    "build_oversight_evidence_bundle",
    "calculate_cdd",
    "calculate_oversight_parity",
    "calculate_proxy_matrix",
    "calculate_risk_quadrants",
    "cdd",
    "compare_models",
    "dataframe_sha256",
    "oversight_parity",
    "profile_dataset",
    "verify_evidence_bundle",
    "__version__",
]
