"""Versioned, integrity-verifiable evidence manifests for audit runs."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from .models import (
    CDDResult,
    IntersectionalResult,
    OversightResult,
    ProxyMatrixResult,
    QuadrantResult,
    TradeoffResult,
)
from .serialization import json_compatible
from .version import __version__

EVIDENCE_SCHEMA = "eu-ai-auditor.evidence.v1"
OVERSIGHT_EVIDENCE_SCHEMA = "eu-ai-auditor.oversight-evidence.v1"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        json_compatible(value),
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def dataframe_sha256(data: pd.DataFrame) -> str:
    """Return a stable digest of values, index, column order and dtypes."""

    descriptor = {
        "columns": [str(column) for column in data.columns],
        "dtypes": [str(dtype) for dtype in data.dtypes],
        "index_name": str(data.index.name),
    }
    digest = hashlib.sha256(_canonical_bytes(descriptor))
    digest.update(pd.util.hash_pandas_object(data, index=True).values.tobytes())
    return digest.hexdigest()


def _result_payload(
    cdd_result: CDDResult,
    proxy_result: ProxyMatrixResult,
    quadrant_result: QuadrantResult | None,
    tradeoff_result: TradeoffResult | None,
    intersectional_result: IntersectionalResult | None,
) -> dict[str, Any]:
    return {
        "cdd": cdd_result.summary(),
        "proxy_scores": proxy_result.scores.to_dict(orient="records"),
        "quadrants": (
            quadrant_result.features.to_dict(orient="records") if quadrant_result else None
        ),
        "tradeoff": tradeoff_result.points.to_dict(orient="records") if tradeoff_result else None,
        "intersectional": (
            {
                "summary": intersectional_result.summary(),
                "groups": intersectional_result.groups.to_dict(orient="records"),
            }
            if intersectional_result
            else None
        ),
    }


def build_evidence_bundle(
    data: pd.DataFrame,
    cdd_result: CDDResult,
    proxy_result: ProxyMatrixResult,
    *,
    quadrant_result: QuadrantResult | None = None,
    tradeoff_result: TradeoffResult | None = None,
    intersectional_result: IntersectionalResult | None = None,
    metadata: dict[str, Any] | None = None,
    report_bytes: bytes | None = None,
    generated_at: str | None = None,
    signing_key: str | bytes | None = None,
) -> dict[str, Any]:
    """Create a portable evidence manifest without embedding source records.

    A SHA-256 digest always protects the canonical manifest. When ``signing_key``
    is supplied, an HMAC-SHA256 is added. The key is never stored in the bundle.
    """

    metadata = dict(metadata or {})
    results = _result_payload(
        cdd_result,
        proxy_result,
        quadrant_result,
        tradeoff_result,
        intersectional_result,
    )
    metadata = json_compatible(metadata)
    results = json_compatible(results)
    audit_basis = {
        "dataset_sha256": dataframe_sha256(data),
        "configuration": {
            "protected_attribute": cdd_result.protected_attribute,
            "protected_value": cdd_result.protected_value,
            "decision_attribute": cdd_result.decision_attribute,
            "advantaged_value": cdd_result.advantaged_value,
            "conditioning_attributes": list(cdd_result.conditioning_attributes),
            "materiality_threshold": cdd_result.materiality_threshold,
            "bootstrap_iterations": cdd_result.bootstrap_iterations,
            "confidence_level": cdd_result.confidence_level,
        },
        "system_name": metadata.get("system_name", "Système évalué"),
        "system_version": metadata.get("system_version", "À compléter"),
    }
    audit_id = "audit-" + hashlib.sha256(_canonical_bytes(audit_basis)).hexdigest()[:16]
    bundle: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "audit_id": audit_id,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "software": {"name": "eu-ai-auditor", "version": __version__},
        "dataset": {
            "sha256": audit_basis["dataset_sha256"],
            "rows": len(data),
            "columns": len(data.columns),
            "column_names": [str(column) for column in data.columns],
        },
        "metadata": metadata,
        "results": results,
        "artifacts": {
            "report_pdf": (
                {
                    "sha256": hashlib.sha256(report_bytes).hexdigest(),
                    "bytes": len(report_bytes),
                }
                if report_bytes is not None
                else None
            )
        },
    }
    manifest_sha256 = hashlib.sha256(_canonical_bytes(bundle)).hexdigest()
    integrity: dict[str, Any] = {
        "canonicalization": "JSON UTF-8, sorted keys, compact separators",
        "manifest_sha256": manifest_sha256,
    }
    if signing_key is not None:
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        integrity["hmac_sha256"] = hmac.new(
            key, manifest_sha256.encode("ascii"), hashlib.sha256
        ).hexdigest()
    bundle["integrity"] = integrity
    return bundle


def build_oversight_evidence_bundle(
    data: pd.DataFrame,
    result: OversightResult,
    *,
    metadata: dict[str, Any] | None = None,
    report_bytes: bytes | None = None,
    generated_at: str | None = None,
    signing_key: str | bytes | None = None,
) -> dict[str, Any]:
    """Create an integrity-verifiable manifest for an OversightParity audit."""

    metadata = dict(metadata or {})
    audit_basis = {
        "dataset_sha256": dataframe_sha256(data),
        "configuration": {
            "protected_attribute": result.protected_attribute,
            "protected_value": result.protected_value,
            "reference_value": result.reference_value,
            "ai_recommendation_attribute": result.ai_recommendation_attribute,
            "human_decision_attribute": result.human_decision_attribute,
            "favourable_value": result.favourable_value,
            "conditioning_attributes": list(result.conditioning_attributes),
            "ground_truth_attribute": result.ground_truth_attribute,
            "exposure_attribute": result.exposure_attribute,
            "exposure_randomized": result.exposure_randomized,
            "appeal_attribute": result.appeal_attribute,
            "final_decision_attribute": result.final_decision_attribute,
            "bootstrap_cluster_attribute": result.bootstrap_cluster_attribute,
            "materiality_threshold": result.materiality_threshold,
            "bootstrap_iterations": result.bootstrap_iterations,
            "confidence_level": result.confidence_level,
        },
        "system_name": metadata.get("system_name", "Système évalué"),
        "system_version": metadata.get("system_version", "À compléter"),
    }
    audit_id = "oversight-" + hashlib.sha256(_canonical_bytes(audit_basis)).hexdigest()[:16]
    bundle: dict[str, Any] = {
        "schema": OVERSIGHT_EVIDENCE_SCHEMA,
        "audit_id": audit_id,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "software": {"name": "eu-ai-auditor", "version": __version__},
        "dataset": {
            "sha256": audit_basis["dataset_sha256"],
            "rows": len(data),
            "columns": len(data.columns),
            "column_names": [str(column) for column in data.columns],
        },
        "metadata": metadata,
        "results": {
            "oversight": result.summary(),
            "group_metrics": result.group_metrics.to_dict(orient="records"),
            "comparisons": result.comparisons.to_dict(orient="records"),
        },
        "artifacts": {
            "report_pdf": (
                {
                    "sha256": hashlib.sha256(report_bytes).hexdigest(),
                    "bytes": len(report_bytes),
                }
                if report_bytes is not None
                else None
            )
        },
    }
    bundle = json_compatible(bundle)
    manifest_sha256 = hashlib.sha256(_canonical_bytes(bundle)).hexdigest()
    integrity: dict[str, Any] = {
        "canonicalization": "JSON UTF-8, sorted keys, compact separators",
        "manifest_sha256": manifest_sha256,
    }
    if signing_key is not None:
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        integrity["hmac_sha256"] = hmac.new(
            key, manifest_sha256.encode("ascii"), hashlib.sha256
        ).hexdigest()
    bundle["integrity"] = integrity
    return bundle


def verify_evidence_bundle(
    bundle: dict[str, Any],
    *,
    report_bytes: bytes | None = None,
    signing_key: str | bytes | None = None,
) -> dict[str, Any]:
    """Verify manifest, optional report artifact and optional HMAC signature."""

    candidate = dict(bundle)
    integrity = dict(candidate.pop("integrity", {}))
    expected_manifest = integrity.get("manifest_sha256")
    actual_manifest = hashlib.sha256(_canonical_bytes(candidate)).hexdigest()
    manifest_valid = bool(expected_manifest) and hmac.compare_digest(
        str(expected_manifest), actual_manifest
    )

    expected_report = (candidate.get("artifacts", {}).get("report_pdf") or {}).get("sha256")
    report_valid: bool | None = None
    if report_bytes is not None:
        report_valid = bool(expected_report) and hmac.compare_digest(
            str(expected_report), hashlib.sha256(report_bytes).hexdigest()
        )

    expected_hmac = integrity.get("hmac_sha256")
    hmac_valid: bool | None = None
    if expected_hmac is not None and signing_key is not None:
        key = signing_key.encode("utf-8") if isinstance(signing_key, str) else signing_key
        actual_hmac = hmac.new(
            key, str(expected_manifest).encode("ascii"), hashlib.sha256
        ).hexdigest()
        hmac_valid = hmac.compare_digest(str(expected_hmac), actual_hmac)

    checks = [manifest_valid]
    if report_valid is not None:
        checks.append(report_valid)
    if expected_hmac is not None:
        checks.append(hmac_valid is True)
    return {
        "valid": all(checks),
        "manifest_valid": manifest_valid,
        "report_valid": report_valid,
        "hmac_present": expected_hmac is not None,
        "hmac_valid": hmac_valid,
        "audit_id": candidate.get("audit_id"),
    }
