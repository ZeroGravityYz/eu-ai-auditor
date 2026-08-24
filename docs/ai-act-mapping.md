# Correspondance avec le règlement (UE) 2024/1689

Cette correspondance décrit les éléments produits par EU AI Auditor et les lacunes à compléter. Elle ne constitue pas une interprétation juridique exhaustive.

| Exigence | Éléments produits | Éléments restant sous responsabilité humaine |
|---|---|---|
| Article 10 - données et gouvernance | taux de valeurs manquantes, doublons, profils de colonnes, représentation des groupes, signaux CDD et proxys | provenance, base juridique, finalité initiale, choix de collecte, annotation, nettoyage, adéquation géographique et fonctionnelle, garanties pour catégories particulières |
| Article 11 - documentation technique | paramètres d'audit, empreinte du jeu, métriques, résultats datés, limites, checklist annexe IV | description complète du système, architecture, ressources, standards, signatures, déclaration UE de conformité, historique des changements |
| Article 13 - transparence | finalité saisie, performances mesurées, limites, instructions d'interprétation, mauvais usages prévisibles | notice déployeur validée, cybersécurité, maintenance, durée de vie, mécanismes de journaux |
| Article 14 - supervision humaine | cadre de surveillance, annulation, interruption, escalade et traçabilité | rôles nominatifs, compétences, formation, autorité, disponibilité et procédures opérationnelles testées |
| Annexe IV | checklist de complétude et preuves d'essais statistiques | dossier complet, gestion des risques, suivi après mise sur le marché, normes et validation par les responsables |

## Principe de rédaction

Le rapport utilise l'expression « dossier de preuves » ou « documentation technique partielle ». Il n'affiche jamais « conforme » sur la seule base d'un indicateur statistique. L'article 11 exige que la documentation permette aux autorités d'évaluer la conformité ; cette évaluation ne peut pas être remplacée par le générateur.

## Protection des données

L'article 10(5) prévoit un régime exceptionnel et encadré pour le traitement de catégories particulières strictement nécessaire à la détection et à la correction de biais des systèmes à haut risque. Le logiciel n'établit pas que ces conditions sont remplies. Le déployeur doit notamment documenter la nécessité, les alternatives, les contrôles d'accès, la sécurité, la non-transmission et l'effacement.

