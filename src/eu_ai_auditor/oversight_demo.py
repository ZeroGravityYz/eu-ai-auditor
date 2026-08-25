"""Deterministic synthetic process log for the OversightParity interface."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _sigmoid(value: np.ndarray) -> np.ndarray:
    return 1 / (1 + np.exp(-value))


def make_oversight_demo(rows: int = 800, random_state: int = 73) -> pd.DataFrame:
    """Create an explicitly synthetic AI-human-appeal decision chain.

    The exposure to the AI recommendation is randomized. The process is built
    to demonstrate three audit signals: a mildly biased recommendation, unequal
    reliance on that recommendation and unequal access to effective remedy.
    It must never be represented as observations about a real organisation.
    """

    if rows < 100:
        raise ValueError("La démonstration OversightParity requiert au moins 100 lignes.")
    rng = np.random.default_rng(random_state)
    gender = rng.choice(["Femme", "Homme"], size=rows, p=[0.49, 0.51])
    diploma = rng.choice(["Bac+2", "Licence", "Master"], size=rows, p=[0.31, 0.39, 0.30])
    experience = np.clip(rng.gamma(2.3, 2.6, size=rows), 0, 18).round(1)
    diploma_score = pd.Series(diploma).map({"Bac+2": -0.35, "Licence": 0.15, "Master": 0.62}).to_numpy()
    latent_merit = diploma_score + 0.11 * experience + rng.normal(0, 0.72, size=rows) - 0.35

    truth_positive = rng.random(rows) < _sigmoid(latent_merit)
    ai_score = latent_merit + rng.normal(0, 0.55, size=rows) - np.where(gender == "Femme", 0.45, 0.00)
    ai_positive = ai_score > 0

    ai_visible = rng.random(rows) < 0.5
    unaided_probability = _sigmoid(
        latent_merit + rng.normal(0, 0.48, size=rows) - np.where(gender == "Femme", 0.05, 0)
    )
    reliance = np.where(gender == "Femme", 0.85, 0.50)
    aided_probability = (1 - reliance) * unaided_probability + reliance * ai_positive.astype(float)
    human_probability = np.where(ai_visible, aided_probability, unaided_probability)
    human_positive = rng.random(rows) < human_probability

    adverse = ~human_positive
    appeal_probability = np.where(gender == "Femme", 0.18, 0.55) + np.where(truth_positive, 0.18, 0)
    appealed = adverse & (rng.random(rows) < appeal_probability)
    reversal_probability = np.where(
        truth_positive,
        np.where(gender == "Femme", 0.45, 0.85),
        0.06,
    )
    reversed_decision = appealed & (rng.random(rows) < reversal_probability)
    final_positive = human_positive | reversed_decision

    start = pd.Timestamp("2026-01-01") + pd.to_timedelta(rng.integers(0, 120, size=rows), unit="D")
    remedy_delay = rng.integers(5, 46, size=rows)
    final_time = pd.Series(pd.NaT, index=range(rows), dtype="datetime64[ns]")
    final_time.loc[appealed] = start[appealed] + pd.to_timedelta(remedy_delay[appealed], unit="D")

    return pd.DataFrame(
        {
            "case_id": [f"SYN-{index + 1:05d}" for index in range(rows)],
            "genre": gender,
            "diplome": diploma,
            "anciennete_annees": experience,
            "verite_terrain": np.where(truth_positive, "Favorable", "Défavorable"),
            "recommandation_ia": np.where(ai_positive, "Favorable", "Défavorable"),
            "ia_visible": np.where(ai_visible, "Visible", "Masquée"),
            "decision_humaine": np.where(human_positive, "Favorable", "Défavorable"),
            "recours": np.where(appealed, "Oui", "Non"),
            "decision_finale": np.where(final_positive, "Favorable", "Défavorable"),
            "decision_at": start.strftime("%Y-%m-%d"),
            "final_at": final_time.dt.strftime("%Y-%m-%d"),
            "reviewer_id": [f"R-{value:02d}" for value in rng.integers(1, 31, size=rows)],
            "synthetic": True,
        }
    )
