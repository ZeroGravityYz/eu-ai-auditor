"""Generate an AI Act-oriented technical evidence report as a PDF."""

from __future__ import annotations

import hashlib
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .data_quality import profile_dataset
from .evidence import dataframe_sha256
from .models import CDDResult, ProxyMatrixResult, QuadrantResult, TradeoffResult
from .version import __version__
from .visuals import cdd_strata_chart, proxy_heatmap, quadrant_chart, tradeoff_chart

plt.switch_backend("Agg")

NAVY = colors.HexColor("#132238")
TEAL = colors.HexColor("#0F766E")
CORAL = colors.HexColor("#D65A4A")
GOLD = colors.HexColor("#D6A53A")
MIST = colors.HexColor("#E8EEF2")
PALE = colors.HexColor("#F6F8FA")
INK = colors.HexColor("#273443")
WHITE = colors.white


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=32,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=8 * mm,
        ),
        "cover_kicker": ParagraphStyle(
            "CoverKicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=TEAL,
            spaceAfter=3 * mm,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=NAVY,
            spaceBefore=4 * mm,
            spaceAfter=4 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=TEAL,
            spaceBefore=3 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=INK,
            spaceAfter=2.2 * mm,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=10,
            textColor=INK,
        ),
        "metric": ParagraphStyle(
            "Metric",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=INK,
            alignment=TA_CENTER,
        ),
        "warning": ParagraphStyle(
            "Warning",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8.5,
            leading=12,
            textColor=CORAL,
        ),
    }


def _p(value: Any, style: ParagraphStyle) -> Paragraph:
    text = str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return Paragraph(text, style)


def _format_percent(value: float | None) -> str:
    return "N/D" if value is None or pd.isna(value) else f"{value:.1%}"


def _dataframe_table(
    frame: pd.DataFrame,
    styles: dict[str, ParagraphStyle],
    *,
    headers: list[str] | None = None,
    widths: list[float] | None = None,
) -> Table:
    columns = list(frame.columns)
    header_values = headers or columns
    rows: list[list[Any]] = [[_p(value, styles["small"]) for value in header_values]]
    for _, row in frame.iterrows():
        rendered: list[Any] = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                value = "N/D" if pd.isna(value) else f"{value:.3f}"
            rendered.append(_p(value, styles["small"]))
        rows.append(rendered)
    table = Table(rows, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5DF")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def _figure_image(figure, width: float, height: float | None = None) -> Image:
    figure_width, figure_height = figure.get_size_inches()
    stream = BytesIO()
    figure.savefig(stream, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(figure)
    stream.seek(0)
    target_height = height or width * figure_height / figure_width
    maximum_height = 175 * mm
    if target_height > maximum_height:
        width *= maximum_height / target_height
        target_height = maximum_height
    image = Image(stream, width=width, height=target_height)
    image._source_stream = stream  # keep the in-memory image alive through document build
    return image


def _header_footer(canvas, document) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(MIST)
    canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
    canvas.setFillColor(NAVY)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(18 * mm, height - 11 * mm, "EU AI AUDITOR - DOSSIER DE PREUVES")
    canvas.setFillColor(colors.HexColor("#667788"))
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def _first_page(canvas, document) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setFillColor(TEAL)
    canvas.rect(0, 0, 8 * mm, A4[1], fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#667788"))
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 18 * mm, 10 * mm, "Document d'aide à l'audit - revue juridique requise")
    canvas.restoreState()


def generate_compliance_report(
    data: pd.DataFrame,
    cdd_result: CDDResult,
    proxy_result: ProxyMatrixResult,
    *,
    quadrant_result: QuadrantResult | None = None,
    tradeoff_result: TradeoffResult | None = None,
    metadata: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> bytes:
    """Build a PDF evidence pack supporting AI Act Articles 10, 11, 13 and 14.

    The document explicitly avoids certifying legal conformity. It records
    evidence, assumptions, gaps and reviewer actions for an accountable human
    assessment.
    """

    metadata = dict(metadata or {})
    protected = list(dict.fromkeys(metadata.get("protected_attributes", [cdd_result.protected_attribute])))
    quality = profile_dataset(data, protected)
    styles = _styles()
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=20 * mm,
        topMargin=21 * mm,
        bottomMargin=16 * mm,
        title=f"Rapport d'audit - {metadata.get('system_name', 'Système évalué')}",
        author=str(metadata.get("auditor", "EU AI Auditor")),
    )
    story: list[Any] = []
    assessment_date = str(metadata.get("assessment_date", date.today().isoformat()))
    system_name = str(metadata.get("system_name", "Système évalué"))
    data_digest = dataframe_sha256(data)
    fallback_audit_basis = "|".join(
        [
            data_digest,
            system_name,
            str(metadata.get("system_version", "À compléter")),
            cdd_result.protected_attribute,
            str(cdd_result.protected_value),
            cdd_result.decision_attribute,
            str(cdd_result.advantaged_value),
        ]
    )
    audit_id = str(
        metadata.get("audit_id")
        or "audit-" + hashlib.sha256(fallback_audit_basis.encode("utf-8")).hexdigest()[:16]
    )

    story.extend(
        [
            Spacer(1, 25 * mm),
            _p("EU AI AUDITOR", styles["cover_kicker"]),
            _p("Dossier de preuves pour l'audit des biais", styles["cover_title"]),
            _p(system_name, styles["h1"]),
            HRFlowable(width="100%", thickness=2, color=TEAL, spaceBefore=2 * mm, spaceAfter=8 * mm),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Fournisseur", metadata.get("provider_name", "À compléter")],
                        ["Version du système", metadata.get("system_version", "À compléter")],
                        ["Identifiant de l'audit", audit_id],
                        ["Version de l'outil", __version__],
                        ["Date de l'évaluation", assessment_date],
                        ["Responsable de l'audit", metadata.get("auditor", "À compléter")],
                        ["Empreinte des données", data_digest[:24] + "..."],
                    ],
                    columns=["Champ", "Valeur"],
                ),
                styles,
                widths=[43 * mm, 110 * mm],
            ),
            Spacer(1, 10 * mm),
            Table(
                [[_p(
                    "STATUT - Dossier technique partiel. Ce rapport ne constitue ni une certification, "
                    "ni un avis juridique, ni une décision sur l'existence d'une discrimination.",
                    styles["warning"],
                )]],
                colWidths=[153 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF3EE")),
                        ("BOX", (0, 0), (-1, -1), 0.8, CORAL),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            PageBreak(),
        ]
    )

    story.append(_p("1. Synthèse exécutive", styles["h1"]))
    metric_rows = [[
        _p(str(quality["rows"]), styles["metric"]),
        _p(_format_percent(cdd_result.gap), styles["metric"]),
        _p(str(int((proxy_result.scores["risk"] == "Haut").sum())), styles["metric"]),
        _p(_format_percent(cdd_result.coverage), styles["metric"]),
    ], [
        _p("Lignes analysées", styles["metric_label"]),
        _p("Écart CDD D_R - A_R", styles["metric_label"]),
        _p("Relations proxy à haut risque", styles["metric_label"]),
        _p("Couverture CDD", styles["metric_label"]),
    ]]
    metrics = Table(metric_rows, colWidths=[38 * mm] * 4)
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, MIST),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, MIST),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
            ]
        )
    )
    story.extend([metrics, Spacer(1, 5 * mm)])
    story.append(
        _p(
            f"Le moteur CDD signale: {cdd_result.status}. Une valeur positive signifie que la "
            f"classe protégée '{cdd_result.protected_value}' est proportionnellement plus présente dans "
            "les issues défavorables que dans les issues favorables, après conditionnement. L'ampleur, "
            "la causalité et la justification éventuelle doivent être appréciées dans leur contexte.",
            styles["body"],
        )
    )
    if cdd_result.confidence_low is not None and cdd_result.confidence_high is not None:
        if cdd_result.confidence_low > cdd_result.materiality_threshold:
            uncertainty_text = "L'intervalle bootstrap reste entièrement au-dessus du seuil interne."
        elif cdd_result.confidence_high <= cdd_result.materiality_threshold:
            uncertainty_text = "L'intervalle bootstrap reste sous le seuil interne."
        else:
            uncertainty_text = (
                "L'intervalle bootstrap recoupe le seuil interne: la classification de matérialité "
                "est incertaine."
            )
        story.append(_p(uncertainty_text, styles["body"]))
    if quality["warnings"]:
        story.append(_p("Points de vigilance", styles["h2"]))
        for warning in quality["warnings"][:8]:
            story.append(_p("- " + warning, styles["body"]))

    story.append(_p("2. Périmètre et traçabilité", styles["h1"]))
    scope_frame = pd.DataFrame(
        [
            ["Finalité prévue", metadata.get("intended_purpose", "À compléter")],
            ["Jeu analysé", f"{quality['rows']} lignes, {quality['columns_count']} colonnes"],
            ["Décision et issue favorable", f"{cdd_result.decision_attribute} = {cdd_result.advantaged_value}"],
            ["Classe protégée testée", f"{cdd_result.protected_attribute} = {cdd_result.protected_value}"],
            ["Facteurs de conditionnement R", ", ".join(cdd_result.conditioning_attributes) or "Aucun"],
            ["Origine des données", metadata.get("data_origin", "À compléter")],
            ["Licence des données", metadata.get("dataset_license", "À compléter")],
            ["Référence de source", metadata.get("source_reference", "À compléter")],
            ["Portée géographique", metadata.get("geographic_scope", "À compléter")],
        ],
        columns=["Élément", "Description"],
    )
    story.append(_dataframe_table(scope_frame, styles, widths=[50 * mm, 103 * mm]))
    story.append(
        _p(
            "La reproductibilité exige de conserver le fichier source, sa base juridique de traitement, "
            "le code de préparation des données, la configuration de l'audit et l'identité des valideurs "
            "dans un environnement à accès contrôlé.",
            styles["body"],
        )
    )

    story.append(_p("3. Article 10 - Données et gouvernance", styles["h1"]))
    story.append(
        _p(
            "Les indicateurs ci-dessous documentent la disponibilité, la complétude et la représentation. "
            "Ils ne suffisent pas à démontrer la pertinence au regard de la finalité, l'absence d'erreur, "
            "la couverture géographique ou la légalité du traitement de catégories particulières.",
            styles["body"],
        )
    )
    quality_frame = pd.DataFrame(
        [
            ["Taux global de valeurs manquantes", _format_percent(quality["overall_missing_rate"])],
            ["Lignes dupliquées", quality["duplicate_count"]],
            ["Variables protégées auditées", ", ".join(protected)],
            ["Lacunes documentées", metadata.get("data_gaps", "À compléter par le responsable des données")],
            ["Mesures de mitigation", metadata.get("bias_mitigation", "À compléter")],
        ],
        columns=["Contrôle", "Résultat"],
    )
    story.append(_dataframe_table(quality_frame, styles, widths=[58 * mm, 95 * mm]))
    representation = pd.DataFrame(quality["representation"])
    if not representation.empty:
        representation = representation[["protected_attribute", "group", "count", "share", "rare"]].head(20)
        representation["share"] = representation["share"].map(lambda value: f"{value:.1%}")
        representation["rare"] = representation["rare"].map({True: "À examiner", False: "Non"})
        story.extend(
            [
                _p("Représentation des groupes", styles["h2"]),
                _dataframe_table(
                    representation,
                    styles,
                    headers=["Attribut", "Groupe", "Effectif", "Part", "Rare"],
                    widths=[36 * mm, 42 * mm, 22 * mm, 22 * mm, 31 * mm],
                ),
            ]
        )

    story.append(PageBreak())
    story.append(_p("4. CDD - Disparité démographique conditionnelle", styles["h1"]))
    story.append(
        _p(
            "Pour chaque strate légitime R: A_R = P(S=classe protégée | issue favorable, R) et "
            "D_R = P(S=classe protégée | issue défavorable, R). L'agrégat est pondéré par la population "
            "de chaque strate. Une strate trop petite reste visible mais n'entre pas dans l'agrégat.",
            styles["body"],
        )
    )
    cdd_summary = pd.DataFrame(
        [
            ["A_R agrégé", _format_percent(cdd_result.advantaged_share)],
            ["D_R agrégé", _format_percent(cdd_result.disadvantaged_share)],
            ["D_R - A_R", _format_percent(cdd_result.gap)],
            [
                f"Intervalle bootstrap ({cdd_result.confidence_level:.0%})"
                if cdd_result.confidence_level
                else "Intervalle bootstrap",
                (
                    f"[{_format_percent(cdd_result.confidence_low)} ; "
                    f"{_format_percent(cdd_result.confidence_high)}]"
                    if cdd_result.confidence_low is not None
                    and cdd_result.confidence_high is not None
                    else "Non calculé"
                ),
            ],
            [
                "Réplications bootstrap valides",
                f"{cdd_result.bootstrap_valid_iterations}/{cdd_result.bootstrap_iterations}"
                if cdd_result.bootstrap_iterations
                else "Non demandées",
            ],
            ["Seuil de matérialité choisi", _format_percent(cdd_result.materiality_threshold)],
            ["Couverture", _format_percent(cdd_result.coverage)],
            ["Interprétation descriptive", cdd_result.status],
        ],
        columns=["Mesure", "Valeur"],
    )
    story.append(_dataframe_table(cdd_summary, styles, widths=[69 * mm, 84 * mm]))
    eligible = cdd_result.strata[cdd_result.strata["eligible"]]
    if not eligible.empty:
        story.extend([Spacer(1, 3 * mm), _figure_image(cdd_strata_chart(cdd_result), 150 * mm)])
        condition_columns = list(cdd_result.conditioning_attributes) or ["__population__"]
        top = eligible.reindex(eligible["gap_D_minus_A"].abs().sort_values(ascending=False).index).head(12)
        top = top[[*condition_columns, "n_total", "A_R", "D_R", "gap_D_minus_A"]]
        story.extend(
            [
                _p("Strates présentant les écarts absolus les plus élevés", styles["h2"]),
                _dataframe_table(top, styles),
            ]
        )
    for note in cdd_result.notes:
        story.append(_p("- " + note, styles["small"]))

    story.append(_p("5. Matrice des proxys", styles["h1"]))
    story.append(
        _p(
            "La matrice mesure une association, pas une causalité. Pearson est utilisé entre variables "
            "numériques, le V de Cramér corrigé entre variables catégorielles et eta pour les couples "
            "mixtes. Les seuils sont des paramètres de triage documentés, pas des seuils réglementaires.",
            styles["body"],
        )
    )
    story.append(_figure_image(proxy_heatmap(proxy_result), 150 * mm))
    top_proxy = proxy_result.scores.head(15)[
        ["feature", "protected_attribute", "score", "method", "n_pairs", "risk"]
    ]
    story.append(
        _dataframe_table(
            top_proxy,
            styles,
            headers=["Variable", "Attribut protégé", "Score", "Méthode", "Paires", "Risque"],
        )
    )

    if quadrant_result is not None:
        story.append(PageBreak())
        story.append(_p("6. Quadrants d'impact", styles["h1"]))
        story.append(
            _p(
                "L'écart de résultat d'un sous-groupe est son taux d'issue favorable moins le taux de la "
                "population. Les axes utilisent la moyenne absolue pondérée et le maximum absolu. Les "
                "seuils configurés servent à prioriser l'investigation.",
                styles["body"],
            )
        )
        story.append(_figure_image(quadrant_chart(quadrant_result), 145 * mm))
        quadrant_table = quadrant_result.features.copy()
        story.append(
            _dataframe_table(
                quadrant_table,
                styles,
                headers=["Attribut", "Moyenne", "Maximum", "Quadrant", "Groupes", "Lignes"],
            )
        )

    if tradeoff_result is not None:
        story.append(
            KeepTogether(
                [
                    _p("7. Arbitrage performance - équité", styles["h1"]),
                    _p(
                "Chaque point provient d'un échantillon de test distinct de l'entraînement. La frontière "
                "de Pareto montre les points qu'aucun autre point ne surpasse simultanément en exactitude "
                "équilibrée et en coût |CDD|. Elle ne choisit pas la pondération normative entre objectifs.",
                        styles["body"],
                    ),
                    _figure_image(tradeoff_chart(tradeoff_result), 145 * mm),
                ]
            )
        )
        pareto = tradeoff_result.points[tradeoff_result.points["pareto_efficient"]].head(12)
        pareto = pareto[
            ["model", "configuration", "threshold", "balanced_accuracy", "cdd_gap", "cdd_coverage"]
        ]
        story.append(
            _dataframe_table(
                pareto,
                styles,
                headers=["Modèle", "Configuration", "Seuil", "Exactitude", "CDD", "Couverture"],
            )
        )

    story.append(PageBreak())
    story.append(_p("8. Article 11 et annexe IV - État du dossier", styles["h1"]))
    checklist = [
        ("Description générale, finalité, fournisseur, version", ["system_name", "intended_purpose", "provider_name", "system_version"]),
        ("Architecture, composants, ressources et interfaces", ["architecture"]),
        ("Provenance, préparation et caractéristiques des données", ["data_origin", "data_preparation"]),
        ("Choix de conception et arbitrages documentés", ["design_choices", "tradeoff_rationale"]),
        ("Procédures et journaux de validation", ["validation_procedure"]),
        ("Mesures de supervision humaine", ["human_oversight"]),
        ("Mesures de cybersécurité", ["cybersecurity"]),
        ("Gestion des risques et risques résiduels", ["risk_management"]),
        ("Standards et spécifications appliqués", ["standards"]),
        ("Plan de suivi après mise sur le marché", ["post_market_monitoring"]),
    ]
    checklist_rows = []
    for item, fields in checklist:
        complete = all(str(metadata.get(field, "")).strip() for field in fields)
        checklist_rows.append([item, "Documenté" if complete else "À compléter", ", ".join(fields)])
    story.append(
        _dataframe_table(
            pd.DataFrame(checklist_rows, columns=["Élément annexe IV", "État", "Champs attendus"]),
            styles,
            widths=[77 * mm, 25 * mm, 51 * mm],
        )
    )
    story.append(
        _p(
            "Les métriques, tableaux et paramètres du présent rapport peuvent alimenter les parties "
            "données, essais, impacts potentiellement discriminatoires et limitations. Les éléments "
            "organisationnels manquants doivent être approuvés, datés et signés par les responsables.",
            styles["body"],
        )
    )

    story.append(_p("9. Article 13 - Transparence et instructions d'utilisation", styles["h1"]))
    transparency_rows = pd.DataFrame(
        [
            ["Finalité prévue", metadata.get("intended_purpose", "À compléter")],
            ["Utilisateurs visés", metadata.get("intended_users", "À compléter")],
            ["Capacités et limites", metadata.get("known_limitations", "Les résultats dépendent de la qualité, de la portée et des choix de groupes.")],
            ["Interprétation des sorties", "Lire CDD et les associations comme des signaux descriptifs; examiner les strates et la couverture."],
            ["Mauvais usages prévisibles", metadata.get("foreseeable_misuse", "Utiliser le rapport comme certification ou ignorer les sous-groupes peu représentés.")],
            ["Conservation des journaux", metadata.get("logging", "À compléter")],
        ],
        columns=["Instruction", "Contenu"],
    )
    story.append(_dataframe_table(transparency_rows, styles, widths=[52 * mm, 101 * mm]))

    story.append(_p("10. Article 14 - Supervision humaine", styles["h1"]))
    oversight = metadata.get("human_oversight", "À compléter: rôles, compétences, autorité et disponibilité du superviseur.")
    story.append(_p(str(oversight), styles["body"]))
    for action in [
        "Comprendre les capacités, limites, groupes concernés et conditions de validité.",
        "Surveiller les anomalies, dérives, écarts de couverture et biais d'automatisation.",
        "Pouvoir ignorer, annuler ou renverser une sortie individuelle documentée.",
        "Pouvoir interrompre le système et déclencher une escalade sûre.",
        "Consigner la décision humaine, la justification, les données consultées et l'action corrective.",
    ]:
        story.append(_p("- " + action, styles["body"]))

    story.append(PageBreak())
    story.append(_p("11. Annexe - Limites, références et validation", styles["h1"]))
    for limitation in [
        "CDD ne détermine ni l'illégalité d'un écart, ni sa justification, ni sa causalité.",
        "Les facteurs R et les groupes comparateurs impliquent des choix juridiques et contextuels.",
        "Une forte association de proxy n'établit pas qu'une variable est utilisée de façon discriminatoire.",
        "L'analyse ponctuelle doit être complétée par le suivi des dérives, incidents et effets réels.",
        "Le traitement de catégories particulières de données exige une base et des garanties adaptées.",
    ]:
        story.append(_p("- " + limitation, styles["body"]))
    references = [
        "Règlement (UE) 2024/1689, articles 10, 11, 13, 14 et annexe IV: https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
        "Wachter, Mittelstadt et Russell, Why Fairness Cannot Be Automated, 2020: https://arxiv.org/abs/2005.05906",
        "Deloitte, Striving for fairness in AI models, 2021: https://www.deloitte.com/content/dam/assets-zone2/de/de/docs/products/2024/Deloitte_Trustworthy20AI_Fairness_Whitepaper_Dec2021.pdf",
    ]
    for reference in references:
        story.append(_p(reference, styles["small"]))
    story.append(_p("Traçabilité de la validation", styles["h2"]))
    validation_frame = pd.DataFrame(
        [
            ["Responsable métier", metadata.get("business_owner", "À compléter"), "Date / signature"],
            ["Responsable données", metadata.get("data_owner", "À compléter"), "Date / signature"],
            ["Revue juridique", metadata.get("legal_reviewer", "À compléter"), "Date / signature"],
            ["Décision de mise en service", metadata.get("deployment_decision", "À compléter"), "Date / signature"],
        ],
        columns=["Rôle", "Nom ou décision", "Validation"],
    )
    story.append(
        _dataframe_table(
            validation_frame,
            styles,
            widths=[52 * mm, 61 * mm, 40 * mm],
        )
    )
    story.extend(
        [
            Spacer(1, 5 * mm),
            _p(
                "Conclusion de l'outil: les résultats constituent des signaux descriptifs et un dossier "
                "de travail. La décision finale doit être motivée, attribuée à une personne compétente "
                "et reliée aux mesures correctives ou au suivi retenu.",
                styles["body"],
            ),
            _p("Empreinte complète du jeu analysé", styles["h2"]),
            _p(data_digest, styles["small"]),
            _p("Identifiant stable de l'audit", styles["h2"]),
            _p(audit_id, styles["small"]),
            _p(
                "Un manifeste JSON séparé peut enregistrer cette empreinte, la configuration, les "
                "résultats, l'empreinte du PDF et une signature HMAC optionnelle. Toute modification "
                "ultérieure invalide la vérification d'intégrité.",
                styles["body"],
            ),
        ]
    )

    document.build(story, onFirstPage=_first_page, onLaterPages=_header_footer)
    pdf_bytes = stream.getvalue()
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pdf_bytes)
    return pdf_bytes
