# EU AI Auditor

EU AI Auditor est un package Python et une application Streamlit pour produire des preuves statistiques de biais dans les systèmes de décision. Il réunit quatre analyses dans un flux léger et reproductible :

- la disparité démographique conditionnelle (CDD) proposée comme mesure descriptive par Wachter, Mittelstadt et Russell ;
- une matrice de risque de proxys inspirée de l'approche présentée par Deloitte ;
- les quadrants d'impact des variables protégées ;
- une frontière performance-équité comparant régression logistique et arbre CART.

Le rapport PDF organise les résultats comme éléments de travail pour les articles 10, 11, 13 et 14 du règlement (UE) 2024/1689. Il ne certifie pas la conformité et ne remplace ni l'analyse juridique, ni l'évaluation des risques, ni la gouvernance interne.

## Démarrage rapide

Prérequis : Python 3.10 ou plus récent.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app.py
```

L'application s'ouvre avec un jeu de recrutement synthétique. Il est possible de déposer un CSV, de sélectionner l'issue favorable, une classe protégée et un ou plusieurs facteurs légitimes de conditionnement `R`.

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
  --output output/pdf/rapport_audit.pdf \
  --json output/resultats.json
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

## Architecture

```text
CSV
 ├─ profil de qualité et représentation
 ├─ moteur CDD
 ├─ matrice des proxys
 ├─ quadrants d'impact
 └─ comparaison LR / CART
        └─ rapport PDF + résultats JSON
```

Le traitement ne dépend d'aucune API externe. L'application Streamlit conserve les données en mémoire le temps de la session ; la sécurité du serveur et la politique de conservation restent sous la responsabilité du déployeur.

## Développement

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Les corrections doivent inclure un test de non-régression et préserver la distinction entre signal statistique et conclusion juridique. Voir [CONTRIBUTING.md](CONTRIBUTING.md).

## Références principales

- [Règlement (UE) 2024/1689 - texte officiel EUR-Lex](https://eur-lex.europa.eu/eli/reg/2024/1689/oj)
- [Wachter, Mittelstadt et Russell, *Why Fairness Cannot Be Automated*](https://arxiv.org/abs/2005.05906)
- [Deloitte, *Striving for fairness in AI models*](https://www.deloitte.com/content/dam/assets-zone2/de/de/docs/products/2024/Deloitte_Trustworthy20AI_Fairness_Whitepaper_Dec2021.pdf)

## Licence

Apache License 2.0. Voir [LICENSE](LICENSE).


