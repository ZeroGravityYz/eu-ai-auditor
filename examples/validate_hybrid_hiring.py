"""External validation of OversightParity with Microsoft Hybrid Hiring.

The official archive is downloaded on demand and never redistributed by this
repository. The script reshapes each model condition into a paired event log:
the AI recommendation is hidden in the human-only arm and visible in the
human+AI arm. Bootstrap resampling keeps both arms of a biography together.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd

from eu_ai_auditor import calculate_oversight_parity

SOURCE_URL = (
    "https://download.microsoft.com/download/f/2/e/"
    "f2e0d694-7b0f-4fa6-a436-2e4421796ef3/hybridhiring.zip"
)
SOURCE_SHA256 = "ec2c7f0209e39312392f05582dbcfa389de6b62835dcb5d866d190feb6c839eb"


def _download(path: Path) -> bytes:
    if path.exists():
        payload = path.read_bytes()
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:  # noqa: S310 - fixed HTTPS source
            payload = response.read()
        path.write_bytes(payload)
    digest = hashlib.sha256(payload).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError(f"Archive Hybrid Hiring inattendue: SHA-256 {digest}")
    return payload


def _load(payload: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(BytesIO(payload)) as archive:
        workbook = archive.read("DATA_RELEASE.xlsx")
    return pd.read_excel(BytesIO(workbook), sheet_name="in")


def _reshape(data: pd.DataFrame, model: str) -> pd.DataFrame:
    model_prediction = f"{model}_prediction"
    assisted_prediction = f"human_{model}_prediction"
    common = pd.DataFrame(
        {
            "case_id": data["Unnamed: 0"].astype(str),
            "bio_gender": data["bio_gender"],
            "tested_occupation": data["tested_occupation"],
            "ground_truth": data["true_occupation"].eq(data["tested_occupation"]).astype(int),
            "ai_recommendation": data[model_prediction].eq(data["tested_occupation"]).astype(int),
        }
    )
    hidden = common.assign(
        ai_visible=False,
        human_decision=data["human_only_prediction"].eq(data["tested_occupation"]).astype(int),
    )
    visible = common.assign(
        ai_visible=True,
        human_decision=data[assisted_prediction].eq(data["tested_occupation"]).astype(int),
    )
    return pd.concat([hidden, visible], ignore_index=True)


def run_validation(data: pd.DataFrame, model: str, bootstrap_iterations: int) -> dict:
    events = _reshape(data, model)
    result = calculate_oversight_parity(
        events,
        protected_attribute="bio_gender",
        protected_value="F",
        reference_value="M",
        ai_recommendation_attribute="ai_recommendation",
        human_decision_attribute="human_decision",
        favourable_value=1,
        conditioning_attributes=["tested_occupation"],
        ground_truth_attribute="ground_truth",
        ground_truth_favourable_value=1,
        exposure_attribute="ai_visible",
        exposed_value=True,
        unexposed_value=False,
        exposure_randomized=True,
        bootstrap_cluster_attribute="case_id",
        min_group_count=10,
        bootstrap_iterations=bootstrap_iterations,
        confidence_level=0.95,
        random_state=73,
    )
    return {
        "model": model,
        "rows": len(events),
        "unique_cases": events["case_id"].nunique(),
        "summary": result.summary(),
        "comparisons": result.comparisons.to_dict(orient="records"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-iterations", type=int, default=100)
    parser.add_argument(
        "--archive", type=Path, default=Path("tmp/public_sources/hybridhiring.zip")
    )
    parser.add_argument(
        "--output", type=Path, default=Path("output/evidence/hybrid_hiring_validation.json")
    )
    args = parser.parse_args()
    source = _load(_download(args.archive))
    results = {
        "schema": "eu-ai-auditor.oversight-validation.v1",
        "source": {
            "name": "Microsoft Hybrid Hiring",
            "url": SOURCE_URL,
            "sha256": SOURCE_SHA256,
            "paper": "https://arxiv.org/abs/2202.11812",
        },
        "design_note": (
            "The publication describes a controlled user study. The script treats the human-only "
            "and human+AI conditions as the unexposed and exposed arms and clusters by biography."
        ),
        "models": [
            run_validation(source, model, args.bootstrap_iterations)
            for model in ("dnn", "bow", "random")
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in results["models"]:
        metrics = item["summary"]["metrics"]
        print(
            f"{item['model'].upper()}: automation gap={metrics['automation_bias_gap']:.3f}; "
            f"human gap={metrics['human_gap']:.3f}; AI gap={metrics['ai_gap']:.3f}"
        )
    print(f"Validation written to {args.output}")


if __name__ == "__main__":
    main()
