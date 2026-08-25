# Méthodologie

## 1. Disparité démographique conditionnelle

Le moteur applique la présentation de Wachter, Mittelstadt et Russell. Pour une classe protégée `S=s`, une décision binaire et une strate légitime `R` :

- `A_R` est la proportion de la classe protégée parmi les personnes ayant reçu l'issue favorable dans la strate ;
- `D_R` est la proportion de la classe protégée parmi les personnes ayant reçu l'issue défavorable dans la strate ;
- l'écart descriptif est `D_R - A_R`.

Lorsque `R` est numérique et contient plus de dix valeurs distinctes, le moteur crée par défaut cinq quantiles. Cette transformation est consignée dans les notes du résultat. Chaque strate est pondérée par son effectif total pour calculer les deux parts agrégées. Cette pondération reproduit l'approche descriptive exposée dans l'exemple des admissions de Berkeley.

Une strate est exclue de l'agrégat si l'une des issues contient moins que l'effectif minimal configuré. Elle reste présente dans la table afin que la perte de couverture soit visible.

### Incertitude par bootstrap

Lorsque le bootstrap est activé, l'outil tire avec remise autant de lignes que le jeu d'origine et recalcule toute la procédure : nettoyage des colonnes requises, discrétisation éventuelle, éligibilité des strates, pondération et CDD. L'intervalle bilatéral est obtenu par les quantiles empiriques de la distribution des CDD valides.

Le générateur exige au moins 30 réplications valides et 80 % du nombre demandé. Cette règle évite d'afficher un intervalle construit principalement sur des rééchantillonnages où des groupes ou issues auraient disparu. L'intervalle décrit l'incertitude d'échantillonnage sous les choix de modèle d'audit ; il ne couvre pas l'incertitude juridique, le biais de sélection ou une mauvaise spécification de `R`.

### Interprétation

Une valeur positive de `D_R - A_R` est un signal directionnel défavorable à la classe protégée. Le logiciel distingue :

1. le signal directionnel (`gap > 0`) ;
2. le signal matériel au regard d'un seuil interne configurable ;
3. la conclusion juridique, qui n'est jamais produite par le logiciel.

La littérature CDD insiste sur ce troisième point : l'outil décrit l'ampleur et la structure de l'écart pour guider une investigation contextuelle.

## 2. Matrice des proxys

Les associations sont calculées sur les paires complètes :

- Pearson en valeur absolue pour deux variables numériques ;
- V de Cramér avec correction du biais de petit échantillon pour deux variables catégorielles ;
- eta pour un couple numérique-catégoriel.

Les scores sont normalisés entre 0 et 1. Ils ne sont pas directement comparables comme estimateurs causaux. Les catégories faible, moyen et haut servent à classer l'ordre de revue. Une investigation de proxy doit ensuite considérer la nécessité métier, la causalité, les interactions du modèle et le contexte juridique.

## 3. Quadrants d'impact

Pour chaque valeur d'une variable protégée, l'écart de résultat vaut :

```text
taux d'issue favorable du groupe - taux d'issue favorable de la population
```

Le point de chaque variable protégée utilise :

- en abscisse, la moyenne des écarts absolus pondérée par la taille des groupes ;
- en ordonnée, l'écart absolu maximal.

Deux seuils configurables séparent impact faible, impact élevé, sous-groupes marginalisés et biais extrême. Ces libellés suivent le cadre visuel de Deloitte ; ils restent des catégories de priorisation.

## 4. Frontière performance-équité

Les variables protégées sont retirées des entrées du modèle. Le module sépare les données en entraînement et test, ajuste plusieurs régressions logistiques et arbres CART, puis évalue plusieurs seuils de décision.

La performance est l'exactitude équilibrée. Le coût d'équité est la valeur absolue de la CDD calculée sur les prédictions de test. Un point appartient à la frontière de Pareto si aucun autre n'obtient simultanément une meilleure performance et un coût d'équité inférieur.

La frontière rend l'arbitrage visible. Elle ne recommande aucun point et ne fixe aucune pondération entre les objectifs.

## 5. Traçabilité et intégrité

Le manifeste versionné contient une empreinte du DataFrame construite à partir de l'ordre des colonnes, des types, de l'index et du hachage des valeurs. Le PDF est protégé par sa propre empreinte SHA-256. Le manifeste retire son bloc `integrity`, sérialise le reste en JSON canonique puis calcule son empreinte.

Une clé fournie par l'opérateur peut ajouter un HMAC-SHA256. La clé n'est jamais écrite dans le manifeste. Cette méthode permet de détecter une altération et d'attester la possession d'un secret partagé ; elle ne remplace pas une signature électronique qualifiée, une infrastructure de clés publiques, un horodatage de confiance ou une politique de conservation.

## 6. Menaces à la validité

- choix inadéquat ou contestable des facteurs `R` ;
- échantillons trop petits, non représentatifs ou avec données manquantes non aléatoires ;
- catégories protégées incomplètes ou inférées avec erreur ;
- dérive entre la période auditée et la période de déploiement ;
- causalité non identifiable par une association bivariée ;
- multiples analyses exploratoires créant des signaux fortuits ;
- confusion entre une mesure sur les données historiques et les effets réels du système.
- dépendance du bootstrap à l'hypothèse que les lignes observées sont une approximation pertinente de la population auditée.
