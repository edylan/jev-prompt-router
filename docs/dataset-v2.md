# Dataset v2

Location: `datasets/v2/`. Successor to the v1 set in
`~/Development/chronocle/tmp/jev-router-eval/` (kept frozen for reference).
Motivation and full critique of v1: `docs/dataset-review.md`.

## Headline

**1,000 rows · 335 independent templates · 250 per tier · zero templates span the
dev/test split · zero duplicate prompts · governance independent of tier.**

v1 had 1,000 rows but only 194 templates (5.2 rows each), and 67% of its test
rows reused a dev template, so its test score was mostly memorisation. v2 keeps
the row count while making each row traceable to one of 335 scenarios, and
splits **at the template level** so no scenario appears in both splits.

## What changed from v1

| Issue (v1) | v2 |
| --- | --- |
| 67% of test rows shared a dev template | template-level split; 0 overlap |
| Qualifier padding assigned by `i % 5` → leaked tier | removed from the canonical prompt; kept only as an optional `prompt_with_ambient` ablation field, verified independent of tier |
| Fabricated `Context: …` distractor on every prompt | removed from the canonical prompt; available as ambient ablation |
| Governance derived from tier (`T3 → high`) | governance drawn independently of tier (Cramér's V ≈ 0.04–0.06) |
| 194 templates, 5.2 rows each | 335 templates, 2.77 rows each |
| Business prose only | + 72 harness-realistic rows (Claude Code, Codex, pi) |
| No baselines | `eval/baselines.py` for every comparison |
| Imbalanced tiers (34/25/29/12%) | balanced 250 per tier |

## Generation pipeline

```
extract-v1-prompts.mjs   v1 rows -> clean, re-tokenized bank-v1.json (194 scenarios)
bank-new.mjs             100 hand-authored scenarios + slot dictionaries
bank-new2.mjs            45 slot-rich scenarios (balance + breadth)
harness-bank.mjs         24 agent scenarios x 3 harnesses
generate.mjs             merge, dedupe, split, allocate, validate, write
```

Regenerate:

```bash
cd datasets/v2
node extract-v1-prompts.mjs /path/to/v1/business-prompts-1000.jsonl   # once
node generate.mjs
```

Deterministic: seed `0x5eed2026`.

## Validation (from `manifest-v2.json`)

| check | result |
| --- | --- |
| total / business / harness | 1000 / 928 / 72 |
| tiers (business) | T0 232 · T1 232 · T2 232 · T3 232 |
| templates | 335 (dev 88 · test 247) |
| rows per template | 2.77 |
| templates spanning the split | **0** |
| duplicate canonical prompts | **0** |
| Cramér's V(tier, data_sensitivity / regulated / residency) | 0.058 / 0.044 / 0.054 |

## Honest baselines (template-level split)

No LLM. Row accuracy / template accuracy:

| predictor | business | business + ambient | harness | legacy row-split (for contrast) |
| --- | --- | --- | --- | --- |
| majority | 22.7% / 25.9% | 22.7% / 25.9% | 25.0% / 25.0% | 24.2% / 29.4% |
| word count | 40.5% / 38.1% | 33.6% / 32.8% | 62.5% / 62.5% | 52.4% / 56.6% |
| 1-NN | 66.3% / 56.3% | 48.8% / 44.5% | 33.3% / 37.5% | 84.1% / 69.2% |
| naive Bayes | **70.7% / 63.2%** | 63.9% / 57.5% | 29.2% / 31.2% | 86.4% / 71.7% |

Read-outs:

- The template-level split removes ~16 points of memorisation (NB 86.4% → 70.7%),
  confirming v1's test split was contaminated.
- **Jev must beat ~71% row / ~63% template naive Bayes** to demonstrate value.
  Reporting a higher number without these baselines is meaningless.
- Ambient noise costs naive Bayes ~7 points (70.7% → 63.9%): a direct, useful
  measurement of the context-rot effect the TypeSafe docs warn about.
- The harness slice is a different distribution — bag-of-words collapses to
  chance. This is the slice closest to the real interception target.

## Evaluation protocol

- Jev `state` = the row's `prompt` only. Never `gold_tier`, `category`,
  `rationale`, `governance`, or another row.
- One Choice question over T0–T3, criteria exactly the tier definitions in the
  README/rubric. Answer semantics: **minimum sufficient tier**.
- The dev split (279 business rows) is for refining criteria and thresholds.
  The test split (649 business + 48 harness rows) stays blind until the
  classifier and thresholds are frozen.
- Report, on the same split: row and template accuracy, macro-F1, **T3 recall**
  (frontier-needed), cost-weighted error (under-routing penalised 3×),
  calibration, confidence threshold sweep, and the four baselines.
- Then the empirical cascade: run a stratified sample on real models per tier
  and promote the lowest tier whose output passes a task-specific rubric.

## Known limitations

- `gold_tier` is the tier its template was authored to, so agreement measures
  our rubric, not model adequacy. The empirical cascade is the real test.
- Slot variants vary setting/surface only; effective independent units are the
  335 templates, not the 1,000 rows. The runner may dedupe on `template_key`.
- Governance fields are synthetic and deliberately independent of tier so the
  policy layer can be tested — they are not a realistic sensitivity model.
- Prices in `eval/model_registry.json` are OpenRouter list prices (see
  `pricing_fetched_at`), not contracted rates; local models are priced at $0.
- Categories are hand-assigned to tiers by design, so topical vocabulary
  correlates with tier; that is signal, not leakage, but it makes the lexical
  baselines strong.
