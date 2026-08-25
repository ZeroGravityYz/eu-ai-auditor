# Sources et licences des études de cas

Ces fichiers sont fournis uniquement pour reproduire des démonstrations techniques. Ils ne doivent pas servir à prendre une décision réelle sur une personne.

## Adult Income

- Source : Barry Becker et Ronny Kohavi, UCI Machine Learning Repository.
- DOI : <https://doi.org/10.24432/C5XW20>
- Page officielle : <https://archive.ics.uci.edu/dataset/2/adult>
- Licence : Creative Commons Attribution 4.0 International (CC BY 4.0).
- Préparation : fusion des partitions d'origine, nettoyage des espaces et du suffixe de cible, suppression des lignes sans attributs indispensables, création de tranches d'âge et d'heures, puis échantillon stratifié déterministe de 6 000 lignes (`random_state=42`).
- Limite essentielle : il s'agit d'une cible de revenu issue du Census américain de 1994, pas de décisions de recrutement et pas de données européennes contemporaines.

Citation : Becker, B. & Kohavi, R. (1996). *Adult* [Dataset]. UCI Machine Learning Repository. <https://doi.org/10.24432/C5XW20>.

## South German Credit

- Source : UCI Machine Learning Repository, version corrigée publiée en 2019.
- DOI : <https://doi.org/10.24432/C5X89F>
- Page officielle : <https://archive.ics.uci.edu/dataset/522/south+german+credit>
- Licence : Creative Commons Attribution 4.0 International (CC BY 4.0).
- Préparation : renommage des colonnes, décodage documenté des catégories et création de tranches d'âge. Les 1 000 observations sont conservées.
- Limite essentielle : crédits de 1973-1975, mauvais risques suréchantillonnés, montants en Deutsche Mark et catégories qui ne reflètent pas le marché actuel.
- Le champ combiné `personal_status_sex` ne permet pas toujours d'isoler le sexe ; l'étude utilise donc l'âge comme attribut protégé principal.

Citation : *South German Credit* [Dataset]. (2019). UCI Machine Learning Repository. <https://doi.org/10.24432/C5X89F>.

## Reproductibilité

Les empreintes des archives UCI et des CSV préparés sont enregistrées dans `manifest.json`. Pour régénérer les fichiers :

```bash
python scripts/prepare_public_cases.py
```

Le code du projet est sous Apache-2.0. Les deux CSV de ce dossier restent soumis à CC BY 4.0 et aux attributions ci-dessus.
