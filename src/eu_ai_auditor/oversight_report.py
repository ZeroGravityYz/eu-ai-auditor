"""PDF evidence report for OversightParity process-fairness audits."""

from __future__ import annotations

import hashlib
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .evidence import dataframe_sha256
from .models import OversightResult
from .report_generator import (
    CORAL,
    MIST,
    PALE,
    TEAL,
    _dataframe_table,
    _figure_image,
    _first_page,
    _format_percent,
    _header_footer,
    _p,
    _styles,
)
from .version import __version__

plt.switch_backend("Agg")


def _metric_card_table(result: OversightResult, styles) -> Table:
    values = [
        _format_percent(result.metrics.get("ai_gap")),
        _format_percent(result.metrics.get("human_gap")),
        _format_percent(result.metrics.get("automation_bias_gap")),
        _format_percent(result.metrics.get("remedy_gap")),
    ]
    labels = ["Écart IA", "Écart décision humaine", "Écart d'influence IA", "Écart de correction"]
    table = Table(
        [
            [_p(value, styles["metric"]) for value in values],
            [_p(label, styles["metric_label"]) for label in labels],
        ],
        colWidths=[38 * mm] * 4,
    )
    table.setStyle(
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
    return table


def _process_chart(result: OversightResult):
    wanted = ["ai_favourable_rate", "human_favourable_rate", "final_favourable_rate"]
    frame = result.comparisons.set_index("metric").reindex(wanted).dropna(subset=["protected_rate"])
    figure, axis = plt.subplots(figsize=(8.2, 3.8))
    x = np.arange(len(frame))
    width = 0.34
    axis.bar(
        x - width / 2,
        frame["protected_rate"],
        width,
        label=str(result.protected_value),
        color="#D65A4A",
    )
    axis.bar(
        x + width / 2,
        frame["reference_rate"],
        width,
        label=str(result.reference_value),
        color="#0F766E",
    )
    axis.set_xticks(x, ["Recommandation IA", "Décision humaine", "Décision finale"][: len(frame)])
    axis.set_ylim(0, 1)
    axis.set_ylabel("Taux favorable standardisé")
    axis.legend(frameon=False, ncol=2, loc="upper center")
    axis.grid(axis="y", color="#DCE3E8", linewidth=0.7)
    axis.spines[["top", "right"]].set_visible(False)
    figure.tight_layout()
    return figure


def _gap_chart(result: OversightResult):
    frame = result.comparisons.dropna(subset=["gap"]).copy()
    frame = frame[~frame["metric"].isin(["override_rate"])]
    frame = frame.tail(8)
    figure, axis = plt.subplots(figsize=(8.2, 4.6))
    y = np.arange(len(frame))
    colors_list = ["#D65A4A" if abs(value) > result.materiality_threshold else "#0F766E" for value in frame["gap"]]
    axis.barh(y, frame["gap"], color=colors_list)
    axis.set_yticks(y, frame["label"])
    axis.axvline(0, color="#273443", linewidth=0.8)
    axis.axvline(result.materiality_threshold, color="#D6A53A", linestyle="--", linewidth=0.8)
    axis.axvline(-result.materiality_threshold, color="#D6A53A", linestyle="--", linewidth=0.8)
    axis.set_xlabel("Écart groupe protégé - groupe de référence")
    axis.grid(axis="x", color="#DCE3E8", linewidth=0.7)
    axis.spines[["top", "right", "left"]].set_visible(False)
    figure.tight_layout()
    return figure


def _interval_text(result: OversightResult, key: str) -> str:
    interval = result.intervals.get(key)
    if interval is None:
        return "Non calculé"
    return f"[{interval[0]:.1%} ; {interval[1]:.1%}]"


def generate_oversight_report(
    data: pd.DataFrame,
    result: OversightResult,
    *,
    metadata: dict[str, Any] | None = None,
    output_path: str | Path | None = None,
) -> bytes:
    """Build a technical evidence report for AI-human-remedy process fairness."""

    metadata = dict(metadata or {})
    styles = _styles()
    stream = BytesIO()
    system_name = str(metadata.get("system_name", "Système de décision assistée"))
    assessment_date = str(metadata.get("assessment_date", date.today().isoformat()))
    data_digest = dataframe_sha256(data)
    fallback_basis = "|".join(
        [
            data_digest,
            system_name,
            result.protected_attribute,
            str(result.protected_value),
            str(result.reference_value),
            result.ai_recommendation_attribute,
            result.human_decision_attribute,
        ]
    )
    audit_id = str(
        metadata.get("audit_id")
        or "oversight-" + hashlib.sha256(fallback_basis.encode("utf-8")).hexdigest()[:16]
    )
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=20 * mm,
        topMargin=21 * mm,
        bottomMargin=16 * mm,
        title=f"OversightParity - {system_name}",
        author=str(metadata.get("auditor", "EU AI Auditor")),
    )
    story: list[Any] = []

    story.extend(
        [
            Spacer(1, 24 * mm),
            _p("OVERSIGHTPARITY / EU AI AUDITOR", styles["cover_kicker"]),
            _p("Audit de la fairness de la décision réelle", styles["cover_title"]),
            _p(system_name, styles["h1"]),
            HRFlowable(width="100%", thickness=2, color=TEAL, spaceBefore=2 * mm, spaceAfter=8 * mm),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Organisation", metadata.get("provider_name", "À compléter")],
                        ["Version du système", metadata.get("system_version", "À compléter")],
                        ["Identifiant de l'audit", audit_id],
                        ["Version de l'outil", __version__],
                        ["Date", assessment_date],
                        ["Responsable", metadata.get("auditor", "À compléter")],
                        ["Empreinte des données", data_digest[:24] + "..."],
                    ],
                    columns=["Champ", "Valeur"],
                ),
                styles,
                widths=[43 * mm, 110 * mm],
            ),
            Spacer(1, 9 * mm),
            Table(
                [[_p(
                    "STATUT - Analyse statistique et procédurale. Ce rapport ne constitue ni une "
                    "certification de conformité, ni une preuve de causalité hors protocole randomisé, "
                    "ni une conclusion juridique sur une discrimination.",
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

    story.extend(
        [
            _p("1. Synthèse exécutive", styles["h1"]),
            _metric_card_table(result, styles),
            Spacer(1, 4 * mm),
            _p(f"Signal de l'outil: {result.status}.", styles["warning"]),
            _p(
                "Le signe d'un écart correspond au taux du groupe protégé moins celui du groupe de "
                "référence. Un écart négatif indique donc un taux inférieur pour le groupe protégé. "
                "L'analyse sépare ce qui provient du modèle, de l'intervention humaine et du recours.",
                styles["body"],
            ),
            _figure_image(_process_chart(result), 151 * mm),
            _p("Périmètre", styles["h2"]),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Groupe protégé", f"{result.protected_attribute} = {result.protected_value}"],
                        ["Groupe de référence", f"{result.protected_attribute} = {result.reference_value}"],
                        ["Issue favorable", result.favourable_value],
                        ["Facteurs légitimes R", ", ".join(result.conditioning_attributes) or "Aucun"],
                        ["Lignes incluses", f"{result.included_rows} ({result.coverage:.1%})"],
                    ],
                    columns=["Élément", "Valeur"],
                ),
                styles,
                widths=[52 * mm, 101 * mm],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("2. Transfert de fairness: IA vers décision humaine", styles["h1"]),
            _p(
                "Le transfert signé est l'écart humain moins l'écart IA. L'amplification utilise les "
                "valeurs absolues: une valeur positive signifie que la décision humaine éloigne davantage "
                "les groupes, quelle que soit la direction initiale.",
                styles["body"],
            ),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Écart favorable IA", _format_percent(result.metrics.get("ai_gap")), _interval_text(result, "ai_gap")],
                        ["Écart favorable humain", _format_percent(result.metrics.get("human_gap")), _interval_text(result, "human_gap")],
                        ["Transfert signé", _format_percent(result.metrics.get("fairness_transfer_signed")), _interval_text(result, "fairness_transfer_signed")],
                        ["Amplification absolue", _format_percent(result.metrics.get("disparity_amplification")), _interval_text(result, "disparity_amplification")],
                        ["Écart de concordance", _format_percent(result.metrics.get("agreement_gap")), _interval_text(result, "agreement_gap")],
                    ],
                    columns=["Mesure", "Estimation", "Intervalle bootstrap"],
                ),
                styles,
                widths=[69 * mm, 35 * mm, 49 * mm],
            ),
            _p("Correction des erreurs", styles["h2"]),
            _p(
                "Une correction utile est une erreur de l'IA que la décision humaine remet en accord avec "
                "la vérité terrain. Une erreur introduite est une recommandation correcte rendue incorrecte "
                "par l'intervention humaine. Ces mesures restent indisponibles sans vérité terrain.",
                styles["body"],
            ),
            _dataframe_table(
                result.comparisons[
                    result.comparisons["metric"].isin(
                        ["agreement_rate", "helpful_override_rate", "harmful_override_rate"]
                    )
                ][["label", "protected_rate", "reference_rate", "gap", "coverage"]],
                styles,
                headers=["Mesure", "Protégé", "Référence", "Écart", "Couverture"],
                widths=[62 * mm, 22 * mm, 24 * mm, 22 * mm, 23 * mm],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("3. Influence de la recommandation et automation bias", styles["h1"]),
            _p(result.causal_interpretation, styles["warning"]),
            _p(
                "L'effet d'exposition compare le taux de décision humaine favorable lorsque la recommandation "
                "IA est visible et lorsqu'elle ne l'est pas. L'écart d'influence est l'effet du groupe protégé "
                "moins celui du groupe de référence. Une randomisation valide autorise une lecture causale; "
                "sinon, les différences non observées peuvent expliquer le contraste.",
                styles["body"],
            ),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Effet d'exposition - groupe protégé", _format_percent(result.metrics.get("automation_effect_protected")), _interval_text(result, "automation_effect_protected")],
                        ["Effet d'exposition - référence", _format_percent(result.metrics.get("automation_effect_reference")), _interval_text(result, "automation_effect_reference")],
                        ["Causal Automation Bias Gap", _format_percent(result.metrics.get("automation_bias_gap")), _interval_text(result, "automation_bias_gap")],
                        ["Exposition déclarée randomisée", "Oui" if result.exposure_randomized else "Non", "Justification documentaire requise"],
                    ],
                    columns=["Mesure", "Estimation", "Incertitude / exigence"],
                ),
                styles,
                widths=[69 * mm, 35 * mm, 49 * mm],
            ),
            _p("Écarts procéduraux standardisés", styles["h2"]),
            _figure_image(_gap_chart(result), 150 * mm),
            PageBreak(),
        ]
    )

    remedy = result.comparisons[
        result.comparisons["metric"].isin(
            ["appeal_access_rate", "remedy_rate", "timely_remedy_rate", "final_favourable_rate"]
        )
    ][["label", "protected_rate", "reference_rate", "gap", "coverage"]]
    story.extend(
        [
            _p("4. Contestation, correction et délai", styles["h1"]),
            _p(
                "Les dénominateurs incluent toutes les décisions humaines initialement défavorables, pas "
                "seulement les personnes ayant introduit un recours. Cette règle évite de masquer une "
                "inégalité d'accès au mécanisme de contestation.",
                styles["body"],
            ),
        ]
    )
    if remedy.empty or result.appeal_attribute is None:
        story.append(
            _p(
                "Données de recours absentes ou incomplètes. Il est impossible d'évaluer l'accès au recours, "
                "la correction effective et le délai. Cette absence constitue une lacune de preuve.",
                styles["warning"],
            )
        )
    else:
        story.append(
            _dataframe_table(
                remedy,
                styles,
                headers=["Mesure", "Protégé", "Référence", "Écart", "Couverture"],
                widths=[62 * mm, 22 * mm, 24 * mm, 22 * mm, 23 * mm],
            )
        )

    group_labels = {
        "protected": "Protégé",
        "reference": "Référence",
    }
    group_decisions = result.group_metrics[
        [
            "group_role",
            "group_value",
            "rows",
            "ai_favourable_rate",
            "human_favourable_rate",
            "final_favourable_rate",
        ]
    ].copy()
    group_decisions["group_role"] = group_decisions["group_role"].replace(group_labels)
    group_process = result.group_metrics[
        [
            "group_value",
            "agreement_rate",
            "helpful_override_rate",
            "appeal_access_rate",
            "remedy_rate",
            "timely_remedy_rate",
        ]
    ].copy()
    story.extend(
        [
            _p("Lecture éthique", styles["h2"]),
            _p(
                "Une procédure peut satisfaire une parité de sortie tout en restant injuste si certains "
                "groupes disposent de moins d'information, rencontrent davantage de friction pour contester "
                "ou attendent plus longtemps une correction. OversightParity sépare donc justice distributive, "
                "justice procédurale et réparation.",
                styles["body"],
            ),
            _p("Résultats détaillés par groupe", styles["h2"]),
            _dataframe_table(
                group_decisions,
                styles,
                headers=["Rôle", "Groupe", "n", "Taux IA", "Taux humain", "Taux final"],
                widths=[25 * mm, 26 * mm, 14 * mm, 27 * mm, 30 * mm, 27 * mm],
            ),
            Spacer(1, 3 * mm),
            _dataframe_table(
                group_process,
                styles,
                headers=["Groupe", "Concordance", "Correction utile", "Accès recours", "Correction", "Dans le délai"],
                widths=[25 * mm, 27 * mm, 31 * mm, 27 * mm, 23 * mm, 26 * mm],
            ),
            PageBreak(),
        ]
    )

    story.extend(
        [
            _p("5. AI Act: preuves pour le contrôle humain", styles["h1"]),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Article 12 - journaux", "Chaîner recommandation, exposition, décision humaine, recours, correction et horodatages.", "Vérifier exhaustivité, accès, conservation et protection."],
                        ["Article 13 - transparence", "Documenter la place de l'IA et les principaux éléments de la décision.", "Adapter l'information aux personnes concernées."],
                        ["Article 14 - contrôle humain", "Mesurer concordance, corrections utiles, erreurs introduites et influence de l'IA.", "Prouver compétence, autorité et possibilité réelle d'override."],
                        ["Article 86 - explication", "Relier l'explication au rôle effectif de l'IA dans la décision.", "Organiser la réponse individuelle et les autres voies de recours applicables."],
                    ],
                    columns=["Référence", "Preuve produite", "Travail humain restant"],
                ),
                styles,
                widths=[32 * mm, 61 * mm, 60 * mm],
            ),
            _p("Schéma minimal du journal", styles["h2"]),
            _p(
                "case_id, attribut protégé, facteurs R, recommandation IA, exposition à la recommandation, "
                "décision humaine initiale, vérité terrain lorsque disponible, recours, décision finale, "
                "horodatages, identifiant du réviseur et justification structurée.",
                styles["body"],
            ),
            _p("Actions prioritaires", styles["h2"]),
        ]
    )
    for action in [
        "Documenter le protocole d'affectation à l'exposition et vérifier la randomisation avant toute conclusion causale.",
        "Investiguer les réviseurs, unités ou périodes contribuant aux écarts sans publier de classement individuel non validé.",
        "Tester l'accessibilité du recours auprès des groupes concernés et mesurer les abandons avant dépôt.",
        "Relier chaque action corrective à un responsable, une échéance et une preuve de revalidation.",
    ]:
        story.append(_p("- " + action, styles["body"]))

    story.extend(
        [
            PageBreak(),
            _p("6. Méthode, limites et validation", styles["h1"]),
            _p(
                "Les taux sont calculés dans les strates communes définies par R puis standardisés sur la "
                "distribution groupée des observations éligibles. Les strates ne contenant pas l'effectif "
                "minimal dans les deux groupes sont exclues. Le bootstrap rééchantillonne les lignes ou, "
                "si configuré, les cas complets afin de préserver les bras d'une expérience appariée.",
                styles["body"],
            ),
        ]
    )
    for note in result.notes:
        story.append(_p("- " + note, styles["small"]))
    limitations = [
        "Une vérité terrain observée peut elle-même refléter des biais historiques ou de mesure.",
        "Une absence d'écart détecté ne démontre ni l'équité individuelle ni l'absence de discrimination intersectionnelle.",
        "Les recours observés dépendent de l'information, du coût, du temps et de la capacité des personnes à agir.",
        "Une exposition non randomisée ne permet pas d'attribuer causalement un écart à la recommandation IA.",
        "Les seuils de matérialité sont des paramètres de triage et non des seuils juridiques.",
    ]
    story.append(_p("Limites essentielles", styles["h2"]))
    for limitation in limitations:
        story.append(_p("- " + limitation, styles["body"]))
    story.extend(
        [
            _p("Validation et responsabilités", styles["h2"]),
            _dataframe_table(
                pd.DataFrame(
                    [
                        ["Responsable métier", metadata.get("business_owner", "À compléter"), "Date / signature"],
                        ["Responsable données", metadata.get("data_owner", "À compléter"), "Date / signature"],
                        ["Revue éthique / juridique", metadata.get("legal_reviewer", "À compléter"), "Date / signature"],
                        ["Décision corrective", metadata.get("remediation_decision", "À compléter"), "Date / signature"],
                    ],
                    columns=["Rôle", "Nom ou décision", "Validation"],
                ),
                styles,
                widths=[52 * mm, 61 * mm, 40 * mm],
            ),
            Spacer(1, 5 * mm),
            _p("Empreinte complète du journal", styles["h2"]),
            _p(data_digest, styles["small"]),
            _p("Identifiant stable de l'audit", styles["h2"]),
            _p(audit_id, styles["small"]),
            _p(
                "Le manifeste JSON associé lie cette configuration, les métriques et l'empreinte du PDF. "
                "Il détecte une modification mais ne remplace pas une signature qualifiée ni un système "
                "d'identité organisationnelle.",
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
