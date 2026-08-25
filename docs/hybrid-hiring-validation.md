# Validation externe : Microsoft Hybrid Hiring

## Source

Hybrid Hiring accompagne l'article de Peng et al., *Investigations of Performance and Bias in Human-AI Teamwork in Hiring* (AAAI 2022). La page Microsoft décrit 38 400 jugements humains sur 9 600 tâches de prédiction et sept conditions expérimentales.

- page de publication : <https://www.microsoft.com/en-us/research/publication/investigations-of-performance-and-bias-in-human-ai-teamwork-in-hiring/>
- archive officielle : <https://download.microsoft.com/download/f/2/e/f2e0d694-7b0f-4fa6-a436-2e4421796ef3/hybridhiring.zip>
- SHA-256 contrôlé : `ec2c7f0209e39312392f05582dbcfa389de6b62835dcb5d866d190feb6c839eb`
- article : <https://arxiv.org/abs/2202.11812>

Le dépôt ne redistribue pas le classeur. Le script `examples/validate_hybrid_hiring.py` le télécharge à la demande, vérifie son empreinte et analyse localement son contenu. Les conditions de réutilisation de la source doivent être vérifiées par l'utilisateur avant toute redistribution.

## Transformation

Pour chaque biographie et pour chacun des modèles DNN, bag-of-words et aléatoire :

1. la cible favorable vaut 1 lorsque la profession prédite correspond à la profession testée ;
2. la recommandation du modèle est calculée une seule fois ;
3. la prédiction `human_only` forme le bras non exposé ;
4. la prédiction `human_<model>` forme le bras exposé ;
5. le sexe de la biographie est l'attribut de groupe ;
6. la profession testée est utilisée comme facteur `R` ;
7. le bootstrap est groupé par biographie afin de conserver les deux bras ensemble.

Cette transformation produit 19 200 lignes par modèle à partir de 9 600 cas uniques. Elle mesure l'influence d'une aide à la classification dans le protocole publié ; elle ne simule pas un recrutement réel et n'étudie aucun recours.

## Résultats

Les valeurs ci-dessous utilisent 100 réplications bootstrap groupées et un intervalle percentile à 95 %.

| Assistance | Écart IA F-M | Écart humain F-M | Causal Automation Bias Gap | IC95 % du CABG |
|---|---:|---:|---:|---:|
| DNN | -1,29 % | -0,67 % | -1,29 % | [-3,96 % ; 1,26 %] |
| Bag-of-words | -1,38 % | -0,27 % | -0,50 % | [-3,27 % ; 2,10 %] |
| Aléatoire | -1,79 % | -0,86 % | -1,69 % | [-4,43 % ; 0,63 %] |

Les trois intervalles CABG recoupent zéro. Ces analyses ne mettent donc pas en évidence, à ce niveau d'agrégation, un effet différentiel précis de la visibilité de l'IA entre biographies féminines et masculines. Elles valident la capacité du moteur à :

- représenter des bras exposés et non exposés ;
- standardiser par type de tâche ;
- conserver l'appariement pendant le bootstrap ;
- publier une incertitude qui empêche de présenter un petit écart comme une découverte.

## Reproduction

```bash
pip install -e ".[research]"
python examples/validate_hybrid_hiring.py --bootstrap-iterations 100
```

Le JSON généré dans `output/evidence/hybrid_hiring_validation.json` est ignoré par Git : il peut être régénéré depuis l'archive officielle.

## Limites

- Les professions prédites ne sont pas des décisions d'embauche.
- Le sexe est limité aux catégories `F` et `M` présentes dans la source.
- Le protocole ne contient pas de recours, de décision finale organisationnelle ni de délai de correction.
- Les résultats dépendent de la transformation binaire « profession testée ou non ».
- La déclaration causale repose sur le plan expérimental décrit par les auteurs et doit être relue à partir du protocole complet avant réutilisation académique.
