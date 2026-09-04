"""Portable research exports using RO-Crate and Croissant metadata."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO
from pathlib import PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pandas as pd

from .evidence import verify_evidence_bundle
from .serialization import json_compatible
from .version import __version__

RESEARCH_CRATE_SCHEMA = "eu-ai-auditor.research-crate.v1"
RO_CRATE_VERSION = "1.3"
CROISSANT_VERSION = "1.1"


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        json_compatible(value),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
        allow_nan=False,
    ).encode("utf-8")


def _strict_json_loads(payload: bytes) -> Any:
    def reject_non_finite(value: str) -> None:
        raise ValueError(f"non-finite JSON number: {value}")

    return json.loads(payload, parse_constant=reject_non_finite)


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip()).strip("-.")
    return normalized.lower() or "result"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _package_versions() -> dict[str, str]:
    packages = ["eu-ai-auditor", "numpy", "pandas", "scipy", "scikit-learn", "matplotlib"]
    installed: dict[str, str] = {}
    for package in packages:
        try:
            installed[package] = version(package)
        except PackageNotFoundError:
            if package == "eu-ai-auditor":
                installed[package] = __version__
    return installed


def _field_type(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "sc:Boolean"
    if pd.api.types.is_integer_dtype(series):
        return "sc:Integer"
    if pd.api.types.is_numeric_dtype(series):
        return "sc:Float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "sc:DateTime"
    return "sc:Text"


def _croissant_metadata(
    data: pd.DataFrame,
    *,
    title: str,
    description: str,
    license_url: str,
    include_source_data: bool,
) -> dict[str, Any]:
    fields = [
        {
            "@type": "cr:Field",
            "@id": f"records/{_slug(str(column))}",
            "name": str(column),
            "description": f"Column {column}; source dtype {data[column].dtype}.",
            "dataType": _field_type(data[column]),
        }
        for column in data.columns
    ]
    metadata: dict[str, Any] = {
        "@context": {
            "@language": "en",
            "sc": "https://schema.org/",
            "cr": "http://mlcommons.org/croissant/",
            "dct": "http://purl.org/dc/terms/",
        },
        "@type": "sc:Dataset",
        "name": title,
        "description": description,
        "license": license_url,
        "dct:conformsTo": f"http://mlcommons.org/croissant/{CROISSANT_VERSION}",
        "recordSet": [
            {
                "@type": "cr:RecordSet",
                "@id": "records",
                "name": "Audit source records",
                "description": (
                    "Source records embedded in this crate."
                    if include_source_data
                    else "Schema only; source records are intentionally not embedded."
                ),
                "field": fields,
            }
        ],
    }
    if include_source_data:
        metadata["distribution"] = [
            {
                "@type": "cr:FileObject",
                "@id": "data/source.csv",
                "name": "Source audit data",
                "encodingFormat": "text/csv",
                "sha256": _sha256(data.to_csv(index=False).encode("utf-8")),
            }
        ]
    return metadata


def _citation_cff(title: str, creators: Sequence[str], released: str) -> bytes:
    author_lines = "\n".join(f"  - name: {json.dumps(name, ensure_ascii=False)}" for name in creators)
    content = (
        "cff-version: 1.2.0\n"
        'message: "If you use this audit package, please cite EU AI Auditor and the archived crate."\n'
        f"title: {json.dumps(title, ensure_ascii=False)}\n"
        "type: dataset\n"
        f"version: {json.dumps(__version__)}\n"
        f"date-released: {released[:10]}\n"
        "authors:\n"
        f"{author_lines}\n"
        'repository-code: "https://github.com/ZeroGravityYz/eu-ai-auditor"\n'
        'license: "Apache-2.0"\n'
    )
    return content.encode("utf-8")


def _media_type(path: str) -> str:
    suffix = PurePosixPath(path).suffix.lower()
    return {
        ".csv": "text/csv",
        ".json": "application/json",
        ".cff": "text/yaml",
        ".md": "text/markdown",
        ".txt": "text/plain",
        ".sha256": "text/plain",
    }.get(suffix, "application/octet-stream")


def _ro_crate_metadata(
    files: Mapping[str, bytes],
    *,
    title: str,
    description: str,
    generated_at: str,
    license_url: str,
    creators: Sequence[str],
    dataset_sha256: str,
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    for path, payload in sorted(files.items()):
        entities.append(
            {
                "@id": path,
                "@type": "File",
                "name": path,
                "encodingFormat": _media_type(path),
                "contentSize": str(len(payload)),
                "sha256": _sha256(payload),
            }
        )
    creator_entities = [
        {"@id": f"#creator-{index}", "@type": "Organization", "name": name}
        for index, name in enumerate(creators, start=1)
    ]
    creator_refs = [{"@id": entity["@id"]} for entity in creator_entities]
    return {
        "@context": f"https://w3id.org/ro/crate/{RO_CRATE_VERSION}/context",
        "@graph": [
            {
                "@id": "ro-crate-metadata.json",
                "@type": "CreativeWork",
                "about": {"@id": "./"},
                "conformsTo": {"@id": f"https://w3id.org/ro/crate/{RO_CRATE_VERSION}"},
            },
            {
                "@id": "./",
                "@type": "Dataset",
                "name": title,
                "description": description,
                "datePublished": generated_at,
                "license": license_url,
                "creator": creator_refs,
                "hasPart": [{"@id": path} for path in sorted(files)],
                "mentions": [{"@id": "#audit-run"}, {"@id": "#source-dataset"}],
            },
            {
                "@id": "#source-dataset",
                "@type": "Dataset",
                "name": "Source dataset fingerprint",
                "description": f"SHA-256: {dataset_sha256}. Raw records may be intentionally excluded.",
            },
            {
                "@id": "#eu-ai-auditor",
                "@type": "SoftwareApplication",
                "name": "EU AI Auditor",
                "softwareVersion": __version__,
                "codeRepository": "https://github.com/ZeroGravityYz/eu-ai-auditor",
            },
            {
                "@id": "#audit-run",
                "@type": "CreateAction",
                "name": "Fairness audit execution",
                "endTime": generated_at,
                "instrument": {"@id": "#eu-ai-auditor"},
                "object": {"@id": "#source-dataset"},
                "result": {"@id": "audit/manifest.json"},
            },
            *creator_entities,
            *entities,
        ],
    }


def build_research_crate(
    data: pd.DataFrame,
    evidence_bundle: Mapping[str, Any],
    *,
    audit_kind: str,
    config: Mapping[str, Any],
    tables: Mapping[str, pd.DataFrame],
    title: str = "EU AI Auditor research audit",
    description: str = "Reproducible fairness audit results and provenance metadata.",
    creators: Sequence[str] = ("EU AI Auditor contributors",),
    license_url: str = "https://www.apache.org/licenses/LICENSE-2.0",
    include_source_data: bool = False,
    generated_at: str | None = None,
) -> bytes:
    """Build a portable ZIP research object without source rows by default."""

    if data.empty:
        raise ValueError("Le jeu de données est vide.")
    if not creators or not all(str(name).strip() for name in creators):
        raise ValueError("Au moins un créateur non vide est requis.")
    if "integrity" not in evidence_bundle or "dataset" not in evidence_bundle:
        raise ValueError("Le manifeste de preuves est incomplet.")
    if not verify_evidence_bundle(dict(evidence_bundle))["manifest_valid"]:
        raise ValueError("Le manifeste de preuves n'est pas valide.")

    timestamp = generated_at or datetime.now(timezone.utc).isoformat()
    files: dict[str, bytes] = {
        "audit/manifest.json": _json_bytes(evidence_bundle),
        "audit/config.json": _json_bytes(
            {
                "schema": RESEARCH_CRATE_SCHEMA,
                "audit_kind": audit_kind,
                "generated_at": timestamp,
                "config": config,
            }
        ),
        "metadata/croissant.json": _json_bytes(
            _croissant_metadata(
                data,
                title=title,
                description=description,
                license_url=license_url,
                include_source_data=include_source_data,
            )
        ),
        "software/environment.json": _json_bytes(
            {
                "python": sys.version.split()[0],
                "implementation": platform.python_implementation(),
                "platform": platform.system(),
                "packages": _package_versions(),
            }
        ),
        "CITATION.cff": _citation_cff(title, creators, timestamp),
    }
    for name, table in tables.items():
        files[f"results/{_slug(name)}.csv"] = table.to_csv(index=False).encode("utf-8")
    if include_source_data:
        files["data/source.csv"] = data.to_csv(index=False).encode("utf-8")

    dataset_digest = str(evidence_bundle["dataset"]["sha256"])
    readme = f"""# {title}

This RO-Crate contains a reproducible `{audit_kind}` fairness audit generated by EU AI Auditor {__version__}.

- Source dataset SHA-256: `{dataset_digest}`
- Source rows embedded: `{str(include_source_data).lower()}`
- Audit manifest: `audit/manifest.json`
- Exact configuration: `audit/config.json`
- Tidy result tables: `results/`
- Dataset schema metadata: `metadata/croissant.json`

The metrics are statistical evidence, not a legal finding or certification. Review group definitions,
conditioning variables, missingness, sampling and the deployment context before reuse.
"""
    files["README.md"] = readme.encode("utf-8")
    checksum_lines = [f"{_sha256(payload)}  {path}" for path, payload in sorted(files.items())]
    files["checksums.sha256"] = ("\n".join(checksum_lines) + "\n").encode("utf-8")
    files["ro-crate-metadata.json"] = _json_bytes(
        _ro_crate_metadata(
            files,
            title=title,
            description=description,
            generated_at=timestamp,
            license_url=license_url,
            creators=creators,
            dataset_sha256=dataset_digest,
        )
    )

    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path, payload in sorted(files.items()):
            info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)
    return stream.getvalue()


def verify_research_crate(payload: bytes) -> dict[str, Any]:
    """Verify safe paths, required metadata, payload checksums and evidence integrity."""

    errors: list[str] = []
    try:
        with ZipFile(BytesIO(payload)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                errors.append("duplicate file names")
            unsafe = [
                name
                for name in names
                if PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
            ]
            if unsafe:
                errors.append("unsafe archive paths")
            required = {
                "ro-crate-metadata.json",
                "metadata/croissant.json",
                "audit/manifest.json",
                "audit/config.json",
                "checksums.sha256",
                "CITATION.cff",
                "README.md",
            }
            missing = sorted(required.difference(names))
            if missing:
                errors.append("missing: " + ", ".join(missing))

            if not missing:
                _strict_json_loads(archive.read("ro-crate-metadata.json"))
                _strict_json_loads(archive.read("metadata/croissant.json"))
                _strict_json_loads(archive.read("audit/config.json"))
                manifest = _strict_json_loads(archive.read("audit/manifest.json"))
                if not verify_evidence_bundle(manifest)["manifest_valid"]:
                    errors.append("invalid evidence manifest")
                for line in archive.read("checksums.sha256").decode("utf-8").splitlines():
                    expected, separator, path = line.partition("  ")
                    if not separator or path not in names:
                        errors.append(f"invalid checksum entry: {line}")
                        continue
                    if _sha256(archive.read(path)) != expected:
                        errors.append(f"checksum mismatch: {path}")
    except Exception as exc:
        errors.append(f"unreadable crate: {exc}")
    return {"valid": not errors, "errors": errors}
