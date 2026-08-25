# Études de cas reproductibles

Les deux cas ci-dessous vérifient le parcours complet : CSV, qualité, CDD avec intervalle bootstrap, proxys, quadrants, frontière LR/CART, PDF et manifeste d'intégrité. Ils illustrent le logiciel et ne constituent pas des audits de systèmes actuellement déployés.

## 1. Adult Income

Le jeu Adult de l'UCI contient 48 842 observations extraites du Census américain de 1994. Le dépôt conserve un échantillon stratifié déterministe de 6 000 lignes. La cible indique si le revenu annuel dépasse 50 000 USD.

Configuration :

- classe protégée examinée : `sex=Female` ;
- issue favorable : `income=>50K` ;
- facteur de conditionnement : `education` ;
- autres attributs examinés par les proxys et quadrants : `race` ;
- 250 réplications bootstrap, IC 95 %, seuil de matérialité 5 %.

Résultat observé lors de la validation de la version 0.2.0 : CDD `26,2 %`, IC95 % `[23,4 % ; 28,6 %]`, couverture `93,4 %`, quatre relations classées à haut risque de proxy.

Interprétation prudente : dans l'échantillon et après conditionnement par l'éducation, la catégorie `Female` représente une part plus élevée des revenus `<=50K` que des revenus `>50K`. Le jeu ne décrit pas une décision de recrutement et ne permet pas d'attribuer une cause ou une illégalité.

## 2. South German Credit

La version UCI de 2019 corrige des erreurs de codage du jeu German Credit classique. Elle contient 1 000 crédits historiques de 1973-1975, avec 700 bons et 300 mauvais risques. Les mauvais risques ont été suréchantillonnés.

Configuration :

- classe protégée examinée : `age_group=under_25` ;
- issue favorable : `credit_risk=good` ;
- facteur de conditionnement : `employment_duration` ;
- autre attribut examiné : `foreign_worker` ;
- 250 réplications bootstrap, IC 95 %, seuil de matérialité 5 %.

Résultat observé lors de la validation de la version 0.2.0 : CDD `6,8 %`, IC95 % `[2,1 % ; 11,4 %]`, couverture `100 %`, deux relations classées à haut risque de proxy.

L'estimation ponctuelle dépasse le seuil interne de 5 %, mais l'intervalle le recoupe. Le rapport qualifie donc explicitement l'incertitude. L'âge brut est naturellement un proxy très fort de la tranche d'âge ; ce résultat sert aussi de contrôle positif pour la matrice.

## Reproduction

```bash
python scripts/prepare_public_cases.py
python examples/run_case_studies.py
eu-ai-auditor-verify output/evidence/case_adult_income.json \
  --report output/pdf/case_adult_income.pdf
```

Les DOI, licences, empreintes d'archives et transformations figurent dans [`data/cases/SOURCES.md`](../data/cases/SOURCES.md) et [`data/cases/manifest.json`](../data/cases/manifest.json).
