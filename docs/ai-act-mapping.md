# Correspondance avec le règlement (UE) 2024/1689

Cette correspondance décrit les éléments produits par EU AI Auditor et les lacunes à compléter. Elle ne constitue pas une interprétation juridique exhaustive.

| Exigence | Éléments produits | Éléments restant sous responsabilité humaine |
|---|---|---|
| Article 10 - données et gouvernance | taux de valeurs manquantes, doublons, profils de colonnes, représentation des groupes, signaux CDD et proxys | provenance, base juridique, finalité initiale, choix de collecte, annotation, nettoyage, adéquation géographique et fonctionnelle, garanties pour catégories particulières |
| Article 11 - documentation technique | paramètres d'audit, identifiant stable, empreintes du jeu et du PDF, manifeste versionné, métriques, résultats datés, limites, checklist annexe IV | description complète du système, architecture, ressources, standards, signatures qualifiées, déclaration UE de conformité, historique des changements |
| Article 12 - journaux | schéma OversightParity reliant recommandation, exposition, décision humaine, recours, décision finale et horodatages | configuration effective des journaux, durée de conservation, contrôle d'accès, sécurité, représentativité et traitement des incidents |
| Article 13 - transparence | finalité saisie, performances mesurées, limites, instructions d'interprétation, mauvais usages prévisibles | notice déployeur validée, cybersécurité, maintenance, durée de vie, mécanismes de journaux |
| Article 14 - supervision humaine | concordance humain-IA, corrections utiles, erreurs introduites, effet différentiel de l'exposition, cadre d'annulation, escalade et traçabilité | preuve du protocole d'affectation, rôles nominatifs, compétences, formation, autorité, disponibilité et procédures opérationnelles testées |
| Article 15 - exactitude, robustesse et cybersécurité | stabilité de la conclusion CDD entre spécifications analytiques, couverture et hypothèses documentées | essais de robustesse du système, tolérance aux erreurs, sécurité, résilience, métriques d'exactitude propres à la finalité et validation en conditions de déploiement |
| Article 86 - explication individuelle | documentation du rôle effectif de l'IA dans la chaîne et des principaux résultats agrégés du processus | explication claire adressée à la personne, examen du champ d'application, secret d'affaires, autres droits de contestation et réponse au cas individuel |
| Annexe IV | checklist de complétude et preuves d'essais statistiques | dossier complet, gestion des risques, suivi après mise sur le marché, normes et validation par les responsables |

## Principe de rédaction

Le rapport utilise l'expression « dossier de preuves » ou « documentation technique partielle ». Il n'affiche jamais « conforme » sur la seule base d'un indicateur statistique. L'article 11 exige que la documentation permette aux autorités d'évaluer la conformité ; cette évaluation ne peut pas être remplacée par le générateur.

Le manifeste d'intégrité facilite la conservation et la comparaison des exécutions. Il ne prouve pas que les métadonnées saisies sont vraies, que l'auteur est juridiquement identifié ou que le dossier est complet.

La « robustesse » du multivers désigne la stabilité d'une conclusion d'audit face aux choix de facteurs `R`. Elle ne doit pas être confondue avec la robustesse technique du système exigée par l'article 15 et ne démontre pas sa conformité.

## Protection des données

L'article 10(5) prévoit un régime exceptionnel et encadré pour le traitement de catégories particulières strictement nécessaire à la détection et à la correction de biais des systèmes à haut risque. Le logiciel n'établit pas que ces conditions sont remplies. Le déployeur doit notamment documenter la nécessité, les alternatives, les contrôles d'accès, la sécurité, la non-transmission et l'effacement.
