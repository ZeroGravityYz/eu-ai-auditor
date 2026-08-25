# OversightParity : spécification scientifique

## Objet

OversightParity audite un système de décision sociotechnique plutôt que le seul modèle. L'unité d'analyse est un événement ou un cas permettant de relier une recommandation automatique à une décision humaine et, lorsque les données existent, à une contestation et une correction.

Le moteur distingue trois formes de justice :

1. la justice distributive, observée dans les taux de décisions favorables ;
2. la justice procédurale, observée dans l'exposition à l'IA, les overrides et l'accès au recours ;
3. la réparation, observée dans la probabilité et le délai de correction.

Il ne détermine pas si une différence est juridiquement discriminatoire.

## Schéma minimal

| Rôle | Colonne type | Obligatoire | Interprétation |
|---|---|---:|---|
| identifiant de cas | `case_id` | recommandé | conserve les bras appariés pendant le bootstrap |
| attribut protégé | `genre` | oui | groupe protégé et groupe de référence explicitement choisis |
| facteurs légitimes | `diplome`, `anciennete` | non | strates `R` utilisées pour la standardisation |
| recommandation IA | `recommandation_ia` | oui | recommandation disponible, visible ou non |
| décision humaine | `decision_humaine` | oui | décision initialement appliquée par le réviseur |
| vérité terrain | `verite_terrain` | non | permet d'identifier corrections utiles et erreurs introduites |
| exposition à l'IA | `ia_visible` | non | bras avec et sans recommandation visible |
| recours | `recours` | non | indique qu'une décision défavorable a été contestée |
| décision finale | `decision_finale` | non | résultat après contestation ou nouvelle revue |
| horodatages | `decision_at`, `final_at` | non | permettent une mesure de correction dans un délai cible |
| réviseur | `reviewer_id` | non | utile à une investigation organisationnelle contrôlée |

Les justifications, textes d'explication et identifiants individuels ne sont pas nécessaires aux métriques. Ils doivent rester dans un environnement à accès contrôlé s'ils contiennent des données personnelles.

## Standardisation conditionnelle

Soit `S` le groupe, `R` un ensemble de facteurs légitimes, `M` la recommandation IA binaire, `H` la décision humaine initiale et `F` la décision finale. Pour une étape `Z`, le moteur calcule dans chaque strate commune :

```text
p_Z(s, r) = P(Z = favorable | S = s, R = r)
```

Les taux par groupe sont ensuite standardisés sur la distribution groupée des dénominateurs des strates éligibles. Une strate est exclue lorsqu'un groupe n'atteint pas l'effectif minimal configuré. La couverture publiée indique la part des observations conservées.

L'écart d'étape est :

```text
Delta_Z = p_Z(protégé) - p_Z(référence)
```

## Fairness Transfer

Le transfert signé indique comment la direction de l'écart change entre l'IA et la décision humaine :

```text
T_signed = Delta_H - Delta_M
```

L'amplification mesure uniquement l'augmentation de la distance entre les groupes :

```text
T_amplification = |Delta_H| - |Delta_M|
```

Une amplification positive signifie que l'intervention humaine augmente la disparité absolue. Une valeur négative signifie qu'elle la réduit, sans démontrer que la décision est juste.

## Equitable Error Correction

Lorsque la vérité terrain `Y` est disponible :

```text
Helpful_s = P(H = Y | M != Y, S = s, R)
Harmful_s = P(H != Y | M = Y, S = s, R)
```

La première mesure la correction d'une erreur IA. La seconde mesure une erreur introduite après une recommandation correcte. La qualité et la légitimité de `Y` doivent être auditées séparément : une vérité terrain historique peut reproduire des biais institutionnels.

## Causal Automation Bias Gap

Soit `E` l'exposition à la recommandation IA. Pour chaque groupe :

```text
tau_s = P(H = favorable | E = 1, S = s, R)
      - P(H = favorable | E = 0, S = s, R)

CABG = tau_protégé - tau_référence
```

Le CABG mesure si rendre la recommandation visible modifie différemment les décisions humaines selon le groupe.

La lecture est causale uniquement si :

- l'affectation à `E` est réellement randomisée ou satisfait une hypothèse d'ignorabilité défendable ;
- les bras ne subissent pas d'attrition différentielle ;
- les mêmes définitions et règles de mesure sont utilisées dans les deux bras ;
- l'interférence entre cas est négligeable ;
- le protocole et ses déviations sont conservés comme preuves.

Le simple fait de cocher l'option dans l'outil ne prouve pas ces conditions. Cette déclaration est enregistrée pour rendre la responsabilité explicite.

## Conditional Remedy Parity

Le dénominateur est constitué de toutes les décisions humaines initialement défavorables, et non des seuls recours déposés :

```text
Appeal_s = P(recours | H = défavorable, S = s, R)
Remedy_s = P(F = favorable | H = défavorable, S = s, R)
Timely_s = P(F = favorable et délai <= q | H = défavorable, S = s, R)
```

Cette convention permet de distinguer l'accès au mécanisme, son efficacité et sa rapidité. Elle ne mesure pas les personnes qui ignoraient la possibilité de contester ou qui ont abandonné avant l'enregistrement du recours ; ces parcours doivent faire l'objet d'une collecte complémentaire.

## Incertitude

Le bootstrap recalcule les strates, les règles d'éligibilité et toutes les métriques. Lorsqu'un identifiant de cas est fourni, les lignes d'un même cas sont rééchantillonnées ensemble. Un intervalle n'est affiché que si au moins 30 réplications et 80 % des réplications demandées fournissent une estimation exploitable.

Les intervalles sont des intervalles percentiles descriptifs. Les déploiements à fort enjeu peuvent nécessiter un plan d'analyse préenregistré, une correction de multiplicité, des modèles hiérarchiques et une revue statistique indépendante.

## Interprétation AI Act

- **Article 12** : le journal doit permettre de relier recommandation, exposition, intervention humaine et décision finale.
- **Article 13** : la personne concernée et le déployeur doivent comprendre le rôle effectif de l'IA.
- **Article 14** : la supervision effective implique davantage qu'un bouton d'override ; son fonctionnement et ses effets doivent être testés.
- **Article 86** : le rapport peut documenter le rôle de l'IA et les principaux éléments de la décision, mais n'automatise pas la réponse individuelle ni les autres voies de droit applicables.

Texte officiel : <https://eur-lex.europa.eu/eli/reg/2024/1689/oj>

## Limites

- Les résultats portent sur les groupes et le périmètre observés.
- Un faible écart agrégé peut masquer des sous-groupes intersectionnels.
- Les facteurs `R` sont des choix normatifs et juridiques, pas de simples réglages techniques.
- Une recommandation non visible dans le journal ne garantit pas qu'aucune autre information algorithmique n'a influencé le réviseur.
- L'absence de recours enregistré n'est pas nécessairement un consentement à la décision.
- Aucune métrique ne remplace la consultation des personnes affectées.

## Références

- Peng et al., *Investigations of Performance and Bias in Human-AI Teamwork in Hiring*, AAAI 2022 : <https://arxiv.org/abs/2202.11812>
- Green et Chen, *On the Fairness of Machine-Assisted Human Decisions* : <https://arxiv.org/abs/2110.15310>
- Commission européenne, *The impact of human oversight on discrimination in AI-supported decision-making* : <https://op.europa.eu/en/publication-detail/-/publication/68b91f8f-cf0a-11ef-be2a-01aa75ed71a1/language-en>
- Règlement (UE) 2024/1689 : <https://eur-lex.europa.eu/eli/reg/2024/1689/oj>
