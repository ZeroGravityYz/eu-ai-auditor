"""Performance versus fairness operating-point comparison for LR and CART."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

from .cdd_engine import calculate_cdd
from .models import TradeoffResult


def _encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:  # scikit-learn < 1.2
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def _preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    numeric = list(features.select_dtypes(include=["number", "bool"]).columns)
    categorical = [column for column in features.columns if column not in numeric]
    transformers: list[tuple[str, Pipeline, list[str]]] = []
    if numeric:
        transformers.append(
            (
                "numeric",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                numeric,
            )
        )
    if categorical:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", _encoder()),
                    ]
                ),
                categorical,
            )
        )
    return ColumnTransformer(transformers=transformers, remainder="drop")


def _pareto_mask(performance: np.ndarray, fairness_cost: np.ndarray) -> np.ndarray:
    mask = np.zeros(len(performance), dtype=bool)
    valid = np.isfinite(performance) & np.isfinite(fairness_cost)
    for index in np.flatnonzero(valid):
        dominated = np.any(
            valid
            & (performance >= performance[index])
            & (fairness_cost <= fairness_cost[index])
            & ((performance > performance[index]) | (fairness_cost < fairness_cost[index]))
        )
        mask[index] = not dominated
    return mask


def compare_models(
    data: pd.DataFrame,
    target_attribute: str,
    favourable_value: Any,
    protected_attribute: str,
    protected_value: Any,
    conditioning_attributes: Sequence[str] = (),
    *,
    exclude_features: Sequence[str] = (),
    test_size: float = 0.30,
    random_state: int = 42,
    thresholds: Sequence[float] = (0.30, 0.40, 0.50, 0.60, 0.70),
    logistic_c_values: Sequence[float] = (0.1, 1.0, 10.0),
    tree_depths: Sequence[int | None] = (2, 3, 4, 6, None),
) -> TradeoffResult:
    """Train LR/CART models and expose their Pareto-efficient operating points.

    Protected attributes are excluded from model inputs by default. CDD is
    calculated on held-out predictions, using the selected legitimate
    conditioning attributes.
    """

    conditioning = list(dict.fromkeys(conditioning_attributes))
    required = [target_attribute, protected_attribute, *conditioning]
    missing = [column for column in required if column not in data]
    if missing:
        raise ValueError(f"Colonnes absentes: {', '.join(missing)}")
    if not 0.1 <= test_size <= 0.5:
        raise ValueError("test_size doit être compris entre 0,1 et 0,5.")
    if len(data) < 80:
        raise ValueError("Au moins 80 lignes sont nécessaires pour la comparaison de modèles.")

    working = data.reset_index(drop=True).copy()
    target_valid = working[target_attribute].notna()
    working = working[target_valid].reset_index(drop=True)
    if favourable_value not in set(working[target_attribute].unique()):
        raise ValueError("L'issue favorable est absente de la cible.")
    y = working[target_attribute].eq(favourable_value).astype(int)
    if y.nunique() != 2 or y.value_counts().min() < 10:
        raise ValueError("La cible doit avoir deux classes avec au moins 10 observations chacune.")

    excluded = set(exclude_features) | {target_attribute, protected_attribute}
    feature_columns = [column for column in working.columns if column not in excluded]
    if not feature_columns:
        raise ValueError("Aucune variable explicative disponible après exclusions.")
    x = working[feature_columns]
    indices = np.arange(len(working))
    train_idx, test_idx = train_test_split(
        indices,
        test_size=test_size,
        random_state=random_state,
        stratify=y,
    )
    x_train, x_test = x.iloc[train_idx], x.iloc[test_idx]
    y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

    model_specs: list[tuple[str, str, object]] = []
    for c_value in logistic_c_values:
        model_specs.append(
            (
                "Régression logistique",
                f"C={c_value:g}",
                LogisticRegression(C=c_value, max_iter=1500, random_state=random_state),
            )
        )
    min_leaf = max(5, int(len(train_idx) * 0.01))
    for depth in tree_depths:
        label = "profondeur=illimitée" if depth is None else f"profondeur={depth}"
        model_specs.append(
            (
                "CART",
                label,
                DecisionTreeClassifier(
                    max_depth=depth,
                    min_samples_leaf=min_leaf,
                    random_state=random_state,
                    class_weight="balanced",
                ),
            )
        )

    records: list[dict[str, object]] = []
    audit_columns = [protected_attribute, *conditioning]
    audit_test = working.iloc[test_idx][audit_columns].reset_index(drop=True)
    for model_name, configuration, estimator in model_specs:
        pipeline = Pipeline([("preprocessor", _preprocessor(x_train)), ("model", estimator)])
        pipeline.fit(x_train, y_train)
        probabilities = pipeline.predict_proba(x_test)[:, 1]
        for threshold in thresholds:
            predictions = (probabilities >= threshold).astype(int)
            cdd_gap = np.nan
            cdd_coverage = 0.0
            if np.unique(predictions).size == 2:
                prediction_frame = audit_test.copy()
                prediction_frame["__prediction__"] = predictions
                try:
                    cdd_result = calculate_cdd(
                        prediction_frame,
                        protected_attribute=protected_attribute,
                        protected_value=protected_value,
                        decision_attribute="__prediction__",
                        advantaged_value=1,
                        conditioning_attributes=conditioning,
                        min_outcome_count=2,
                    )
                    cdd_gap = cdd_result.gap if cdd_result.gap is not None else np.nan
                    cdd_coverage = cdd_result.coverage
                except ValueError:
                    pass
            records.append(
                {
                    "model": model_name,
                    "configuration": configuration,
                    "threshold": float(threshold),
                    "accuracy": float(accuracy_score(y_test, predictions)),
                    "balanced_accuracy": float(balanced_accuracy_score(y_test, predictions)),
                    "f1": float(f1_score(y_test, predictions, zero_division=0)),
                    "cdd_gap": cdd_gap,
                    "fairness_cost": abs(cdd_gap) if np.isfinite(cdd_gap) else np.nan,
                    "cdd_coverage": cdd_coverage,
                    "positive_prediction_rate": float(predictions.mean()),
                }
            )

    points = pd.DataFrame.from_records(records)
    points["pareto_efficient"] = _pareto_mask(
        points["balanced_accuracy"].to_numpy(), points["fairness_cost"].to_numpy()
    )
    points = points.sort_values(
        ["pareto_efficient", "balanced_accuracy", "fairness_cost"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    return TradeoffResult(
        points=points,
        train_rows=len(train_idx),
        test_rows=len(test_idx),
        excluded_features=tuple(sorted(excluded)),
        random_state=random_state,
    )

