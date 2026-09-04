"""Conservative column-role suggestions for guided audits."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class SchemaInference:
    """Suggested audit mapping with confidence scores and explicit caveats."""

    mode: str
    mapping: dict[str, str | None]
    value_suggestions: dict[str, Any]
    confidence: dict[str, float]
    reasons: dict[str, str]
    conditioning_candidates: tuple[str, ...]
    warnings: tuple[str, ...]

    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "mapping": self.mapping,
            "value_suggestions": self.value_suggestions,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "conditioning_candidates": list(self.conditioning_candidates),
            "warnings": list(self.warnings),
        }


_ALIASES: dict[str, tuple[str, ...]] = {
    "decision_attribute": (
        "decision",
        "outcome",
        "selection",
        "selected",
        "approved",
        "accepted",
        "hired",
        "target",
        "label",
        "prediction",
        "y_pred",
        "resultat",
        "result",
    ),
    "protected_attribute": (
        "gender",
        "genre",
        "sex",
        "sexe",
        "race",
        "ethnicity",
        "ethnie",
        "age_group",
        "age_band",
        "disability",
        "handicap",
        "religion",
        "nationality",
        "nationalite",
    ),
    "ai_recommendation_attribute": (
        "ai_recommendation",
        "model_recommendation",
        "recommendation_ai",
        "recommandation_ia",
        "ai_decision",
        "model_decision",
        "prediction",
        "y_pred",
    ),
    "human_decision_attribute": (
        "human_decision",
        "reviewer_decision",
        "decision_humaine",
        "initial_decision",
        "decision_initiale",
    ),
    "ground_truth_attribute": (
        "ground_truth",
        "truth",
        "actual_outcome",
        "observed_outcome",
        "verite_terrain",
        "y_true",
    ),
    "exposure_attribute": (
        "ai_visible",
        "ai_exposure",
        "recommendation_visible",
        "ia_visible",
        "treatment",
        "condition",
    ),
    "appeal_attribute": (
        "appeal",
        "appealed",
        "contest",
        "recourse",
        "recours",
        "contestation",
    ),
    "final_decision_attribute": (
        "final_decision",
        "decision_finale",
        "remedied_decision",
        "corrected_decision",
    ),
    "decision_timestamp_attribute": (
        "decision_timestamp",
        "decision_at",
        "initial_timestamp",
        "date_decision",
    ),
    "final_timestamp_attribute": (
        "final_timestamp",
        "final_at",
        "remedy_timestamp",
        "correction_at",
        "date_correction",
    ),
    "cluster_attribute": (
        "case_id",
        "subject_id",
        "person_id",
        "candidate_id",
        "application_id",
        "dossier_id",
        "id_cas",
    ),
}

_CONDITIONING_ALIASES = (
    "education",
    "degree",
    "diploma",
    "diplome",
    "qualification",
    "experience",
    "tenure",
    "anciennete",
    "income",
    "revenu",
    "employment_duration",
)

_POSITIVE_VALUES = (
    "1",
    "true",
    "yes",
    "oui",
    "positive",
    "favorable",
    "favourable",
    "approved",
    "accepted",
    "selected",
    "hired",
    "retenu",
    "admis",
)


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")


def _role_score(column: str, aliases: tuple[str, ...]) -> tuple[float, str]:
    normalized = _normalize(column)
    if normalized in aliases:
        return 1.0, f"nom exact reconnu: {column}"
    matches = [alias for alias in aliases if alias in normalized or normalized in alias]
    if matches:
        best = max(matches, key=len)
        return 0.72, f"nom proche du rôle '{best}'"
    return 0.0, "aucun indice lexical fiable"


def _best_column(
    data: pd.DataFrame,
    role: str,
    *,
    excluded: set[str] | None = None,
) -> tuple[str | None, float, str]:
    excluded = excluded or set()
    candidates: list[tuple[float, str, str]] = []
    for column in data.columns:
        if column in excluded:
            continue
        score, reason = _role_score(str(column), _ALIASES[role])
        unique = data[column].nunique(dropna=True)
        if role in {"decision_attribute", "human_decision_attribute", "ai_recommendation_attribute"}:
            if 2 <= unique <= 10:
                score = min(1.0, score + 0.08)
                reason += "; cardinalité compatible avec une décision"
        if role.endswith("timestamp_attribute") and pd.api.types.is_datetime64_any_dtype(data[column]):
            score = max(score, 0.82)
            reason += "; type date/heure détecté"
        if score:
            candidates.append((score, str(column), reason))
    if not candidates:
        return None, 0.0, "aucune suggestion sûre"
    score, column, reason = max(candidates, key=lambda item: (item[0], -list(data.columns).index(item[1])))
    return column, score, reason


def _positive_value(series: pd.Series) -> tuple[Any | None, float]:
    values = list(series.dropna().unique())
    if not values:
        return None, 0.0
    if pd.api.types.is_bool_dtype(series) and len(values) == 2:
        return True, 0.9
    by_name = {_normalize(value): value for value in values}
    for preferred in _POSITIVE_VALUES:
        if preferred in by_name:
            return by_name[preferred], 0.95
    numeric = pd.to_numeric(pd.Series(values), errors="coerce")
    if len(values) == 2 and numeric.notna().all() and 1 in set(numeric):
        return values[list(numeric).index(1)], 0.8
    return None, 0.0


def infer_audit_schema(data: pd.DataFrame, *, mode: str = "classic") -> SchemaInference:
    """Suggest column roles while leaving normative group choices to the researcher."""

    if mode not in {"classic", "oversight"}:
        raise ValueError("mode doit être 'classic' ou 'oversight'.")
    if data.empty or not len(data.columns):
        raise ValueError("Le jeu de données doit contenir des lignes et des colonnes.")
    if not all(isinstance(column, str) for column in data.columns):
        raise ValueError("Les noms de colonnes doivent être des chaînes de caractères.")

    roles = (
        ["decision_attribute", "protected_attribute"]
        if mode == "classic"
        else [
            "protected_attribute",
            "ai_recommendation_attribute",
            "human_decision_attribute",
            "ground_truth_attribute",
            "exposure_attribute",
            "appeal_attribute",
            "final_decision_attribute",
            "decision_timestamp_attribute",
            "final_timestamp_attribute",
            "cluster_attribute",
        ]
    )
    mapping: dict[str, str | None] = {}
    confidence: dict[str, float] = {}
    reasons: dict[str, str] = {}
    used: set[str] = set()
    for role in roles:
        column, score, reason = _best_column(data, role, excluded=used)
        if score < 0.6:
            column = None
        mapping[role] = column
        confidence[role] = score if column else 0.0
        reasons[role] = reason
        if column:
            used.add(column)

    decision_role = "decision_attribute" if mode == "classic" else "human_decision_attribute"
    decision = mapping.get(decision_role)
    favourable, favourable_confidence = _positive_value(data[decision]) if decision else (None, 0.0)
    value_suggestions = {"favourable_value": favourable}
    confidence["favourable_value"] = favourable_confidence

    conditioning: list[str] = []
    for column in data.columns:
        normalized = _normalize(column)
        if column not in used and any(alias in normalized for alias in _CONDITIONING_ALIASES):
            conditioning.append(str(column))

    warnings = [
        "Les suggestions reposent sur les noms et types de colonnes; elles doivent être vérifiées.",
        "Aucun groupe protégé, groupe de référence ou facteur légitime n'est choisi automatiquement.",
    ]
    if mapping.get("protected_attribute") is None:
        warnings.append("Aucun attribut protégé n'a été reconnu avec une confiance suffisante.")
    if decision is None:
        warnings.append("Aucune variable de décision n'a été reconnue avec une confiance suffisante.")
    if favourable is None:
        warnings.append("L'issue favorable doit être choisie explicitement.")

    return SchemaInference(
        mode=mode,
        mapping=mapping,
        value_suggestions=value_suggestions,
        confidence=confidence,
        reasons=reasons,
        conditioning_candidates=tuple(conditioning[:5]),
        warnings=tuple(warnings),
    )
