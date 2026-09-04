# EU AI Auditor

EU AI Auditor is a Python package and Streamlit application for reproducible statistical and procedural fairness audits. It is designed for researchers, auditors and multidisciplinary teams who need transparent results rather than an automated legal verdict.

## What is included

- Conditional Demographic Disparity (CDD) with explicit conditioning factors and bootstrap intervals.
- Proxy association screening using Pearson correlation, corrected Cramér's V and correlation ratio eta.
- Intersectional outcome analysis with Wilson intervals, Fisher exact tests and Benjamini-Hochberg false-discovery-rate control.
- OversightParity for AI recommendation, human decision, appeal, correction and differential automation-bias analysis.
- Performance/fairness operating points for logistic regression and CART.
- PDF evidence reports and integrity-verifiable JSON manifests.
- Privacy-first research ZIPs using RO-Crate 1.3, Croissant 1.1 and Citation File Format 1.2.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app.py
```

Open **Research Workbench** for the bilingual guided workflow. It recognizes common English and French column names but never chooses the protected group, reference group or legitimate conditioning variables on behalf of the researcher.

## Python example

```python
import pandas as pd
from eu_ai_auditor import (
    calculate_cdd,
    calculate_intersectional_parity,
    infer_audit_schema,
)

data = pd.read_csv("decisions.csv")
print(infer_audit_schema(data).summary())

cdd = calculate_cdd(
    data,
    protected_attribute="gender",
    protected_value="woman",
    decision_attribute="approved",
    advantaged_value=True,
    conditioning_attributes=["qualification", "experience"],
    bootstrap_iterations=250,
)

intersections = calculate_intersectional_parity(
    data,
    protected_attributes=["gender", "age_band"],
    decision_attribute="approved",
    favourable_value=True,
    min_group_count=30,
)
print(intersections.groups)
```

## Reproducible research package

```bash
eu-ai-auditor decisions.csv \
  --protected gender --protected-value woman \
  --additional-protected age_band \
  --decision approved --favourable-value True \
  --condition qualification \
  --research-bundle output/audit-ro-crate.zip

eu-ai-auditor-research verify output/audit-ro-crate.zip
```

A downloaded JSON recipe can replay the entire classic audit:

```bash
eu-ai-auditor-research run decisions.csv audit-recipe.json --output-dir output/replayed
```

Raw source rows are excluded from research packages by default. The ZIP contains the exact configuration, tidy result tables, software environment, cryptographic checksums, a verifiable evidence manifest, `CITATION.cff`, `ro-crate-metadata.json` and Croissant dataset-schema metadata.

## Scientific interpretation

- A detected gap is evidence for investigation, not proof of causality or unlawful discrimination.
- Conditioning variables encode contextual and often legal judgments. They must be justified outside the software.
- Small intersections remain visible but are excluded from inferential claims below the configured minimum count.
- FDR correction reduces false discoveries across tested groups but does not remove measurement, sampling or construct-validity problems.
- A differential exposure estimate is called causal only when the user declares and documents randomized AI visibility.

Read the [research workflow](research-workbench.md), [methodology](methodology.md), [OversightParity specification](oversight-parity.md) and [AI Act mapping](ai-act-mapping.md).

## Citation and license

GitHub renders the repository's [`CITATION.cff`](../CITATION.cff). Code is licensed under Apache-2.0. Included public datasets retain the licenses documented in [`data/cases/SOURCES.md`](../data/cases/SOURCES.md).
