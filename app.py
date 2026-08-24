"""Streamlit interface for EU AI Auditor."""

from __future__ import annotations

import json
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from eu_ai_auditor import (
    calculate_cdd,
    calculate_proxy_matrix,
    calculate_risk_quadrants,
    compare_models,
    profile_dataset,
)
from eu_ai_auditor.demo import make_demo_dataset
from eu_ai_auditor.report_generator import generate_compliance_report
from eu_ai_auditor.visuals import cdd_strata_chart, proxy_heatmap, quadrant_chart, tradeoff_chart

st.set_page_config(
    page_title="EU AI Auditor",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --navy:#132238; --teal:#0F766E; --mist:#E8EEF2; --coral:#D65A4A; }
    .block-container {padding-top: 2rem; padding-bottom: 4rem; max-width: 1320px;}
    [data-testid="stSidebar"] {background:#F6F8FA; border-right:1px solid #E8EEF2;}
    h1, h2, h3 {color:var(--navy); letter-spacing:-0.02em;}
    .eyebrow {font-size:.78rem; font-weight:700; color:var(--teal); letter-spacing:.12em; text-transform:uppercase;}
    .hero {padding:1.5rem 0 1rem 0; border-bottom:1px solid var(--mist); margin-bottom:1.25rem;}
    .hero p {max-width:800px; color:#526274; font-size:1.04rem;}
    .privacy {padding:.7rem .9rem; background:#E8F3F1; border-left:3px solid var(--teal); border-radius:.25rem; color:#294B49; font-size:.86rem;}
    .legal {padding:.75rem .9rem; background:#FFF3EE; border-left:3px solid var(--coral); border-radius:.25rem; color:#724237; font-size:.86rem;}
    [data-testid="stMetric"] {background:white; border:1px solid var(--mist); border-radius:.5rem; padding:.8rem 1rem;}
    .stButton button, .stDownloadButton button {border-radius:.35rem; font-weight:650;}
    </style>
    """,
    unsafe_allow_html=True,
)


def _read_csv(uploaded) -> pd.DataFrame:
    payload = uploaded.getvalue()
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(BytesIO(payload), sep=None, engine="python", encoding=encoding)
        except (UnicodeDecodeError, pd.errors.ParserError) as exc:
            errors.append(str(exc))
    raise ValueError("Impossible de lire le CSV. Vérifiez l'encodage et le séparateur. " + errors[-1])


def _safe_values(series: pd.Series) -> list:
    return list(series.dropna().unique())


st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">Audit statistique européen</div>
      <h1>EU AI Auditor</h1>
      <p>Détectez les disparités conditionnelles, les variables proxys et les arbitrages
      performance-équité. Constituez un dossier de preuves aligné sur les articles 10, 11,
      13 et 14 du règlement européen sur l'intelligence artificielle.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("1. Données")
    uploaded = st.file_uploader("Déposer un fichier CSV", type=["csv"])
    use_demo = st.toggle("Utiliser les données de démonstration", value=uploaded is None)
    if uploaded is not None:
        use_demo = False
    st.markdown(
        '<div class="privacy">Traitement local à la session Streamlit. Le projet ne contient aucun envoi vers un service tiers.</div>',
        unsafe_allow_html=True,
    )

if uploaded is None and not use_demo:
    st.info("Déposez un fichier CSV ou activez la démonstration pour commencer.")
    st.stop()

try:
    dataset = make_demo_dataset() if use_demo else _read_csv(uploaded)
except (ValueError, pd.errors.ParserError) as exc:
    st.error(str(exc))
    st.stop()

if dataset.empty or len(dataset.columns) < 3:
    st.error("Le fichier doit contenir des lignes et au moins trois colonnes.")
    st.stop()

with st.sidebar:
    st.header("2. Paramètres")
    decision_options = list(dataset.columns)
    decision_default = decision_options.index("selection") if use_demo and "selection" in decision_options else 0
    decision_attribute = st.selectbox(
        "Variable de décision", decision_options, index=decision_default
    )
    favourable_values = _safe_values(dataset[decision_attribute])
    if len(favourable_values) < 2:
        st.error("La variable de décision doit contenir au moins deux issues.")
        st.stop()
    favourable_default = (
        favourable_values.index("Retenu")
        if use_demo and "Retenu" in favourable_values
        else 0
    )
    favourable_value = st.selectbox(
        "Issue favorable", favourable_values, index=favourable_default
    )
    protected_choices = [column for column in dataset.columns if column != decision_attribute]
    protected_default = protected_choices.index("genre") if use_demo and "genre" in protected_choices else 0
    protected_attribute = st.selectbox(
        "Variable protégée principale", protected_choices, index=protected_default
    )
    protected_values = _safe_values(dataset[protected_attribute])
    protected_value_default = (
        protected_values.index("Femme")
        if use_demo and "Femme" in protected_values
        else 0
    )
    protected_value = st.selectbox(
        "Classe protégée examinée", protected_values, index=protected_value_default
    )
    additional_default = []
    protected_attributes = st.multiselect(
        "Variables protégées pour la matrice",
        protected_choices,
        default=[protected_attribute, *additional_default],
    )
    if protected_attribute not in protected_attributes:
        protected_attributes = [protected_attribute, *protected_attributes]
    condition_choices = [
        column for column in dataset.columns if column not in {decision_attribute, protected_attribute}
    ]
    conditioning_default = (
        [column for column in ["diplome", "anciennete_annees"] if column in condition_choices]
        if use_demo
        else []
    )
    conditioning = st.multiselect(
        "Facteurs légitimes R", condition_choices, default=conditioning_default
    )
    candidate_default = [
        column
        for column in dataset.columns
        if column not in {*protected_attributes, decision_attribute}
    ]
    candidate_features = st.multiselect(
        "Variables candidates aux proxys", candidate_default, default=candidate_default
    )
    with st.expander("Seuils et qualité"):
        materiality = st.slider("Seuil de matérialité CDD", 0.0, 0.30, 0.05, 0.01)
        min_outcome_count = st.number_input("Minimum par issue et par strate", 1, 100, 5)
        low_proxy = st.slider("Seuil proxy moyen", 0.01, 0.50, 0.10, 0.01)
        high_proxy = st.slider("Seuil proxy haut", low_proxy + 0.01, 0.90, 0.30, 0.01)
        mean_quadrant = st.slider("Seuil impact moyen", 0.01, 0.30, 0.05, 0.01)
        max_quadrant = st.slider("Seuil impact maximal", 0.01, 0.40, 0.10, 0.01)
    run_audit = st.button("Lancer l'audit", type="primary", width="stretch")

st.caption(f"Jeu chargé: {len(dataset):,} lignes × {len(dataset.columns)} colonnes")
with st.expander("Aperçu des données", expanded=False):
    st.dataframe(dataset.head(100), width="stretch", hide_index=True)

if run_audit:
    try:
        quality = profile_dataset(dataset, protected_attributes)
        cdd_result = calculate_cdd(
            dataset,
            protected_attribute=protected_attribute,
            protected_value=protected_value,
            decision_attribute=decision_attribute,
            advantaged_value=favourable_value,
            conditioning_attributes=conditioning,
            min_outcome_count=int(min_outcome_count),
            materiality_threshold=materiality,
        )
        proxy_result = calculate_proxy_matrix(
            dataset,
            protected_attributes=protected_attributes,
            candidate_features=candidate_features,
            low_threshold=low_proxy,
            high_threshold=high_proxy,
            min_pairs=max(5, int(min_outcome_count)),
        )
        quadrant_result = calculate_risk_quadrants(
            dataset,
            protected_attributes=protected_attributes,
            decision_attribute=decision_attribute,
            favourable_value=favourable_value,
            mean_threshold=mean_quadrant,
            max_threshold=max_quadrant,
        )
        st.session_state["audit"] = {
            "signature": (decision_attribute, str(favourable_value), protected_attribute, str(protected_value), tuple(conditioning)),
            "quality": quality,
            "cdd": cdd_result,
            "proxy": proxy_result,
            "quadrant": quadrant_result,
            "tradeoff": None,
        }
    except ValueError as exc:
        st.error(str(exc))

audit = st.session_state.get("audit")
if not audit:
    st.markdown(
        '<div class="legal">Lancez l’audit après avoir validé les groupes, l’issue favorable et les facteurs R. Ces choix sont contextuels et doivent être justifiés.</div>',
        unsafe_allow_html=True,
    )
    st.stop()

current_signature = (decision_attribute, str(favourable_value), protected_attribute, str(protected_value), tuple(conditioning))
if audit["signature"] != current_signature:
    st.warning("Les paramètres ont changé. Relancez l'audit pour mettre les résultats à jour.")

quality = audit["quality"]
cdd_result = audit["cdd"]
proxy_result = audit["proxy"]
quadrant_result = audit["quadrant"]

tabs = st.tabs(["Vue d'ensemble", "CDD", "Proxys", "Quadrants", "Performance", "Rapport"])

with tabs[0]:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Écart CDD", "N/D" if cdd_result.gap is None else f"{cdd_result.gap:.1%}")
    col2.metric("Couverture CDD", f"{cdd_result.coverage:.1%}")
    col3.metric("Proxys à haut risque", int((proxy_result.scores["risk"] == "Haut").sum()))
    col4.metric("Valeurs manquantes", f"{quality['overall_missing_rate']:.1%}")
    if cdd_result.material_signal:
        st.warning(f"CDD: {cdd_result.status}. Une investigation contextuelle est requise.")
    else:
        st.success(f"CDD: {cdd_result.status}. Cela ne constitue pas une conclusion juridique.")
    left, right = st.columns([1.05, 0.95])
    with left:
        st.subheader("Priorités d'investigation")
        priorities = proxy_result.scores[proxy_result.scores["risk"].isin(["Haut", "Moyen"])].head(10)
        if priorities.empty:
            st.info("Aucune relation moyenne ou haute selon les seuils choisis.")
        else:
            st.dataframe(priorities, width="stretch", hide_index=True)
    with right:
        st.subheader("Qualité et représentation")
        if quality["warnings"]:
            for warning in quality["warnings"][:8]:
                st.write("- " + warning)
        else:
            st.write("Aucun signal automatique de qualité avec les seuils par défaut.")

with tabs[1]:
    st.subheader("Disparité démographique conditionnelle")
    st.latex(r"A_R=P(S=s\mid Y=\mathrm{favorable},R),\quad D_R=P(S=s\mid Y=\mathrm{defavorable},R)")
    c1, c2, c3 = st.columns(3)
    c1.metric("A_R agrégé", "N/D" if cdd_result.advantaged_share is None else f"{cdd_result.advantaged_share:.1%}")
    c2.metric("D_R agrégé", "N/D" if cdd_result.disadvantaged_share is None else f"{cdd_result.disadvantaged_share:.1%}")
    c3.metric("D_R - A_R", "N/D" if cdd_result.gap is None else f"{cdd_result.gap:.1%}")
    if cdd_result.strata["eligible"].any():
        figure = cdd_strata_chart(cdd_result)
        st.pyplot(figure, width="content")
        plt.close(figure)
    st.dataframe(cdd_result.strata, width="stretch", hide_index=True)
    for note in cdd_result.notes:
        st.caption(note)

with tabs[2]:
    st.subheader("Matrice des proxys")
    figure = proxy_heatmap(proxy_result)
    st.pyplot(figure, width="content")
    plt.close(figure)
    st.dataframe(proxy_result.scores, width="stretch", hide_index=True)
    st.caption("Association ne signifie pas causalité. Les seuils servent à prioriser la revue.")

with tabs[3]:
    st.subheader("Quadrants d'impact")
    figure = quadrant_chart(quadrant_result)
    st.pyplot(figure, width="content")
    plt.close(figure)
    st.dataframe(quadrant_result.features, width="stretch", hide_index=True)
    with st.expander("Détail des sous-groupes"):
        st.dataframe(quadrant_result.subgroups, width="stretch", hide_index=True)

with tabs[4]:
    st.subheader("Frontière performance-équité")
    st.write(
        "La comparaison entraîne une régression logistique et un arbre CART sur un échantillon "
        "d'entraînement, puis évalue plusieurs seuils sur un échantillon de test."
    )
    if st.button("Calculer la frontière LR / CART"):
        try:
            with st.spinner("Entraînement et évaluation des points de fonctionnement..."):
                audit["tradeoff"] = compare_models(
                    dataset,
                    target_attribute=decision_attribute,
                    favourable_value=favourable_value,
                    protected_attribute=protected_attribute,
                    protected_value=protected_value,
                    conditioning_attributes=conditioning,
                    exclude_features=[column for column in protected_attributes if column != protected_attribute],
                )
                st.session_state["audit"] = audit
        except ValueError as exc:
            st.error(str(exc))
    tradeoff_result = audit.get("tradeoff")
    if tradeoff_result is not None:
        figure = tradeoff_chart(tradeoff_result)
        st.pyplot(figure, width="content")
        plt.close(figure)
        st.dataframe(tradeoff_result.points, width="stretch", hide_index=True)
        st.caption("La frontière n'impose aucun choix normatif. Documentez la décision finale et son responsable.")

with tabs[5]:
    st.subheader("Dossier de preuves AI Act")
    st.markdown(
        '<div class="legal">Le PDF aide à constituer la documentation technique. Il ne certifie pas la conformité et doit être complété par les responsables juridiques, métiers, données et risques.</div>',
        unsafe_allow_html=True,
    )
    with st.form("report_metadata"):
        left, right = st.columns(2)
        with left:
            system_name = st.text_input("Nom du système", "Système de décision")
            provider_name = st.text_input("Fournisseur / organisation")
            system_version = st.text_input("Version")
            auditor = st.text_input("Responsable de l'audit")
            intended_purpose = st.text_area("Finalité prévue")
            data_origin = st.text_area("Origine et période des données")
        with right:
            intended_users = st.text_input("Utilisateurs visés")
            geographic_scope = st.text_input("Portée géographique")
            human_oversight = st.text_area("Mesures de supervision humaine")
            known_limitations = st.text_area("Limites connues")
            tradeoff_rationale = st.text_area("Justification de l'arbitrage performance-équité")
            post_market = st.text_area("Plan de suivi après mise sur le marché")
        build_report = st.form_submit_button("Générer le PDF", type="primary")
    if build_report:
        metadata = {
            "system_name": system_name,
            "provider_name": provider_name,
            "system_version": system_version,
            "auditor": auditor,
            "intended_purpose": intended_purpose,
            "data_origin": data_origin,
            "intended_users": intended_users,
            "geographic_scope": geographic_scope,
            "human_oversight": human_oversight,
            "known_limitations": known_limitations,
            "tradeoff_rationale": tradeoff_rationale,
            "post_market_monitoring": post_market,
            "protected_attributes": protected_attributes,
        }
        try:
            pdf = generate_compliance_report(
                dataset,
                cdd_result,
                proxy_result,
                quadrant_result=quadrant_result,
                tradeoff_result=audit.get("tradeoff"),
                metadata=metadata,
            )
            st.download_button(
                "Télécharger le rapport PDF",
                data=pdf,
                file_name="rapport_eu_ai_auditor.pdf",
                mime="application/pdf",
                type="primary",
            )
            json_payload = {
                "cdd": cdd_result.summary(),
                "proxy_scores": proxy_result.scores.to_dict(orient="records"),
                "quadrants": quadrant_result.features.to_dict(orient="records"),
                "quality": quality,
            }
            st.download_button(
                "Télécharger les résultats JSON",
                data=json.dumps(json_payload, ensure_ascii=False, indent=2, default=str),
                file_name="resultats_eu_ai_auditor.json",
                mime="application/json",
            )
        except Exception as exc:  # keep the UI responsive and show a bounded failure
            st.error(f"Le rapport n'a pas pu être généré: {exc}")
