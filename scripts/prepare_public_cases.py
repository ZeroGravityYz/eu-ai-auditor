"""Download, verify and prepare the two public UCI case-study datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

SOURCES = {
    "adult": {
        "url": "https://archive.ics.uci.edu/static/public/2/adult.zip",
        "sha256": "7537312dd56c2b98035880805ce99e68183a30ee468aa5329d6df0fbb3cc21bb",
        "doi": "10.24432/C5XW20",
    },
    "south_german_credit": {
        "url": "https://archive.ics.uci.edu/static/public/522/south+german+credit.zip",
        "sha256": "0b40d40eb7321693d559e247a556f88a6cc8df8489c3cb2ae084db7592584551",
        "doi": "10.24432/C5X89F",
    },
}

ADULT_COLUMNS = [
    "age",
    "workclass",
    "census_weight",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "relationship",
    "race",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",
]

CREDIT_COLUMNS = [
    "status",
    "duration_months",
    "credit_history",
    "purpose",
    "amount_dm",
    "savings",
    "employment_duration",
    "installment_rate",
    "personal_status_sex",
    "other_debtors",
    "present_residence",
    "property",
    "age",
    "other_installment_plans",
    "housing",
    "number_credits",
    "job",
    "people_liable",
    "telephone",
    "foreign_worker",
    "credit_risk",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _archive(source_dir: Path, key: str) -> Path:
    archive = source_dir / f"{key}.zip"
    source = SOURCES[key]
    if not archive.exists():
        source_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(source["url"], archive)
    actual = _sha256(archive)
    if actual != source["sha256"]:
        raise ValueError(f"Empreinte UCI inattendue pour {archive.name}: {actual}")
    return archive


def _read_archive_text(archive: Path, member: str) -> str:
    with zipfile.ZipFile(archive) as zipped:
        return zipped.read(member).decode("utf-8")


def _prepare_adult(archive: Path, sample_rows: int) -> pd.DataFrame:
    with zipfile.ZipFile(archive) as zipped:
        training = pd.read_csv(
            zipped.open("adult.data"),
            names=ADULT_COLUMNS,
            skipinitialspace=True,
            na_values="?",
        )
        testing = pd.read_csv(
            zipped.open("adult.test"),
            names=ADULT_COLUMNS,
            skiprows=1,
            skipinitialspace=True,
            na_values="?",
        )
    adult = pd.concat([training, testing], ignore_index=True)
    adult["income"] = adult["income"].astype("string").str.rstrip(".")
    adult["age_group"] = pd.cut(
        adult["age"],
        bins=[0, 24, 34, 44, 54, np.inf],
        labels=["under_25", "25_34", "35_44", "45_54", "55_plus"],
    ).astype("string")
    adult["hours_band"] = pd.cut(
        adult["hours_per_week"],
        bins=[0, 34, 40, 49, np.inf],
        labels=["under_35", "35_40", "41_49", "50_plus"],
    ).astype("string")
    adult = adult.dropna(subset=["sex", "race", "income", "education", "age_group"])
    if sample_rows and sample_rows < len(adult):
        stratification = adult[["sex", "income"]].astype(str).agg("|".join, axis=1)
        adult, _ = train_test_split(
            adult,
            train_size=sample_rows,
            random_state=42,
            stratify=stratification,
        )
    return adult.sort_index().reset_index(drop=True)


def _map_codes(frame: pd.DataFrame, column: str, labels: dict[int, str]) -> None:
    frame[column] = frame[column].map(labels).astype("string")


def _prepare_credit(archive: Path) -> pd.DataFrame:
    with zipfile.ZipFile(archive) as zipped:
        frame = pd.read_csv(zipped.open("SouthGermanCredit.asc"), sep=r"\s+")
    frame.columns = CREDIT_COLUMNS
    mappings = {
        "status": {
            1: "no_checking_account",
            2: "below_0_dm",
            3: "0_to_200_dm",
            4: "200_plus_dm",
        },
        "credit_history": {
            0: "past_delay",
            1: "critical_or_other_credits",
            2: "no_or_repaid_credits",
            3: "repaid_to_date",
            4: "all_repaid_at_bank",
        },
        "purpose": {
            0: "other",
            1: "new_car",
            2: "used_car",
            3: "furniture_equipment",
            4: "radio_television",
            5: "domestic_appliances",
            6: "repairs",
            7: "education",
            8: "vacation",
            9: "retraining",
            10: "business",
        },
        "savings": {
            1: "unknown_or_none",
            2: "below_100_dm",
            3: "100_to_500_dm",
            4: "500_to_1000_dm",
            5: "1000_plus_dm",
        },
        "employment_duration": {
            1: "unemployed",
            2: "under_1_year",
            3: "1_to_4_years",
            4: "4_to_7_years",
            5: "7_plus_years",
        },
        "personal_status_sex": {
            1: "male_divorced_or_separated",
            2: "female_non_single_or_male_single",
            3: "male_married_or_widowed",
            4: "female_single",
        },
        "other_debtors": {1: "none", 2: "co_applicant", 3: "guarantor"},
        "property": {
            1: "unknown_or_none",
            2: "car_or_other",
            3: "savings_or_life_insurance",
            4: "real_estate",
        },
        "other_installment_plans": {1: "bank", 2: "stores", 3: "none"},
        "housing": {1: "free", 2: "rent", 3: "own"},
        "job": {
            1: "unemployed_or_nonresident_unskilled",
            2: "resident_unskilled",
            3: "skilled_employee_or_official",
            4: "manager_or_self_employed",
        },
        "telephone": {1: "no", 2: "yes"},
        "foreign_worker": {1: "yes", 2: "no"},
        "credit_risk": {0: "bad", 1: "good"},
    }
    for column, labels in mappings.items():
        _map_codes(frame, column, labels)
    frame["age_group"] = pd.cut(
        frame["age"],
        bins=[0, 24, 34, 49, np.inf],
        labels=["under_25", "25_34", "35_49", "50_plus"],
    ).astype("string")
    return frame


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=Path("tmp/datasets"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/cases"))
    parser.add_argument("--adult-sample", type=int, default=6000)
    args = parser.parse_args()

    adult_archive = _archive(args.source_dir, "adult")
    credit_archive = _archive(args.source_dir, "south_german_credit")
    adult = _prepare_adult(adult_archive, args.adult_sample)
    credit = _prepare_credit(credit_archive)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    adult_path = args.output_dir / "adult_income_sample.csv"
    credit_path = args.output_dir / "south_german_credit.csv"
    adult.to_csv(adult_path, index=False)
    credit.to_csv(credit_path, index=False)
    manifest = {
        "schema": "eu-ai-auditor.public-datasets.v1",
        "sources": SOURCES,
        "outputs": {
            adult_path.name: {"rows": len(adult), "sha256": _sha256(adult_path)},
            credit_path.name: {"rows": len(credit), "sha256": _sha256(credit_path)},
        },
        "preparation": {
            "script": "scripts/prepare_public_cases.py",
            "random_state": 42,
            "adult_sample_rows": args.adult_sample,
        },
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest["outputs"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
