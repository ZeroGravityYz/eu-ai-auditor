"""Streamlit page for fairness of AI-assisted human decision processes."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import streamlit as st

from eu_ai_auditor import (
    build_oversight_evidence_bundle,
    build_research_crate,
    calculate_oversight_parity,
    infer_audit_schema,
    read_csv_flexible,
)
from eu_ai_auditor.oversight_demo import make_oversight_demo
from eu_ai_auditor.oversight_report import generate_oversight_report
from eu_ai_auditor.serialization import json_compatible

st.set_page_config(page_title="OversightParity", page_icon="⚖️", layout="wide")

st.markdown(
    """
    <style>
    .stApp {background: linear-gradient(180deg, #f6f8fa 0%, #ffffff 38%);}
    [data-testid="stMetric"] {background:#ffffff;border:1px solid #dce3e8;border-radius:12px;padding:12px;}
    [data-testid="stSidebar"] {background:#132238;}
    [data-testid="stSidebar"] * {color:#eef4f6;}
    .oversight-kicker {color:#0f766e;font-weight:750;letter-spacing:.08em;text-transform:uppercase;}
    .oversight-chain {padding:14px 18px;border-left:4px solid #0f766e;background:#edf7f5;border-radius:6px;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _read_csv(uploaded) -> pd.DataFrame:
    return read_csv_flexible(uploaded.getvalue())


def _values(series: pd.Series) -> list[Any]:
    return list(series.dropna().unique())


def _default_index(options: list[str], preferred: str) -> int:
    return options.index(preferred) if preferred in options else 0


def _optional_column(label: str, columns: list[str], preferred: str) -> str | None:
    options = ["— Aucun —", *columns]
    selected = st.selectbox(label, options, index=_default_index(options, preferred))
    return None if selected == "— Aucun —" else selected


st.markdown('<div class="oversight-kicker">Fairness après le modèle</div>', unsafe_allow_html=True)
st.title("OversightParity")
st.markdown(
    """
    <div class="oversight-chain">
    <strong>Recommandation IA</strong> → décision humaine → recours → correction effective.<br>
    L'objectif est de détecter où une disparité apparaît, s'amplifie ou résiste à la supervision.
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("1. Journal de décisions")
    uploaded = st.file_uploader("Déposer un CSV de processus", type=["csv"])
    use_demo = st.toggle("Utiliser la démonstration synthétique", value=uploaded is None)
    st.caption("Le traitement reste local à la session Streamlit.")

if uploaded is not None and not use_demo:
    try:
        dataset = _read_csv(uploaded)
    except Exception as exc:
        st.error(f"Lecture impossible: {exc}")
        st.stop()
elif use_demo:
    dataset = make_oversight_demo()
    st.warning(
        "Démonstration entièrement synthétique: elle illustre volontairement des inégalités de recours. "
        "Elle ne décrit aucune organisation réelle."
    )
else:
    st.info("Déposez un journal CSV ou activez la démonstration.")
    st.stop()

if dataset.empty or len(dataset.columns) < 4:
    st.error("Le journal doit contenir des lignes et au moins quatre colonnes.")
    st.stop()

columns = list(dataset.columns)
schema_suggestion = infer_audit_schema(dataset, mode="oversight")
with st.sidebar:
    st.header("2. Chaîne décisionnelle")
    protected_attribute = st.selectbox(
        "Attribut protégé",
        columns,
        index=_default_index(
            columns,
            schema_suggestion.mapping.get("protected_attribute") or "genre",
        ),
    )
    protected_values = _values(dataset[protected_attribute])
    if len(protected_values) < 2:
        st.error("L'attribut protégé doit contenir au moins deux groupes.")
        st.stop()
    protected_value = st.selectbox(
        "Groupe protégé",
        protected_values,
        index=protected_values.index("Femme") if "Femme" in protected_values else 0,
    )
    reference_options = [value for value in protected_values if value != protected_value]
    reference_value = st.selectbox(
        "Groupe de référence",
        reference_options,
        index=reference_options.index("Homme") if "Homme" in reference_options else 0,
    )
    ai_column = st.selectbox(
        "Recommandation IA",
        columns,
        index=_default_index(
            columns,
            schema_suggestion.mapping.get("ai_recommendation_attribute") or "recommandation_ia",
        ),
    )
    human_column = st.selectbox(
        "Décision humaine initiale",
        columns,
        index=_default_index(
            columns,
            schema_suggestion.mapping.get("human_decision_attribute") or "decision_humaine",
        ),
    )
    favourable_values = _values(dataset[human_column])
    favourable_value = st.selectbox(
        "Issue favorable",
        favourable_values,
        index=(
            favourable_values.index(schema_suggestion.value_suggestions["favourable_value"])
            if schema_suggestion.value_suggestions["favourable_value"] in favourable_values
            else favourable_values.index("Favorable")
            if "Favorable" in favourable_values
            else 0
        ),
    )
    forbidden = {protected_attribute, ai_column, human_column}
    conditioning = st.multiselect(
        "Facteurs légitimes R",
        [column for column in columns if column not in forbidden],
        default=(
            [column for column in ["diplome", "anciennete_annees"] if column in columns]
            if use_demo
            else [
                column
                for column in schema_suggestion.conditioning_candidates
                if column in columns and column not in forbidden
            ]
        ),
    )

    st.header("3. Étapes optionnelles")
    ground_truth = _optional_column(
        "Vérité terrain",
        columns,
        schema_suggestion.mapping.get("ground_truth_attribute") or "verite_terrain",
    )
    exposure = _optional_column(
        "Exposition à la recommandation",
        columns,
        schema_suggestion.mapping.get("exposure_attribute") or "ia_visible",
    )
    exposed_value = unexposed_value = None
    if exposure:
        exposure_values = _values(dataset[exposure])
        exposed_value = st.selectbox(
            "Valeur exposée",
            exposure_values,
            index=exposure_values.index("Visible") if "Visible" in exposure_values else 0,
        )
        remaining_exposure = [value for value in exposure_values if value != exposed_value]
        if not remaining_exposure:
            st.error("La variable d'exposition doit avoir deux valeurs.")
            st.stop()
        unexposed_value = st.selectbox(
            "Valeur non exposée",
            remaining_exposure,
            index=remaining_exposure.index("Masquée") if "Masquée" in remaining_exposure else 0,
        )
    exposure_randomized = st.checkbox(
        "Exposition randomisée et protocole documenté",
        value=bool(use_demo and exposure),
        help="Cochez uniquement si l'affectation à la visibilité de l'IA a réellement été randomisée.",
    )
    appeal = _optional_column(
        "Recours / contestation",
        columns,
        schema_suggestion.mapping.get("appeal_attribute") or "recours",
    )
    appeal_value = None
    if appeal:
        appeal_values = _values(dataset[appeal])
        appeal_value = st.selectbox(
            "Valeur indiquant un recours",
            appeal_values,
            index=appeal_values.index("Oui") if "Oui" in appeal_values else 0,
        )
    final_decision = _optional_column(
        "Décision finale",
        columns,
        schema_suggestion.mapping.get("final_decision_attribute") or "decision_finale",
    )
    decision_timestamp = _optional_column(
        "Horodatage initial",
        columns,
        schema_suggestion.mapping.get("decision_timestamp_attribute") or "decision_at",
    )
    final_timestamp = _optional_column(
        "Horodatage final",
        columns,
        schema_suggestion.mapping.get("final_timestamp_attribute") or "final_at",
    )
    cluster = _optional_column(
        "Identifiant de cas pour le bootstrap",
        columns,
        schema_suggestion.mapping.get("cluster_attribute") or "case_id",
    )

    with st.expander("Seuils et incertitude"):
        remedy_sla_days = st.number_input("Délai cible de correction (jours)", 1, 365, 30)
        min_group_count = st.number_input("Minimum par groupe et strate", 1, 100, 5)
        materiality = st.slider("Seuil d'investigation", 0.0, 0.30, 0.05, 0.01)
        bootstrap_iterations = st.select_slider(
            "Réplications bootstrap", options=[0, 100, 250, 500], value=100
        )
        confidence_level = st.select_slider(
            "Niveau de confiance", options=[0.90, 0.95, 0.99], value=0.95
        )
    with st.expander("Configuration automatique"):
        for role, column in schema_suggestion.mapping.items():
            if column:
                st.caption(f"{role}: {column} ({schema_suggestion.confidence[role]:.0%})")
        st.caption("Suggestions lexicales uniquement; vérifiez la sémantique et le protocole.")
    run_audit = st.button("Auditer la décision réelle", type="primary", width="stretch")

st.caption(f"Journal chargé: {len(dataset):,} événements × {len(dataset.columns)} colonnes")
with st.expander("Aperçu du journal"):
    st.dataframe(dataset.head(100), width="stretch", hide_index=True)

signature = (
    protected_attribute,
    str(protected_value),
    str(reference_value),
    ai_column,
    human_column,
    str(favourable_value),
    tuple(conditioning),
    ground_truth,
    exposure,
    str(exposed_value),
    str(unexposed_value),
    exposure_randomized,
    appeal,
    str(appeal_value),
    final_decision,
    decision_timestamp,
    final_timestamp,
    cluster,
    float(remedy_sla_days),
    int(min_group_count),
    float(materiality),
    int(bootstrap_iterations),
    float(confidence_level),
)

if run_audit:
    try:
        with st.spinner("Reconstruction de la chaîne IA → humain → recours..."):
            result = calculate_oversight_parity(
                dataset,
                protected_attribute=protected_attribute,
                protected_value=protected_value,
                reference_value=reference_value,
                ai_recommendation_attribute=ai_column,
                human_decision_attribute=human_column,
                favourable_value=favourable_value,
                conditioning_attributes=conditioning,
                ground_truth_attribute=ground_truth,
                exposure_attribute=exposure,
                exposed_value=exposed_value,
                unexposed_value=unexposed_value,
                exposure_randomized=exposure_randomized,
                appeal_attribute=appeal,
                appeal_value=appeal_value,
                final_decision_attribute=final_decision,
                decision_timestamp_attribute=decision_timestamp,
                final_timestamp_attribute=final_timestamp,
                remedy_sla_days=float(remedy_sla_days),
                bootstrap_cluster_attribute=cluster,
                min_group_count=int(min_group_count),
                materiality_threshold=materiality,
                bootstrap_iterations=int(bootstrap_iterations),
                confidence_level=float(confidence_level),
            )
        st.session_state["oversight_audit"] = {"signature": signature, "result": result}
        st.session_state.pop("oversight_research_crate", None)
    except Exception as exc:
        st.error(str(exc))

audit = st.session_state.get("oversight_audit")
if not audit:
    st.info("Validez les colonnes puis lancez l'audit de la décision réelle.")
    st.stop()
if audit["signature"] != signature:
    st.warning("Les paramètres ont changé. Relancez l'audit pour actualiser les résultats.")
    st.stop()

result = audit["result"]
tabs = st.tabs(
    ["Vue d'ensemble", "Transfert", "Automation bias", "Recours", "Preuves", "Recherche"]
)

with tabs[0]:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Écart IA", "N/D" if result.metrics["ai_gap"] is None else f"{result.metrics['ai_gap']:.1%}")
    c2.metric(
        "Écart décision humaine",
        "N/D" if result.metrics["human_gap"] is None else f"{result.metrics['human_gap']:.1%}",
    )
    c3.metric(
        "Écart d'influence IA",
        "N/D"
        if result.metrics["automation_bias_gap"] is None
        else f"{result.metrics['automation_bias_gap']:.1%}",
    )
    c4.metric(
        "Écart de correction",
        "N/D" if result.metrics["remedy_gap"] is None else f"{result.metrics['remedy_gap']:.1%}",
    )
    if result.status.startswith("aucun"):
        st.success(result.status)
    else:
        st.warning(result.status)
    st.dataframe(
        result.comparisons[["label", "protected_rate", "reference_rate", "gap", "coverage"]],
        width="stretch",
        hide_index=True,
        column_config={
            "protected_rate": st.column_config.NumberColumn("Groupe protégé", format="percent"),
            "reference_rate": st.column_config.NumberColumn("Référence", format="percent"),
            "gap": st.column_config.NumberColumn("Écart", format="percent"),
            "coverage": st.column_config.NumberColumn("Couverture", format="percent"),
        },
    )

with tabs[1]:
    st.subheader("Où la disparité change-t-elle ?")
    stages = result.comparisons[
        result.comparisons["metric"].isin(
            ["ai_favourable_rate", "human_favourable_rate", "final_favourable_rate"]
        )
    ].set_index("label")[["protected_rate", "reference_rate"]]
    st.bar_chart(stages)
    st.metric(
        "Amplification absolue par l'intervention humaine",
        "N/D"
        if result.metrics["disparity_amplification"] is None
        else f"{result.metrics['disparity_amplification']:.1%}",
    )
    correction = result.comparisons[
        result.comparisons["metric"].isin(["helpful_override_rate", "harmful_override_rate"])
    ]
    if correction.empty:
        st.info("Ajoutez une vérité terrain pour mesurer les corrections utiles et les erreurs introduites.")
    else:
        st.dataframe(correction, width="stretch", hide_index=True)

with tabs[2]:
    st.subheader("Causal Automation Bias Gap")
    st.markdown(result.causal_interpretation)
    a, b, c = st.columns(3)
    a.metric(
        f"Effet pour {protected_value}",
        "N/D"
        if result.metrics["automation_effect_protected"] is None
        else f"{result.metrics['automation_effect_protected']:.1%}",
    )
    b.metric(
        f"Effet pour {reference_value}",
        "N/D"
        if result.metrics["automation_effect_reference"] is None
        else f"{result.metrics['automation_effect_reference']:.1%}",
    )
    c.metric(
        "Écart différentiel",
        "N/D"
        if result.metrics["automation_bias_gap"] is None
        else f"{result.metrics['automation_bias_gap']:.1%}",
    )
    if result.intervals["automation_bias_gap"]:
        low, high = result.intervals["automation_bias_gap"]
        st.caption(f"IC bootstrap: [{low:.1%} ; {high:.1%}]")
    if not result.exposure_randomized:
        st.warning("Ne présentez pas ce contraste comme causal sans affectation randomisée documentée.")

with tabs[3]:
    st.subheader("Équité de l'accès au recours et de la correction")
    remedy = result.comparisons[
        result.comparisons["metric"].isin(
            ["appeal_access_rate", "remedy_rate", "timely_remedy_rate"]
        )
    ]
    if remedy.empty:
        st.warning("Le journal ne permet pas d'évaluer le recours. Cette absence est une lacune de preuve.")
    else:
        st.dataframe(remedy, width="stretch", hide_index=True)
    st.caption(
        "Le dénominateur contient toutes les décisions initialement défavorables, y compris les personnes "
        "qui n'ont pas déposé de recours."
    )

with tabs[4]:
    st.subheader("Rapport et manifeste vérifiable")
    st.info(
        "Le rapport aide à documenter les articles 12, 13, 14 et 86. Il ne certifie pas la conformité."
    )
    with st.form("oversight_report_metadata"):
        left, right = st.columns(2)
        with left:
            system_name = st.text_input("Nom du système", "Système de décision assistée")
            provider_name = st.text_input("Organisation")
        with right:
            system_version = st.text_input("Version")
            auditor = st.text_input("Responsable de l'audit")
        build_report = st.form_submit_button("Générer le dossier OversightParity", type="primary")
    if build_report:
        metadata = {
            "system_name": system_name,
            "provider_name": provider_name,
            "system_version": system_version,
            "auditor": auditor,
        }
        try:
            prebundle = build_oversight_evidence_bundle(dataset, result, metadata=metadata)
            metadata["audit_id"] = prebundle["audit_id"]
            pdf = generate_oversight_report(dataset, result, metadata=metadata)
            evidence = build_oversight_evidence_bundle(
                dataset, result, metadata=metadata, report_bytes=pdf
            )
            st.download_button(
                "Télécharger le rapport PDF",
                data=pdf,
                file_name="rapport_oversight_parity.pdf",
                mime="application/pdf",
                type="primary",
            )
            st.download_button(
                "Télécharger le manifeste JSON",
                data=json.dumps(
                    json_compatible(evidence), ensure_ascii=False, indent=2, allow_nan=False
                ),
                file_name="preuves_oversight_parity.json",
                mime="application/json",
            )
        except Exception as exc:
            st.error(f"Génération impossible: {exc}")

with tabs[5]:
    st.subheader("Paquet de recherche reproductible")
    st.write(
        "Archivez les métriques, la configuration exacte, l'environnement logiciel, une citation CFF "
        "et des métadonnées RO-Crate 1.3 / Croissant 1.1. Les lignes sources sont exclues par défaut."
    )
    crate_title = st.text_input("Titre du paquet de supervision", "OversightParity research audit")
    crate_creator = st.text_input("Auteur ou organisation du paquet", "EU AI Auditor contributors")
    include_source = st.checkbox(
        "Inclure les événements sources",
        value=False,
        help="À activer uniquement si leur redistribution est autorisée et sûre.",
    )
    recipe = {
        "protected_attribute": protected_attribute,
        "protected_value": protected_value,
        "reference_value": reference_value,
        "ai_recommendation_attribute": ai_column,
        "human_decision_attribute": human_column,
        "favourable_value": favourable_value,
        "conditioning_attributes": conditioning,
        "ground_truth_attribute": ground_truth,
        "exposure_attribute": exposure,
        "exposure_randomized": exposure_randomized,
        "appeal_attribute": appeal,
        "final_decision_attribute": final_decision,
        "bootstrap_cluster_attribute": cluster,
        "remedy_sla_days": float(remedy_sla_days),
        "min_group_count": int(min_group_count),
        "materiality_threshold": float(materiality),
        "bootstrap_iterations": int(bootstrap_iterations),
        "confidence_level": float(confidence_level),
    }
    st.download_button(
        "Télécharger la recette OversightParity",
        data=json.dumps(json_compatible(recipe), ensure_ascii=False, indent=2, allow_nan=False),
        file_name="oversight_parity_recipe.json",
        mime="application/json",
    )
    if st.button("Construire le RO-Crate OversightParity", type="primary"):
        try:
            manifest = build_oversight_evidence_bundle(
                dataset,
                result,
                metadata={"system_name": crate_title},
            )
            crate = build_research_crate(
                dataset,
                manifest,
                audit_kind="oversight-parity",
                config=recipe,
                tables={
                    "oversight_comparisons": result.comparisons,
                    "oversight_group_metrics": result.group_metrics,
                },
                title=crate_title,
                description="AI recommendation, human decision, appeal and remedy fairness evidence.",
                creators=[crate_creator],
                include_source_data=include_source,
            )
            st.session_state["oversight_research_crate"] = crate
        except Exception as exc:
            st.error(f"Paquet de recherche impossible: {exc}")
    if st.session_state.get("oversight_research_crate"):
        st.download_button(
            "Télécharger le RO-Crate OversightParity",
            data=st.session_state["oversight_research_crate"],
            file_name="oversight_parity_research_crate.zip",
            mime="application/zip",
            type="primary",
        )
