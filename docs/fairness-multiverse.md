# Fairness multiverse: stability across conditioning choices

## Why this exists

Conditional fairness depends on which factors are accepted as legitimate context. A single CDD value can therefore look definitive while hiding a material analyst choice. EU AI Auditor 0.5 makes that dependence inspectable through a bounded multiverse: the researcher declares plausible factors `R` first, then the engine evaluates every permitted subset.

The design adapts the logic of multiverse analysis and specification-curve analysis to a descriptive fairness audit. It does not claim that every possible specification is equally credible, and it does not search for the result an analyst prefers. See [Steegen et al. on multiverse analysis](https://doi.org/10.1177/1745691616658637) and [Simonsohn, Simmons and Nelson on specification curves](https://doi.org/10.1038/s41562-020-0912-z).

## Protocol

Given an ordered, pre-declared set of candidates `C = {R1, ..., Rp}` and a maximum depth `k`, the engine constructs:

```text
M = {R ⊆ C : |R| ≤ k}
```

The empty specification is included as an unconditioned baseline. For every `m` in `M`, the ordinary CDD engine returns an aggregate gap `g_m`, eligible-strata coverage and diagnostics. A specification that cannot satisfy the minimum outcome count remains visible as invalid.

Each valid gap is assigned to one of three descriptive classes for a pre-declared materiality threshold `τ`:

```text
adverse material:    g_m >  τ
within materiality: -τ ≤ g_m ≤ τ
reverse material:    g_m < -τ
```

The dominant share is the proportion of valid specifications in the most frequent class. The headline score is intentionally simple:

```text
robustness score = dominant share × median CDD coverage
```

A conclusion is labelled robust only when the dominant share reaches the consensus threshold, median coverage reaches the coverage threshold, and the configured minimum share of all specifications is calculable. These defaults are 80%, 80% and 80%. They are review rules, not legal thresholds.

## Factor influence

For each candidate, the engine pairs every calculable specification without the factor with the corresponding specification that adds it, subject to depth `k`. It reports:

- the median signed shift in CDD;
- the median and maximum absolute shift;
- the proportion of pairs whose descriptive class changes.

The specification curve orders valid gaps from lowest to highest and aligns them with a factor-inclusion matrix. This makes sign reversals, threshold crossings and influential choices visible without collapsing them into a single average.

## Required safeguards

1. Freeze the candidate set, maximum depth, materiality threshold and minimum counts before reading results.
2. Record a substantive reason why every candidate could be a legitimate conditioning factor.
3. Do not interpret the most convenient specification as the correct one.
4. Investigate invalid specifications and low coverage; missing estimates are not evidence of fairness.
5. Preserve the full table in the evidence manifest or RO-Crate, not only the headline score.
6. Treat the result as a sensitivity analysis. It does not establish causal effects or resolve contested legal concepts of justification.

The implementation caps the universe at 256 specifications. Larger spaces need a written analysis plan and more specialized tooling rather than silent combinatorial exploration.

## Regulatory and risk-management interpretation

The module supports documentation of assumptions, uncertainty and test conditions. This is consistent with the NIST AI RMF emphasis on documented, reproducible testing and explicit uncertainty in measurement: [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/) and [AI RMF 1.0](https://doi.org/10.6028/NIST.AI.100-1).

It can also strengthen an Article 11 technical evidence file by recording test choices and limitations. It does **not** demonstrate compliance with Article 15. The robustness in this module is the stability of an audit conclusion across analytical specifications, while Article 15 addresses accuracy, robustness and cybersecurity of high-risk AI systems themselves. See the [official text of Regulation (EU) 2024/1689](https://eur-lex.europa.eu/eli/reg/2024/1689/oj).

## Scope of the contribution

Multiverse analysis, specification curves and fairness sensitivity research already exist. The project's contribution is an open, lightweight workflow that connects a CDD-specific multiverse to factor influence, a bilingual UI, strict machine-readable evidence, a rendered AI Act-oriented report and a privacy-first research crate. Public landscape review cannot prove that no private or unpublished implementation has ever combined these elements.
