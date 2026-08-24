"""Reusable Matplotlib figures for Streamlit and PDF reports."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from .models import CDDResult, ProxyMatrixResult, QuadrantResult, TradeoffResult

plt.switch_backend("Agg")

NAVY = "#132238"
TEAL = "#0F766E"
CORAL = "#D65A4A"
GOLD = "#D6A53A"
MIST = "#E8EEF2"


def proxy_heatmap(result: ProxyMatrixResult):
    matrix = result.matrix.fillna(0.0)
    width = max(6.5, 1.2 * len(matrix.columns) + 3)
    height = max(4.0, 0.45 * len(matrix.index) + 2)
    figure, axis = plt.subplots(figsize=(width, height))
    image = axis.imshow(matrix.to_numpy(), vmin=0, vmax=1, cmap="YlOrRd", aspect="auto")
    axis.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=25, ha="right")
    axis.set_yticks(range(len(matrix.index)), matrix.index)
    for row in range(len(matrix.index)):
        for column in range(len(matrix.columns)):
            score = matrix.iloc[row, column]
            color = "white" if score >= 0.55 else NAVY
            axis.text(column, row, f"{score:.2f}", ha="center", va="center", color=color, fontsize=8)
    axis.set_title("Risque de proxy - force d'association", color=NAVY, loc="left", weight="bold")
    axis.set_xlabel("Variables protégées")
    axis.set_ylabel("Variables candidates")
    figure.colorbar(image, ax=axis, fraction=0.025, pad=0.02)
    figure.tight_layout()
    return figure


def cdd_strata_chart(result: CDDResult, limit: int = 18):
    data = result.strata[result.strata["eligible"]].copy()
    data = data.reindex(data["gap_D_minus_A"].abs().sort_values(ascending=False).index).head(limit)
    labels = data.iloc[:, 0].astype(str) if len(result.conditioning_attributes) <= 1 else data[
        list(result.conditioning_attributes)
    ].astype(str).agg(" | ".join, axis=1)
    figure, axis = plt.subplots(figsize=(8, max(3.5, 0.38 * len(data) + 1.5)))
    colors = [CORAL if value > 0 else TEAL for value in data["gap_D_minus_A"]]
    axis.barh(labels, data["gap_D_minus_A"], color=colors)
    axis.axvline(0, color=NAVY, linewidth=1)
    axis.invert_yaxis()
    axis.set_xlabel("D_R - A_R")
    axis.set_title("Écart CDD par strate", color=NAVY, loc="left", weight="bold")
    axis.grid(axis="x", alpha=0.2)
    figure.tight_layout()
    return figure


def quadrant_chart(result: QuadrantResult):
    figure, axis = plt.subplots(figsize=(7.4, 5.2))
    x = result.features["weighted_mean_disparity"]
    y = result.features["maximum_disparity"]
    axis.axvspan(0, result.mean_threshold, color="#E8F3F1", alpha=0.85)
    axis.axvspan(result.mean_threshold, max(float(x.max()) * 1.2, result.mean_threshold * 2), color="#FFF3E6", alpha=0.65)
    axis.axhline(result.max_threshold, color=NAVY, linestyle="--", linewidth=1)
    axis.axvline(result.mean_threshold, color=NAVY, linestyle="--", linewidth=1)
    axis.scatter(x, y, s=90, color=CORAL, edgecolor="white", linewidth=1.2, zorder=3)
    for _, row in result.features.iterrows():
        axis.annotate(
            row["protected_attribute"],
            (row["weighted_mean_disparity"], row["maximum_disparity"]),
            xytext=(6, 6),
            textcoords="offset points",
            fontsize=9,
        )
    axis.set_xlim(left=0)
    axis.set_ylim(bottom=0)
    axis.set_xlabel("Disparité absolue moyenne pondérée")
    axis.set_ylabel("Disparité absolue maximale")
    axis.set_title("Quadrants d'impact des variables protégées", color=NAVY, loc="left", weight="bold")
    axis.grid(alpha=0.15)
    figure.tight_layout()
    return figure


def tradeoff_chart(result: TradeoffResult):
    figure, axis = plt.subplots(figsize=(7.4, 5.2))
    colors = {"Régression logistique": TEAL, "CART": CORAL}
    markers = {"Régression logistique": "o", "CART": "s"}
    for model_name, group in result.points.groupby("model"):
        axis.scatter(
            group["fairness_cost"],
            group["balanced_accuracy"],
            label=model_name,
            alpha=0.55,
            color=colors.get(model_name, GOLD),
            marker=markers.get(model_name, "o"),
        )
    frontier = result.points[result.points["pareto_efficient"]].sort_values("fairness_cost")
    axis.plot(
        frontier["fairness_cost"],
        frontier["balanced_accuracy"],
        color=NAVY,
        linewidth=1.6,
        marker="o",
        markersize=4,
        label="Frontière de Pareto",
    )
    axis.set_xlabel("Coût d'équité |CDD|")
    axis.set_ylabel("Exactitude équilibrée")
    axis.set_title("Performance et équité sur l'échantillon de test", color=NAVY, loc="left", weight="bold")
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    finite = result.points["fairness_cost"].replace([np.inf, -np.inf], np.nan).dropna()
    if not finite.empty:
        axis.set_xlim(left=max(0, float(finite.min()) - 0.01))
    figure.tight_layout()
    return figure
