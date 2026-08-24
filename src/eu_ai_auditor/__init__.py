"""EU AI Auditor public API."""

from .cdd_engine import calculate_cdd, cdd
from .data_quality import profile_dataset
from .models import CDDResult, ProxyMatrixResult, QuadrantResult, TradeoffResult
from .proxy_matrix import association_score, calculate_proxy_matrix
from .risk_quadrants import calculate_risk_quadrants
from .tradeoff import compare_models

__all__ = [
    "CDDResult",
    "ProxyMatrixResult",
    "QuadrantResult",
    "TradeoffResult",
    "association_score",
    "calculate_cdd",
    "calculate_proxy_matrix",
    "calculate_risk_quadrants",
    "cdd",
    "compare_models",
    "profile_dataset",
]

__version__ = "0.1.0"

