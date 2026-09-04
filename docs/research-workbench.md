# Research Workbench and portable audit crates

## Objective

Research Workbench is the international, bilingual entry point to EU AI Auditor. It minimizes setup errors while keeping normative decisions visible and attributable to the researcher.

The workflow is deliberately split into four layers:

1. **Suggestion** — common English and French column names are recognized conservatively.
2. **Human mapping** — the researcher confirms the outcome, protected attributes, protected value and conditioning variables.
3. **Statistical audit** — CDD, proxy screening, representation, quadrants and intersectional analysis run from one immutable configuration signature.
4. **Research export** — the exact configuration and tidy results are packaged with provenance and integrity metadata.

Schema inference does not use an LLM, external API or hidden classifier. It is a deterministic lexical and type-based assistant. A low-confidence role remains empty instead of being silently guessed.

## Intersectional analysis

For every observed combination of selected protected attributes, the engine reports:

- sample count and favourable count;
- favourable-outcome rate;
- Wilson confidence interval;
- difference and ratio relative to the complete-case population;
- odds ratio and two-sided Fisher exact p-value against the rest of the population;
- Benjamini-Hochberg q-value across eligible intersections;
- a review priority requiring both a material gap and an FDR-controlled statistical flag.

Groups below `min_group_count` remain in the table but receive no p-value or q-value. This prevents a lack of power from being misreported as fairness. The worst-case gap is the difference between the highest and lowest eligible group rates.

The tests are exploratory. Dependence between overlapping group-versus-rest comparisons, selection effects, missing protected attributes and construct validity still require expert review.

## RO-Crate export

The ZIP follows RO-Crate 1.3 structure and contains:

```text
ro-crate-metadata.json
README.md
CITATION.cff
checksums.sha256
audit/
  config.json
  manifest.json
metadata/
  croissant.json
results/
  *.csv
software/
  environment.json
data/
  source.csv  # only after explicit opt-in
```

`audit/manifest.json` carries the dataset fingerprint and the exact audit results. `checksums.sha256` detects altered payloads. The verifier rejects duplicate or path-traversal filenames before checking the contents.

Croissant metadata describes the column schema and source dtypes. When source records are omitted, the metadata says so explicitly and cannot be mistaken for a loadable copy of the confidential dataset.

## Replaying an audit

Download the recipe from the application and run:

```bash
eu-ai-auditor-research run source.csv recipe.json --output-dir replayed-audit
```

The command writes a PDF, evidence manifest, machine-readable JSON results and a new RO-Crate. Dataset and artifact hashes make differences visible, but reproducibility still depends on retaining lawful access to the original source data.

## Standards

- [RO-Crate Metadata Specification 1.3](https://www.researchobject.org/ro-crate/specification/1.3/)
- [MLCommons Croissant 1.1](https://docs.mlcommons.org/croissant/docs/croissant-spec-1.1.html)
- [Citation File Format 1.2](https://citation-file-format.github.io/)
- [Fairlearn guidance on intersecting groups](https://fairlearn.org/main/user_guide/assessment/intersecting_groups.html)
- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
