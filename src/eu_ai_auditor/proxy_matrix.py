"""Mixed-type association matrix for detecting potential proxy variables."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from .models import ProxyMatrixResult


def _cramers_v(x: pd.Series, y: pd.Series) -> float:
    table = pd.crosstab(x, y)
    if table.empty or min(table.shape) < 2:
        return 0.0
    chi2 = chi2_contingency(table, correction=False)[0]
    n = table.to_numpy().sum()
    phi2 = chi2 / n
    rows, cols = table.shape
    phi2_corrected = max(0.0, phi2 - ((cols - 1) * (rows - 1)) / max(n - 1, 1))
    rows_corrected = rows - ((rows - 1) ** 2) / max(n - 1, 1)
    cols_corrected = cols - ((cols - 1) ** 2) / max(n - 1, 1)
    denominator = min(cols_corrected - 1, rows_corrected - 1)
    return float(np.sqrt(phi2_corrected / denominator)) if denominator > 0 else 0.0


def _correlation_ratio(categories: pd.Series, values: pd.Series) -> float:
    codes, _ = pd.factorize(categories)
    numeric = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    valid = (codes >= 0) & np.isfinite(numeric)
    codes = codes[valid]
    numeric = numeric[valid]
    if numeric.size < 2 or np.isclose(np.var(numeric), 0):
        return 0.0
    overall = numeric.mean()
    numerator = 0.0
    for code in np.unique(codes):
        group = numeric[codes == code]
        numerator += len(group) * (group.mean() - overall) ** 2
    denominator = ((numeric - overall) ** 2).sum()
    return float(np.sqrt(numerator / denominator)) if denominator > 0 else 0.0


def association_score(left: pd.Series, right: pd.Series) -> tuple[float, str, int]:
    """Return an absolute association score, method name and complete-pair count."""

    pair = pd.concat([left, right], axis=1).dropna()
    if len(pair) < 3:
        return np.nan, "insufficient", len(pair)
    x, y = pair.iloc[:, 0], pair.iloc[:, 1]
    x_numeric = pd.api.types.is_numeric_dtype(x)
    y_numeric = pd.api.types.is_numeric_dtype(y)
    if x_numeric and y_numeric:
        if x.nunique() < 2 or y.nunique() < 2:
            return 0.0, "Pearson", len(pair)
        return float(abs(x.corr(y, method="pearson"))), "Pearson", len(pair)
    if not x_numeric and not y_numeric:
        return _cramers_v(x.astype("string"), y.astype("string")), "V de Cramér corrigé", len(pair)
    if x_numeric:
        return _correlation_ratio(y.astype("string"), x), "rapport de corrélation eta", len(pair)
    return _correlation_ratio(x.astype("string"), y), "rapport de corrélation eta", len(pair)


def calculate_proxy_matrix(
    data: pd.DataFrame,
    protected_attributes: Sequence[str],
    candidate_features: Sequence[str] | None = None,
    *,
    low_threshold: float = 0.10,
    high_threshold: float = 0.30,
    min_pairs: int = 20,
) -> ProxyMatrixResult:
    """Assess pairwise proxy risk between protected and non-protected columns."""

    protected = list(dict.fromkeys(protected_attributes))
    if not protected:
        raise ValueError("Sélectionnez au moins une variable protégée.")
    missing = [column for column in protected if column not in data]
    if missing:
        raise ValueError(f"Colonnes protégées absentes: {', '.join(missing)}")
    if not 0 <= low_threshold < high_threshold <= 1:
        raise ValueError("Les seuils doivent respecter 0 <= faible < haut <= 1.")
    if min_pairs < 3:
        raise ValueError("min_pairs doit être supérieur ou égal à 3.")

    if candidate_features is None:
        candidates = [column for column in data.columns if column not in protected]
    else:
        candidates = list(dict.fromkeys(candidate_features))
        missing = [column for column in candidates if column not in data]
        if missing:
            raise ValueError(f"Variables candidates absentes: {', '.join(missing)}")
        candidates = [column for column in candidates if column not in protected]
    if not candidates:
        raise ValueError("Aucune variable non protégée à analyser.")

    records: list[dict[str, object]] = []
    for feature in candidates:
        for protected_attribute in protected:
            score, method, n_pairs = association_score(data[feature], data[protected_attribute])
            if n_pairs < min_pairs or np.isnan(score):
                risk = "Données insuffisantes"
            elif score < low_threshold:
                risk = "Faible"
            elif score < high_threshold:
                risk = "Moyen"
            else:
                risk = "Haut"
            records.append(
                {
                    "feature": feature,
                    "protected_attribute": protected_attribute,
                    "score": score,
                    "method": method,
                    "n_pairs": n_pairs,
                    "risk": risk,
                }
            )
    scores = pd.DataFrame.from_records(records).sort_values(
        ["score", "feature"], ascending=[False, True], na_position="last"
    )
    matrix = scores.pivot(index="feature", columns="protected_attribute", values="score")
    methods = scores.pivot(index="feature", columns="protected_attribute", values="method")
    return ProxyMatrixResult(
        scores=scores.reset_index(drop=True),
        matrix=matrix,
        methods=methods,
        low_threshold=low_threshold,
        high_threshold=high_threshold,
    )

