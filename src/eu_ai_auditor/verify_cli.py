"""Command-line verification for evidence manifests and PDF artifacts."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .evidence import verify_evidence_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="eu-ai-auditor-verify")
    parser.add_argument("evidence", type=Path, help="Manifeste JSON à vérifier")
    parser.add_argument("--report", type=Path, help="PDF associé à vérifier")
    parser.add_argument("--signing-key-env", help="Variable d'environnement de la clé HMAC")
    args = parser.parse_args(argv)
    bundle = json.loads(args.evidence.read_text(encoding="utf-8"))
    report = args.report.read_bytes() if args.report else None
    signing_key = os.environ.get(args.signing_key_env) if args.signing_key_env else None
    result = verify_evidence_bundle(bundle, report_bytes=report, signing_key=signing_key)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
