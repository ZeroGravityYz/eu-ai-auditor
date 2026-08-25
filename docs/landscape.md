# Positionnement dans l'écosystème

EU AI Auditor est un outil d'intégration et de documentation, pas la première bibliothèque d'équité algorithmique.

| Projet | Force principale | Différence avec EU AI Auditor |
|---|---|---|
| [AIF360](https://github.com/Trusted-AI/AIF360) | catalogue étendu de métriques et méthodes de mitigation, dont une fonction CDD | EU AI Auditor rend le choix des facteurs `R`, les strates, la couverture et l'intervalle bootstrap visibles dans une interface et un rapport |
| [Fairlearn](https://fairlearn.org/) | métriques de groupe et réduction des contraintes d'équité | EU AI Auditor ajoute la matrice de proxys et le dossier AI Act |
| [OxonFair](https://github.com/oxfordinternetinstitute/oxonfair) | optimisation et post-traitement pour de nombreux modèles | EU AI Auditor vise un audit tabulaire léger et documenté plutôt que la mitigation avancée |
| [EuConform](https://github.com/Hiepler/EuConform) | format de preuves et préparation générale à l'AI Act | EU AI Auditor se concentre sur les disparités de décisions tabulaires et le conditionnement CDD |
| [CHAP](https://github.com/BrightbeamAI/chap) | protocole et journal d'approbations ou d'overrides humain-agent | OversightParity calcule les disparités de résultat, de correction et de recours par groupe sur des journaux décisionnels |

La recherche sur la fairness des équipes humain-IA précède OversightParity. Peng et al. publient Hybrid Hiring et Green et Chen analysent formellement les décisions humaines assistées. La Commission européenne a également étudié le contrôle humain dans des scénarios de recrutement et de crédit. Le projet ne revendique donc pas l'invention du sujet.

La contribution visée est plus précise : un package Python léger réunissant une standardisation conditionnelle, un contraste d'exposition explicitement causal ou associatif, la décomposition des corrections utiles et nuisibles, l'accès au recours, le bootstrap apparié et un dossier de preuves orienté AI Act.

## Niche visée

Le projet est pertinent pour un premier diagnostic reproductible par une équipe données, risque, conformité ou audit qui dispose d'un CSV de décisions ou d'un journal reliant recommandation et décision humaine. Sa valeur vient de la réunion des analyses, de garde-fous explicites, d'un rapport lisible et d'un manifeste vérifiable.

Il n'est pas adapté comme unique preuve de conformité, outil de décision individuelle, certification ou substitut à l'analyse de la base juridique et des mesures organisationnelles. Son contraste d'exposition n'a une interprétation causale que dans un protocole randomisé ou lorsque des hypothèses causales équivalentes sont défendables et documentées.
