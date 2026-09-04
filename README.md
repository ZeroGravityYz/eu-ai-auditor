# EU AI Auditor

> [English documentation](docs/README.en.md) · [Research workflow](docs/research-workbench.md) · [Scientific methodology](docs/methodology.md)

[![CI](https://github.com/ZeroGravityYz/eu-ai-auditor/actions/workflows/ci.yml/badge.svg)](https://github.com/ZeroGravityYz/eu-ai-auditor/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-0F766E)](https://www.python.org/)
[![License: Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-132238)](LICENSE)

EU AI Auditor est un package Python et une application Streamlit pour produire des preuves statistiques et procédurales sur les systèmes de décision. Il réunit deux parcours complémentaires :

- **OversightParity** suit la recommandation IA, la décision humaine, le recours et la correction afin d'auditer la fairness de la décision réellement appliquée ;
- l'audit tabulaire classique combine CDD, proxys, quadrants d'impact et frontière performance-équité.

Le parcours classique comprend :

- la disparité démographique conditionnelle (CDD) proposée comme mesure descriptive par Wachter, Mittelstadt et Russell ;
- une matrice de risque de proxys inspirée de l'approche présentée par Deloitte ;
- les quadrants d'impact des variables protégées ;
- une frontière performance-équité comparant régression logistique et arbre CART.

Depuis la version 0.4, le projet ajoute un laboratoire bilingue, une configuration assistée, l'analyse intersectionnelle avec correction des comparaisons multiples et des paquets de recherche RO-Crate vérifiables. OversightParity mesure toujours le transfert de disparité entre le modèle et l'humain, les corrections utiles et erreurs introduites, l'influence différentielle de l'assistance IA, ainsi que l'équité de l'accès au recours.

Le rapport PDF organise les résultats comme éléments de travail pour les articles 10, 11, 13 et 14 du règlement (UE) 2024/1689. Il ne certifie pas la conformité et ne remplace ni l'analyse juridique, ni l'évaluation des risques, ni la gouvernance interne.

## Démarrage rapide

Prérequis : Python 3.10 ou plus récent.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app.py
```

L'application s'ouvre avec un jeu de recrutement synthétique. La page **OversightParity** dispose de son propre journal synthétique explicitement signalé et d'une interface de correspondance des étapes du processus.

## Research Workbench — parcours international

La page **Research Workbench** propose une interface guidée en anglais et en français :

- reconnaissance prudente des colonnes de décision, attributs protégés et facteurs potentiels `R` ;
- validation humaine obligatoire des choix normatifs ;
- analyse de plusieurs attributs et de leurs intersections ;
- intervalles de Wilson, tests exacts de Fisher et q-values de Benjamini-Hochberg ;
- export sans données sources par défaut d'un ZIP conforme à **RO-Crate 1.3**, avec métadonnées **Croissant 1.1**, tables CSV ordonnées, configuration, environnement logiciel, empreintes et `CITATION.cff`.

L'inférence de schéma facilite la configuration mais ne choisit jamais automatiquement un groupe protégé ou de référence. Elle utilise uniquement les noms, types et cardinalités des colonnes.

```python
from eu_ai_auditor import infer_audit_schema, calculate_intersectional_parity

suggestion = infer_audit_schema(data, mode="classic")
result = calculate_intersectional_parity(
    data,
    protected_attributes=["gender", "age_band"],
    decision_attribute="approved",
    favourable_value=True,
    min_group_count=30,
)
print(result.groups)
```

## OversightParity

La plupart des bibliothèques s'arrêtent à la sortie du modèle. OversightParity reconstruit la chaîne complète :

```text
recommandation IA → décision humaine → recours → décision corrigée
```

Il produit notamment :

- le **Fairness Transfer**, qui indique comment l'écart change entre la recommandation et la décision humaine ;
- le **Causal Automation Bias Gap**, qui compare l'effet de rendre l'avis IA visible entre deux groupes ;
- l'**Equitable Error Correction**, qui mesure les erreurs IA corrigées et les erreurs introduites par l'humain ;
- la **Conditional Remedy Parity**, qui compare l'accès au recours et la correction parmi toutes les décisions initialement défavorables.

Un contraste d'exposition n'est présenté comme causal que si l'utilisateur déclare une affectation randomisée documentée. Dans les autres cas, le résultat est explicitement qualifié d'association conditionnelle.

```python
import pandas as pd
from eu_ai_auditor import calculate_oversight_parity

events = pd.read_csv("journal_decisions.csv")
result = calculate_oversight_parity(
    events,
    protected_attribute="genre",
    protected_value="Femme",
    reference_value="Homme",
    ai_recommendation_attribute="recommandation_ia",
    human_decision_attribute="decision_humaine",
    favourable_value="Favorable",
    conditioning_attributes=["diplome", "anciennete_annees"],
    ground_truth_attribute="verite_terrain",
    exposure_attribute="ia_visible",
    exposed_value="Visible",
    unexposed_value="Masquée",
    exposure_randomized=True,
    appeal_attribute="recours",
    appeal_value="Oui",
    final_decision_attribute="decision_finale",
    bootstrap_cluster_attribute="case_id",
    bootstrap_iterations=250,
)

print(result.metrics)
print(result.comparisons)
```

Voir [la spécification scientifique et le schéma d'événements](docs/oversight-parity.md).

## Utilisation Python

```python
import pandas as pd
from eu_ai_auditor import calculate_cdd, calculate_proxy_matrix

data = pd.read_csv("decisions.csv")

result = calculate_cdd(
    data,
    protected_attribute="genre",
    protected_value="Femme",
    decision_attribute="selection",
    advantaged_value="Retenu",
    conditioning_attributes=["diplome", "anciennete"],
    min_outcome_count=5,
    materiality_threshold=0.05,
    bootstrap_iterations=250,
    confidence_level=0.95,
)

print(result.gap)
print(result.strata)

proxies = calculate_proxy_matrix(
    data,
    protected_attributes=["genre", "tranche_age"],
    candidate_features=["code_postal", "profession", "revenu"],
)
print(proxies.scores)
```

## Utilisation en ligne de commande

```bash
eu-ai-auditor data/recrutement_demo.csv \
  --protected genre \
  --protected-value Femme \
  --decision selection \
  --favourable-value Retenu \
  --condition diplome \
  --condition anciennete_annees \
  --with-tradeoff \
  --bootstrap-iterations 250 \
  --output output/pdf/rapport_audit.pdf \
  --evidence output/evidence/audit.json
```

Le PDF et son manifeste peuvent ensuite être contrôlés sans relancer l'audit :

```bash
eu-ai-auditor-verify output/evidence/audit.json \
  --report output/pdf/rapport_audit.pdf
```

Audit de la décision réelle :

```bash
eu-ai-auditor-oversight data/oversight_demo.csv \
  --protected genre --protected-value Femme --reference-value Homme \
  --ai-recommendation recommandation_ia \
  --human-decision decision_humaine --favourable-value Favorable \
  --condition diplome --condition anciennete_annees \
  --ground-truth verite_terrain --ground-truth-favourable-value Favorable \
  --exposure ia_visible --exposed-value Visible --unexposed-value Masquée \
  --randomized-exposure \
  --appeal recours --appeal-value Oui --final-decision decision_finale \
  --decision-timestamp decision_at --final-timestamp final_at \
  --bootstrap-cluster case_id \
  --output output/pdf/rapport_oversight_parity.pdf \
  --evidence output/evidence/oversight_manifest.json
```

Créer aussi un paquet de recherche reproductible :

```bash
eu-ai-auditor data/recrutement_demo.csv \
  --protected genre --protected-value Femme \
  --additional-protected tranche_age \
  --decision selection --favourable-value Retenu \
  --condition diplome \
  --research-bundle output/research/audit-ro-crate.zip

eu-ai-auditor-research verify output/research/audit-ro-crate.zip
```

Une recette JSON téléchargée depuis l'interface peut relancer exactement le parcours :

```bash
eu-ai-auditor-research run data.csv audit-recipe.json --output-dir output/replayed
```

## Comment la CDD est calculée

Pour chaque strate légitime `R`, le moteur calcule :

```text
A_R = P(S = classe protégée | Y = issue favorable, R)
D_R = P(S = classe protégée | Y = issue défavorable, R)
CDD = D_R - A_R
```

Les statistiques conditionnelles sont agrégées en pondérant chaque strate par sa population. Une valeur positive indique que la classe protégée est proportionnellement plus présente dans les issues défavorables. Les strates qui n'atteignent pas l'effectif minimal dans chacune des deux issues sont affichées mais exclues de l'agrégat.

Le seuil de matérialité configurable déclenche une priorité de revue. Ce n'est pas un seuil juridique. Le choix de `R`, des groupes et de la portée de l'analyse doit être justifié et documenté.

L'intervalle de confiance utilise un bootstrap non paramétrique des lignes. Les strates, quantiles et règles d'éligibilité sont recalculés à chaque réplication. Si moins de 80 % des réplications sont exploitables, l'outil refuse d'afficher un intervalle.

## Mesures d'association des proxys

| Types de variables | Mesure |
|---|---|
| Numérique / numérique | valeur absolue de la corrélation de Pearson |
| Catégorielle / catégorielle | V de Cramér corrigé |
| Numérique / catégorielle | rapport de corrélation eta |

Les seuils par défaut sont `faible < 0,10`, `moyen < 0,30` et `haut >= 0,30`. Ils sont documentés comme paramètres de triage et peuvent être modifiés. Une association forte n'établit ni causalité, ni utilisation discriminatoire.

## Rapport AI Act

Le PDF contient :

- des indicateurs de complétude et de représentation pour l'article 10 ;
- les paramètres, métriques, limites et résultats de test utiles à l'article 11 et à l'annexe IV ;
- des instructions d'interprétation et les limites connues pour l'article 13 ;
- un cadre de supervision, d'annulation et d'escalade pour l'article 14 ;
- une liste explicite des éléments organisationnels restant à compléter.

Voir [la correspondance AI Act](docs/ai-act-mapping.md) et [la méthodologie](docs/methodology.md).

## Études de cas publiques

Deux jeux UCI sous CC BY 4.0 sont inclus avec leurs attributions et un script de préparation reproductible :

| Cas | Observations | Configuration CDD | Résultat descriptif |
|---|---:|---|---|
| Adult Income | 6 000 | `sex=Female`, conditionné par `education` | 26,2 %, IC95 % [23,4 % ; 28,6 %], couverture 93,4 % |
| South German Credit | 1 000 | `age_group=under_25`, conditionné par `employment_duration` | 6,8 %, IC95 % [2,1 % ; 11,4 %], couverture 100 % |

Ces valeurs démontrent le fonctionnement du logiciel. Adult prédit un revenu et ne constitue pas un jeu de recrutement. South German Credit date de 1973-1975 et suréchantillonne les mauvais risques. Aucun résultat ne doit être extrapolé à une population actuelle.

```bash
python examples/run_case_studies.py
```

Voir [les études de cas](docs/case-studies.md) et [les sources et licences](data/cases/SOURCES.md).

### Validation humain-IA

Le moteur a aussi été vérifié sur le jeu expérimental **Hybrid Hiring** de Microsoft : 38 400 jugements humains sur 9 600 tâches et sept conditions. Le script ne redistribue pas le classeur ; il télécharge l'archive officielle, contrôle son SHA-256 et conserve ensemble les bras d'une même biographie pendant le bootstrap.

```bash
pip install -e ".[research]"
python examples/validate_hybrid_hiring.py
```

Sur les trois modèles publiés, les intervalles bootstrap du Causal Automation Bias Gap recoupent zéro. La validation démontre donc le fonctionnement du protocole sans transformer une absence de preuve en preuve d'absence. Voir [le protocole et les résultats](docs/hybrid-hiring-validation.md).

## Manifeste de preuves

Les manifestes `eu-ai-auditor.evidence.v1` et `eu-ai-auditor.oversight-evidence.v1` ne copient aucune ligne source. Ils enregistrent :

- l'identifiant stable de l'audit et la version du logiciel ;
- l'empreinte SHA-256 du DataFrame, sa forme et ses colonnes ;
- les paramètres CDD, les métriques et les résultats ;
- l'empreinte et la taille du PDF ;
- l'empreinte canonique du manifeste ;
- une signature HMAC-SHA256 optionnelle, dont la clé reste hors du fichier.

Cette vérification détecte une modification ; elle ne fournit pas à elle seule une identité de signataire, un horodatage qualifié ou une certification réglementaire.

## Paquet de recherche interopérable

Le RO-Crate contient des résultats en format tabulaire stable et lisible depuis Python, R, Julia ou un tableur. Les données sources ne sont ajoutées que sur demande explicite. `checksums.sha256` protège chaque fichier utile ; `ro-crate-metadata.json` décrit la provenance et `metadata/croissant.json` décrit le schéma du jeu audité. Le paquet se vérifie sans relancer les calculs.

Le dépôt fournit aussi [`CITATION.cff`](CITATION.cff), rendu directement par GitHub pour faciliter la citation du logiciel.

## Positionnement

EU AI Auditor ne prétend pas inventer l'audit de biais ni être la seule implémentation de la CDD. [AIF360](https://github.com/Trusted-AI/AIF360) expose déjà `conditional_demographic_disparity`, [Fairlearn](https://fairlearn.org/) couvre de nombreuses métriques de groupe et [OxonFair](https://github.com/oxfordinternetinstitute/oxonfair) traite les arbitrages d'équité.

Le projet se concentre sur un angle encore peu outillé : relier dans un même objet vérifiable la disparité conditionnelle, les intersections, la décision humaine réelle, les overrides et l'accès effectif à la correction. La recherche et d'autres bibliothèques existent déjà ; la contribution logicielle est leur orchestration transparente, reproductible et orientée audit. Aucune revendication d'unicité absolue n'est faite sans étude d'antériorité. Voir [l'analyse de l'écosystème](docs/landscape.md).

## Architecture

```text
CSV tabulaire                       Journal de décisions
 ├─ qualité / représentation        ├─ recommandation IA
 ├─ CDD et proxys                   ├─ décision humaine
 ├─ quadrants                       ├─ recours / correction
 └─ frontière LR / CART             └─ exposition expérimentale
            └──────── rapport PDF + manifeste vérifiable ────────┘
```

Le traitement ne dépend d'aucune API externe. L'application Streamlit conserve les données en mémoire le temps de la session ; la sécurité du serveur et la politique de conservation restent sous la responsabilité du déployeur.

## Développement

```bash
pip install -e ".[dev]"
pytest
pytest --cov=eu_ai_auditor --cov-fail-under=80
ruff check .
python -m build
```

Les corrections doivent inclure un test de non-régression et préserver la distinction entre signal statistique et conclusion juridique. Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Références principales

- [Règlement (UE) 2024/1689 - texte officiel EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Wachter, Mittelstadt et Russell, *Why Fairness Cannot Be Automated*](https://arxiv.org/abs/2005.05906)
- [Deloitte, *Striving for fairness in AI models*](https://www.deloitte.com/content/dam/assets-zone2/de/de/docs/products/2024/Deloitte_Trustworthy20AI_Fairness_Whitepaper_Dec2021.pdf)
- [Fairlearn, *Intersecting groups*](https://fairlearn.org/main/user_guide/assessment/intersecting_groups.html)
- [RO-Crate Metadata Specification 1.3](https://www.researchobject.org/ro-crate/specification/1.3/)
- [MLCommons Croissant 1.1](https://docs.mlcommons.org/croissant/docs/croissant-spec-1.1.html)

## Licence

Le code est sous Apache License 2.0. Voir [LICENSE](LICENSE). Les CSV de `data/cases/` sont sous CC BY 4.0 avec les attributions détaillées dans [SOURCES.md](data/cases/SOURCES.md).
