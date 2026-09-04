# Changelog

Toutes les modifications importantes du projet sont consignées ici.

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
