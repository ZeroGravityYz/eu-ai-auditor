# Changelog

Toutes les modifications importantes du projet sont consignées ici.

## 0.5.0 — 2026-09-05

### Ajouté

- Analyse multivers de la CDD sur toutes les combinaisons pré-déclarées de facteurs `R` jusqu'à une profondeur bornée.
- Courbe de spécifications reliée à une matrice visuelle d'inclusion des facteurs.
- Score de robustesse combinant consensus de conclusion et couverture médiane, avec contrôle séparé de la part de spécifications calculables.
- Mesure de l'influence de chaque facteur : décalage médian, amplitude maximale et fréquence de bascule de conclusion.
- Résultats de stabilité dans Streamlit, le Research Workbench bilingue, le CLI, le PDF, le manifeste JSON et le RO-Crate.

### Garde-fous

- Les facteurs candidats doivent être justifiés et déclarés avant interprétation ; aucun facteur n'est optimisé en fonction du résultat souhaité.
- L'univers est limité à 256 spécifications pour éviter une exploration incontrôlée.
- La robustesse de la conclusion d'audit n'est présentée ni comme une preuve de causalité, ni comme la robustesse technique du système au sens de l'article 15, ni comme un verdict juridique.

## 0.4.0 — 2026-09-05

### Ajouté

- Research Workbench bilingue avec suggestion conservatrice du schéma de données.
- Audit intersectionnel avec intervalles de Wilson, tests exacts de Fisher et correction de Benjamini-Hochberg.
- Export de recherche privé par défaut au format RO-Crate 1.3 avec métadonnées Croissant 1.1 et CFF 1.2.
- Commande `eu-ai-auditor-research` pour inférer un schéma, vérifier un crate ou rejouer une recette d'audit.
- Résultats intersectionnels dans les rapports PDF et manifestes de preuve.
- Recettes JSON téléchargeables pour reproduire un audit hors de Streamlit.

### Modifié

- Sécurisation de l'état Streamlit : les résultats obsolètes sont invalidés dès qu'un paramètre change.
- Signatures de configuration complètes pour les audits classique et OversightParity.
- Lecture CSV plus tolérante aux encodages courants.
- Sérialisation JSON stricte : les valeurs scientifiques non finies deviennent `null`.
- Liste blanche du paquet source pour exclure les artefacts locaux et accélérer les builds.
- Version du paquet portée à 0.4.0 et documentation internationale ajoutée.

### Garde-fous

- Les données sources ne sont jamais incluses dans un crate sans consentement explicite.
- Les petits groupes restent visibles mais sont exclus des affirmations inférentielles.
- Les sorties demeurent des preuves d'audit et non une certification ou une conclusion juridique automatisée.
