"""Deterministic synthetic recruitment dataset used in documentation and tests."""

from __future__ import annotations

import numpy as np
import pandas as pd


def make_demo_dataset(rows: int = 600, random_state: int = 17) -> pd.DataFrame:
    """Create realistic-looking, entirely synthetic recruitment audit data."""

    if rows < 100:
        raise ValueError("La démonstration nécessite au moins 100 lignes.")
    rng = np.random.default_rng(random_state)
    gender = rng.choice(["Femme", "Homme"], rows, p=[0.48, 0.52])
    age = np.clip(rng.normal(38, 10, rows).round(), 20, 64).astype(int)
    degree = rng.choice(["Licence", "Master", "Doctorat"], rows, p=[0.49, 0.43, 0.08])
    tenure = np.clip(rng.gamma(2.2, 2.2, rows).round(1), 0, 18)
    postcode_zone = np.where(
        gender == "Femme",
        rng.choice(["Centre", "Nord", "Sud", "Ouest"], rows, p=[0.22, 0.40, 0.20, 0.18]),
        rng.choice(["Centre", "Nord", "Sud", "Ouest"], rows, p=[0.33, 0.19, 0.25, 0.23]),
    )
    sector = rng.choice(["Tech", "Finance", "Industrie", "Services"], rows, p=[0.30, 0.22, 0.20, 0.28])
    score = (
        0.55 * (degree == "Master")
        + 0.95 * (degree == "Doctorat")
        + 0.08 * tenure
        + 0.18 * (sector == "Tech")
        - 0.33 * (gender == "Femme")
        - 0.18 * ((gender == "Femme") & (postcode_zone == "Nord"))
        + rng.normal(0, 0.75, rows)
    )
    probability = 1 / (1 + np.exp(-(score - 0.35)))
    selected = rng.binomial(1, probability)
    performance = (
        0.50 * (degree == "Master")
        + 0.85 * (degree == "Doctorat")
        + 0.07 * tenure
        + rng.normal(0, 0.85, rows)
        > 0.55
    )
    return pd.DataFrame(
        {
            "genre": gender,
            "age": age,
            "diplome": degree,
            "anciennete_annees": tenure,
            "zone_postale": postcode_zone,
            "secteur": sector,
            "selection": np.where(selected == 1, "Retenu", "Non retenu"),
            "performance_observee": np.where(performance, "Satisfaisante", "Insuffisante"),
        }
    )


if __name__ == "__main__":
    make_demo_dataset().to_csv("data/recrutement_demo.csv", index=False)

