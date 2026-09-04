"""Bilingual guided workbench for reproducible fairness research."""

from __future__ import annotations

import json

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from eu_ai_auditor import (
    build_evidence_bundle,
    build_research_crate,
    calculate_cdd,
    calculate_fairness_stability,
    calculate_intersectional_parity,
    calculate_proxy_matrix,
    calculate_risk_quadrants,
    infer_audit_schema,
    profile_dataset,
    read_csv_flexible,
)
from eu_ai_auditor.demo import make_demo_dataset
from eu_ai_auditor.serialization import json_compatible
from eu_ai_auditor.visuals import stability_curve

st.set_page_config(page_title="Research Workbench", page_icon="🌍", layout="wide")

TEXT = {
    "English": {
        "title": "Research Workbench",
        "kicker": "GLOBAL · REPRODUCIBLE · PRIVACY-FIRST",
        "intro": (
            "A guided fairness audit for researchers. Map a dataset, inspect intersectional uncertainty, "
            "and export a citable research object without uploading records to a third party."
        ),
        "language": "Language",
        "data": "1. Data",
        "upload": "Upload a CSV",
        "demo": "Use synthetic demo data",
        "local": "Processing stays in this Streamlit session.",
        "mapping": "2. Audit mapping",
        "decision": "Decision column",
        "favourable": "Favourable outcome",
        "protected": "Protected attributes",
        "primary_group": "Primary protected group",
        "conditioning": "Legitimate conditioning factors R",
        "advanced": "Scientific options",
        "minimum": "Minimum observations per intersection",
        "bootstrap": "CDD bootstrap replications",
        "confidence": "Confidence level",
        "materiality": "Materiality review threshold",
        "fdr": "False-discovery-rate threshold",
        "depth": "Maximum conditioning factors per specification",
        "run": "Run reproducible audit",
        "suggestions": "Automatic mapping suggestions",
        "verify": "Suggestions use names and types only. Verify every normative choice.",
        "loaded": "Loaded",
        "rows": "rows",
        "columns": "columns",
        "launch": "Review the mapping, then run the audit.",
        "summary": "Summary",
        "intersections": "Intersections",
        "stability": "Specification stability",
        "reproducibility": "Reproducibility",
        "cdd": "CDD gap",
        "coverage": "CDD coverage",
        "groups": "Eligible intersections",
        "priorities": "FDR priorities",
        "worst": "Worst-case gap",
        "robustness": "Robustness score",
        "consensus": "Dominant conclusion",
        "gap_range": "CDD range",
        "no_stability": "Select at least one defensible R factor to compare specifications.",
        "stability_note": (
            "Justify every candidate factor before reading the results. This diagnoses analyst-choice "
            "sensitivity; it is not a causal or legal conclusion."
        ),
        "quality": "Data quality",
        "no_warning": "No automatic data-quality warning at the configured thresholds.",
        "small_groups": (
            "Small groups remain visible but are not tested. q-values control multiple comparisons; "
            "neither p-values nor q-values are legal findings."
        ),
        "crate": "Citable research package",
        "crate_help": (
            "The ZIP contains RO-Crate 1.3 and Croissant 1.1 metadata, exact configuration, tidy CSV "
            "results, checksums, software environment and CITATION.cff."
        ),
        "crate_title": "Package title",
        "creator": "Author or organisation",
        "include": "Include source records",
        "include_help": "Off by default to avoid accidental redistribution of personal or sensitive data.",
        "recipe": "Download audit recipe",
        "build": "Build research RO-Crate",
        "download": "Download research RO-Crate",
        "stale": "Parameters changed. Run the audit again before using the results.",
    },
    "Français": {
        "title": "Laboratoire de recherche",
        "kicker": "MONDIAL · REPRODUCTIBLE · CONFIDENTIEL PAR DÉFAUT",
        "intro": (
            "Un audit de fairness guidé pour la recherche. Associez les colonnes, examinez l'incertitude "
            "intersectionnelle et exportez un objet citable sans envoyer les données à un tiers."
        ),
        "language": "Langue",
        "data": "1. Données",
        "upload": "Déposer un CSV",
        "demo": "Utiliser la démonstration synthétique",
        "local": "Le traitement reste dans cette session Streamlit.",
        "mapping": "2. Correspondance de l'audit",
        "decision": "Colonne de décision",
        "favourable": "Issue favorable",
        "protected": "Attributs protégés",
        "primary_group": "Groupe protégé principal",
        "conditioning": "Facteurs légitimes de conditionnement R",
        "advanced": "Options scientifiques",
        "minimum": "Minimum par intersection",
        "bootstrap": "Réplications bootstrap CDD",
        "confidence": "Niveau de confiance",
        "materiality": "Seuil matériel de revue",
        "fdr": "Seuil du taux de fausses découvertes",
        "depth": "Nombre maximal de facteurs par spécification",
        "run": "Lancer l'audit reproductible",
        "suggestions": "Suggestions de correspondance automatique",
        "verify": "Les suggestions utilisent seulement les noms et types. Vérifiez chaque choix normatif.",
        "loaded": "Chargé",
        "rows": "lignes",
        "columns": "colonnes",
        "launch": "Vérifiez la correspondance puis lancez l'audit.",
        "summary": "Synthèse",
        "intersections": "Intersections",
        "stability": "Stabilité des spécifications",
        "reproducibility": "Reproductibilité",
        "cdd": "Écart CDD",
        "coverage": "Couverture CDD",
        "groups": "Intersections éligibles",
        "priorities": "Priorités après FDR",
        "worst": "Écart pire cas",
        "robustness": "Score de robustesse",
        "consensus": "Conclusion dominante",
        "gap_range": "Étendue CDD",
        "no_stability": "Sélectionnez au moins un facteur R défendable pour comparer les spécifications.",
        "stability_note": (
            "Justifiez chaque facteur candidat avant lecture. Ce diagnostic mesure la sensibilité aux "
            "choix d'analyse; ce n'est pas une conclusion causale ou juridique."
        ),
        "quality": "Qualité des données",
        "no_warning": "Aucun avertissement automatique de qualité aux seuils configurés.",
        "small_groups": (
            "Les petits groupes restent visibles mais ne sont pas testés. Les q-values corrigent les "
            "comparaisons multiples; ni p-values ni q-values ne constituent une conclusion juridique."
        ),
        "crate": "Paquet de recherche citable",
        "crate_help": (
            "Le ZIP contient les métadonnées RO-Crate 1.3 et Croissant 1.1, la configuration exacte, "
            "les résultats CSV, les empreintes, l'environnement logiciel et CITATION.cff."
        ),
        "crate_title": "Titre du paquet",
        "creator": "Auteur ou organisation",
        "include": "Inclure les lignes sources",
        "include_help": "Désactivé par défaut pour éviter une redistribution accidentelle.",
        "recipe": "Télécharger la recette d'audit",
        "build": "Construire le RO-Crate de recherche",
        "download": "Télécharger le RO-Crate de recherche",
        "stale": "Les paramètres ont changé. Relancez l'audit avant d'utiliser les résultats.",
    },
}


def _read_csv(uploaded) -> pd.DataFrame:
    return read_csv_flexible(uploaded.getvalue())


def _index(options: list, preferred) -> int:
    return options.index(preferred) if preferred in options else 0


with st.sidebar:
    language = st.selectbox("Language / Langue", ["English", "Français"])
t = TEXT[language]

st.caption(t["kicker"])
st.title(t["title"])
st.write(t["intro"])

with st.sidebar:
    st.header(t["data"])
    uploaded = st.file_uploader(t["upload"], type=["csv"])
    use_demo = st.toggle(t["demo"], value=uploaded is None)
    st.caption(t["local"])

if uploaded is not None:
    use_demo = False
try:
    data = make_demo_dataset() if use_demo else _read_csv(uploaded) if uploaded else None
except ValueError as exc:
    st.error(str(exc))
    st.stop()
if data is None:
    st.info(t["launch"])
    st.stop()
if data.empty or len(data.columns) < 3:
    st.error("The dataset needs rows and at least three columns. / Trois colonnes sont requises.")
    st.stop()

inference = infer_audit_schema(data, mode="classic")
columns = list(data.columns)
with st.sidebar:
    st.header(t["mapping"])
    suggested_decision = inference.mapping.get("decision_attribute")
    decision = st.selectbox(t["decision"], columns, index=_index(columns, suggested_decision))
    outcomes = list(data[decision].dropna().unique())
    if len(outcomes) < 2:
        st.error("The decision column needs at least two outcomes.")
        st.stop()
    favourable = st.selectbox(
        t["favourable"],
        outcomes,
        index=_index(outcomes, inference.value_suggestions.get("favourable_value")),
    )
    protected_candidates = [column for column in columns if column != decision]
    suggested_protected = inference.mapping.get("protected_attribute")
    protected = st.multiselect(
        t["protected"],
        protected_candidates,
        default=[suggested_protected] if suggested_protected in protected_candidates else [],
        max_selections=4,
    )
    if not protected:
        st.warning("Select at least one protected attribute. / Sélectionnez au moins un attribut protégé.")
        st.stop()
    primary_values = list(data[protected[0]].dropna().unique())
    primary_group = st.selectbox(t["primary_group"], primary_values)
    conditioning_candidates = [
        column for column in columns if column not in {*protected, decision}
    ]
    conditioning = st.multiselect(
        t["conditioning"],
        conditioning_candidates,
        default=[
            column
            for column in inference.conditioning_candidates
            if column in conditioning_candidates
        ],
    )
    with st.expander(t["advanced"]):
        min_group = st.number_input(t["minimum"], 2, 1000, 30)
        bootstrap = st.select_slider(t["bootstrap"], options=[0, 100, 250, 500], value=100)
        confidence = st.select_slider(t["confidence"], options=[0.90, 0.95, 0.99], value=0.95)
        materiality = st.slider(t["materiality"], 0.0, 0.30, 0.05, 0.01)
        fdr_alpha = st.select_slider(t["fdr"], options=[0.01, 0.05, 0.10], value=0.05)
        max_stability_depth = st.number_input(
            t["depth"],
            min_value=1,
            max_value=max(1, len(conditioning)),
            value=min(2, max(1, len(conditioning))),
            disabled=not conditioning,
        )
    with st.expander(t["suggestions"]):
        st.json(inference.summary())
        st.caption(t["verify"])
    run = st.button(t["run"], type="primary", width="stretch")

st.caption(
    f"{t['loaded']}: {len(data):,} {t['rows']} × {len(data.columns)} {t['columns']} · "
    f"SHA-256 tracked in every export"
)
with st.expander("Data preview / Aperçu"):
    st.dataframe(data.head(100), width="stretch", hide_index=True)

signature = (
    decision,
    str(favourable),
    tuple(protected),
    str(primary_group),
    tuple(conditioning),
    int(min_group),
    int(bootstrap),
    float(confidence),
    float(materiality),
    float(fdr_alpha),
    int(max_stability_depth),
)
if run:
    try:
        with st.spinner("Computing uncertainty / Calcul de l'incertitude..."):
            cdd = calculate_cdd(
                data,
                protected[0],
                primary_group,
                decision,
                favourable,
                conditioning,
                min_outcome_count=max(2, min(int(min_group), 20)),
                materiality_threshold=float(materiality),
                bootstrap_iterations=int(bootstrap),
                confidence_level=float(confidence),
            )
            intersections = calculate_intersectional_parity(
                data,
                protected,
                decision,
                favourable,
                min_group_count=int(min_group),
                materiality_threshold=float(materiality),
                confidence_level=float(confidence),
                fdr_alpha=float(fdr_alpha),
            )
            quality = profile_dataset(data, protected)
            candidates = [column for column in columns if column not in {*protected, decision}]
            proxies = calculate_proxy_matrix(data, protected, candidates, min_pairs=max(5, int(min_group)))
            quadrants = calculate_risk_quadrants(data, protected, decision, favourable)
            stability = (
                calculate_fairness_stability(
                    data,
                    protected[0],
                    primary_group,
                    decision,
                    favourable,
                    conditioning,
                    max_conditioning_factors=min(
                        int(max_stability_depth), len(conditioning)
                    ),
                    min_outcome_count=max(2, min(int(min_group), 20)),
                    materiality_threshold=float(materiality),
                )
                if conditioning
                else None
            )
        st.session_state["research_workbench"] = {
            "signature": signature,
            "cdd": cdd,
            "intersections": intersections,
            "quality": quality,
            "proxies": proxies,
            "quadrants": quadrants,
            "stability": stability,
        }
        st.session_state.pop("workbench_crate", None)
    except ValueError as exc:
        st.error(str(exc))

audit = st.session_state.get("research_workbench")
if not audit:
    st.info(t["launch"])
    st.stop()
if audit["signature"] != signature:
    st.warning(t["stale"])
    st.stop()

cdd = audit["cdd"]
intersections = audit["intersections"]
quality = audit["quality"]
proxies = audit["proxies"]
quadrants = audit["quadrants"]
stability = audit["stability"]
summary_tab, intersections_tab, stability_tab, reproducibility_tab = st.tabs(
    [t["summary"], t["intersections"], t["stability"], t["reproducibility"]]
)

with summary_tab:
    a, b, c, d = st.columns(4)
    a.metric(t["cdd"], "N/A" if cdd.gap is None else f"{cdd.gap:.1%}")
    b.metric(t["coverage"], f"{cdd.coverage:.1%}")
    c.metric(t["groups"], intersections.eligible_groups)
    d.metric(t["priorities"], intersections.flagged_groups)
    st.subheader(t["quality"])
    if quality["warnings"]:
        for warning in quality["warnings"]:
            st.write("- " + warning)
    else:
        st.success(t["no_warning"])

with intersections_tab:
    st.metric(
        t["worst"],
        "N/A" if intersections.worst_case_gap is None else f"{intersections.worst_case_gap:.1%}",
    )
    st.dataframe(intersections.groups, width="stretch", hide_index=True)
    st.caption(t["small_groups"])

with stability_tab:
    if stability is None:
        st.info(t["no_stability"])
    else:
        a, b, c = st.columns(3)
        a.metric(t["robustness"], f"{stability.robustness_score:.1%}")
        b.metric(t["consensus"], f"{stability.dominant_share:.1%}")
        c.metric(t["gap_range"], f"{stability.gap_min:.1%} to {stability.gap_max:.1%}")
        if "sensible" in stability.status:
            st.warning(stability.status)
        else:
            st.success(stability.status)
        figure = stability_curve(stability)
        st.pyplot(figure, width="content")
        plt.close(figure)
        st.dataframe(stability.factor_effects, width="stretch", hide_index=True)
        with st.expander("All specifications / Toutes les spécifications"):
            st.dataframe(stability.specifications, width="stretch", hide_index=True)
        st.caption(t["stability_note"])

with reproducibility_tab:
    st.subheader(t["crate"])
    st.write(t["crate_help"])
    crate_title = st.text_input(t["crate_title"], "EU AI Auditor research audit")
    creator = st.text_input(t["creator"], "EU AI Auditor contributors")
    include_source = st.checkbox(t["include"], value=False, help=t["include_help"])
    recipe = {
        "decision_attribute": decision,
        "favourable_value": favourable,
        "protected_attributes": protected,
        "protected_value": primary_group,
        "conditioning_attributes": conditioning,
        "intersection_min_group_count": int(min_group),
        "min_outcome_count": max(2, min(int(min_group), 20)),
        "bootstrap_iterations": int(bootstrap),
        "confidence_level": float(confidence),
        "materiality_threshold": float(materiality),
        "fdr_alpha": float(fdr_alpha),
        "stability_max_factors": int(max_stability_depth),
    }
    st.download_button(
        t["recipe"],
        json.dumps(json_compatible(recipe), ensure_ascii=False, indent=2, allow_nan=False),
        file_name="eu_ai_auditor_recipe.json",
        mime="application/json",
    )
    if st.button(t["build"], type="primary"):
        evidence = build_evidence_bundle(
            data,
            cdd,
            proxies,
            quadrant_result=quadrants,
            intersectional_result=intersections,
            stability_result=stability,
            metadata={"system_name": crate_title, "protected_attributes": protected},
        )
        st.session_state["workbench_crate"] = build_research_crate(
            data,
            evidence,
            audit_kind="research-workbench",
            config=recipe,
            tables={
                "cdd_strata": cdd.strata,
                "intersectional_groups": intersections.groups,
                "proxy_scores": proxies.scores,
                "quadrants": quadrants.features,
                **(
                    {
                        "stability_specifications": stability.specifications,
                        "stability_factor_effects": stability.factor_effects,
                    }
                    if stability is not None
                    else {}
                ),
            },
            title=crate_title,
            creators=[creator],
            include_source_data=include_source,
        )
    if st.session_state.get("workbench_crate"):
        st.download_button(
            t["download"],
            st.session_state["workbench_crate"],
            file_name="eu_ai_auditor_research_crate.zip",
            mime="application/zip",
            type="primary",
        )
