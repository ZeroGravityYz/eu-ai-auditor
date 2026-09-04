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

## 2. Analyse intersectionnelle

L'analyse intersectionnelle décrit chaque combinaison observée des attributs protégés sélectionnés. Pour chaque groupe, le moteur calcule l'effectif, le nombre d'issues favorables, le taux d'issue favorable et un intervalle de Wilson. Les lignes dont une valeur protégée manque sont exclues du dénominateur complet-case ; leur nombre reste consigné dans le résultat.

Chaque groupe éligible est comparé au reste de la population complète-case par un test exact bilatéral de Fisher. Les valeurs p sont ensuite corrigées ensemble par la procédure de Benjamini-Hochberg. Une priorité de revue n'est déclenchée que si trois conditions sont réunies :

1. l'effectif du groupe atteint le minimum configuré ;
2. l'écart absolu au taux global atteint le seuil de matérialité ;
3. la valeur q est inférieure ou égale au niveau FDR configuré.

Les groupes trop petits restent visibles mais ne reçoivent ni valeur p ni valeur q. Cette convention évite de transformer une puissance statistique insuffisante en conclusion rassurante. L'écart extrême est la différence entre les taux maximal et minimal parmi les groupes éligibles.

Les comparaisons groupe-contre-reste se chevauchent et ne sont donc pas indépendantes. Benjamini-Hochberg limite la proportion attendue de fausses découvertes dans la famille testée, mais ne corrige ni la sélection des variables, ni les erreurs de mesure, ni la multiplicité de plusieurs audits successifs.

## 3. Matrice des proxys

Les associations sont calculées sur les paires complètes :

- Pearson en valeur absolue pour deux variables numériques ;
- V de Cramér avec correction du biais de petit échantillon pour deux variables catégorielles ;
- eta pour un couple numérique-catégoriel.

Les scores sont normalisés entre 0 et 1. Ils ne sont pas directement comparables comme estimateurs causaux. Les catégories faible, moyen et haut servent à classer l'ordre de revue. Une investigation de proxy doit ensuite considérer la nécessité métier, la causalité, les interactions du modèle et le contexte juridique.

## 4. Quadrants d'impact

Pour chaque valeur d'une variable protégée, l'écart de résultat vaut :

```text
taux d'issue favorable du groupe - taux d'issue favorable de la population
```

Le point de chaque variable protégée utilise :

- en abscisse, la moyenne des écarts absolus pondérée par la taille des groupes ;
- en ordonnée, l'écart absolu maximal.

Deux seuils configurables séparent impact faible, impact élevé, sous-groupes marginalisés et biais extrême. Ces libellés suivent le cadre visuel de Deloitte ; ils restent des catégories de priorisation.

## 5. Frontière performance-équité

Les variables protégées sont retirées des entrées du modèle. Le module sépare les données en entraînement et test, ajuste plusieurs régressions logistiques et arbres CART, puis évalue plusieurs seuils de décision.

La performance est l'exactitude équilibrée. Le coût d'équité est la valeur absolue de la CDD calculée sur les prédictions de test. Un point appartient à la frontière de Pareto si aucun autre n'obtient simultanément une meilleure performance et un coût d'équité inférieur.

La frontière rend l'arbitrage visible. Elle ne recommande aucun point et ne fixe aucune pondération entre les objectifs.

## 6. Traçabilité et intégrité

Le manifeste versionné contient une empreinte du DataFrame construite à partir de l'ordre des colonnes, des types, de l'index et du hachage des valeurs. Le PDF est protégé par sa propre empreinte SHA-256. Le manifeste retire son bloc `integrity`, sérialise le reste en JSON canonique puis calcule son empreinte.

Une clé fournie par l'opérateur peut ajouter un HMAC-SHA256. La clé n'est jamais écrite dans le manifeste. Cette méthode permet de détecter une altération et d'attester la possession d'un secret partagé ; elle ne remplace pas une signature électronique qualifiée, une infrastructure de clés publiques, un horodatage de confiance ou une politique de conservation.

## 7. Objet de recherche portable

L'export de recherche assemble la configuration exacte, les résultats tabulaires, le manifeste de preuve, l'environnement logiciel et les métadonnées dans une archive ZIP structurée comme un RO-Crate 1.3. Un fichier Croissant 1.1 décrit le schéma du jeu de données et `CITATION.cff` rend le logiciel citable.

Les données sources sont absentes par défaut. Si l'opérateur choisit explicitement de les inclure, leur copie CSV est ajoutée et référencée dans les métadonnées. Le fichier `checksums.sha256` couvre les charges utiles ; le vérificateur contrôle également les chemins, les doublons, le JSON du crate et l'intégrité du manifeste.

Une empreinte ne garantit pas à elle seule l'authenticité, la confidentialité, l'archivage à long terme ou la reproductibilité sémantique. Le protocole permet surtout de détecter les divergences et de transmettre les choix d'audit sans dépendre de l'interface graphique.

## 8. Menaces à la validité

- choix inadéquat ou contestable des facteurs `R` ;
- échantillons trop petits, non représentatifs ou avec données manquantes non aléatoires ;
- catégories protégées incomplètes ou inférées avec erreur ;
- dérive entre la période auditée et la période de déploiement ;
- causalité non identifiable par une association bivariée ;
- multiples analyses exploratoires créant des signaux fortuits ;
- confusion entre une mesure sur les données historiques et les effets réels du système.
- dépendance du bootstrap à l'hypothèse que les lignes observées sont une approximation pertinente de la population auditée.
- dépendance entre comparaisons intersectionnelles et inflation du risque d'erreur si plusieurs configurations sont explorées sans protocole préalable.
- risque de réidentification lors de l'export de petits groupes, même lorsque les lignes sources ne sont pas incluses.
