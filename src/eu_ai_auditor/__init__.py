"""EU AI Auditor public API."""

from .cdd_engine import calculate_cdd, cdd
from .csv_io import read_csv_flexible
from .data_quality import profile_dataset
from .evidence import (
    build_evidence_bundle,
    build_oversight_evidence_bundle,
    dataframe_sha256,
    verify_evidence_bundle,
)
from .intersectional import calculate_intersectional_parity, intersectional_parity
from .models import (
    CDDResult,
    IntersectionalResult,
    OversightResult,
    ProxyMatrixResult,
    QuadrantResult,
    StabilityResult,
    TradeoffResult,
)
from .oversight import calculate_oversight_parity, oversight_parity
from .proxy_matrix import association_score, calculate_proxy_matrix
from .research_bundle import build_research_crate, verify_research_crate
from .risk_quadrants import calculate_risk_quadrants
from .schema_inference import SchemaInference, infer_audit_schema
from .stability import calculate_fairness_stability, fairness_stability
from .tradeoff import compare_models
from .version import __version__

__all__ = [
    "CDDResult",
    "IntersectionalResult",
    "OversightResult",
    "ProxyMatrixResult",
    "QuadrantResult",
    "StabilityResult",
    "TradeoffResult",
    "association_score",
    "build_evidence_bundle",
    "build_oversight_evidence_bundle",
    "build_research_crate",
    "calculate_cdd",
    "calculate_fairness_stability",
    "calculate_intersectional_parity",
    "calculate_oversight_parity",
    "calculate_proxy_matrix",
    "calculate_risk_quadrants",
    "cdd",
    "compare_models",
    "dataframe_sha256",
    "fairness_stability",
    "infer_audit_schema",
    "intersectional_parity",
    "oversight_parity",
    "profile_dataset",
    "read_csv_flexible",
    "SchemaInference",
    "verify_evidence_bundle",
    "verify_research_crate",
    "__version__",
]
