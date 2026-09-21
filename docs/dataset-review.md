# Dataset Review: `business-prompts-1000`

Source: `/home/dylan/Development/chronocle/tmp/jev-router-eval/`
Reviewed: generator (`generate-dataset.mjs`), README, `manifest.json`, and all 1,000 rows.

## Verdict

The dataset is usable for a **first-pass** Jev evaluation, but the shipped dev/test split
is contaminated by template memorisation and will report a **wildly inflated** score.
Two fixes are required before any number from it means anything: a template-level split,
and baselines to compare against. Two further issues (governance coupling, padding
artifacts) mean the dataset cannot currently test the "policy separate from capability"
design.

## What's good

- Deterministic and reproducible (seeded LCG, `0x5eed2026`), exact-duplicate check.
- Capability tiers are defined without vendor names, and governance is conceptually a
  separate object. The right separation on paper.
- A dev/test split exists and the protocol states Jev sees only `prompt`.
- Independent `business_function` / `task_family` labels support slice analysis.
- README is honest that `gold_tier` is a synthetic prior and points to the empirical
  cascade as the real validation.

## Findings

### P1 (blocker) — Template leakage inflates the test split

194 distinct templates produce 1,000 rows (5.2 rows/template). 121 of 194 templates
appear in **both** dev and test; **539 / 800 test rows (67%)** have a template that also
appears in dev. The README's "each row independently" instruction removes within-request
contamination but not this across-split template reuse.

Baseline test accuracy (no Jev, no LLM):

| Method | Shipped row-split | Template-holdout |
| --- | --- | --- |
| Majority class | 33.6% | 32.7% |
| Word count (3 thresholds) | 40.0% | 36.5% |
| 1-NN Jaccard to dev | **75.4%** | 35.7% |
| Naive Bayes (unigrams) | **73.4%** | 40.6% |

A nearest-neighbour lookup gets 75% on the shipped split but 36% when held-out
templates are unseen. Roughly **35–40 points of "accuracy" is pure memorisation.**
Any Jev result on the shipped split is uninterpretable.

**Fix:** split at the template level — `(category, gold_tier, task_variant)` is the
template key. Report *both* regimes; the template-holdout number is the real one.
Always print the four baselines above next to Jev's score.

### P2 (blocker for the policy design) — Governance is a proxy for T3

The generator sets `data_sensitivity = (tier === 'T3' ? 'high' : 'moderate')` and
`cloud_processing_allowed = policy_check_required` only for high sensitivity. Measured:

| Tier | high sensitivity | regulated | cloud policy check |
| --- | --- | --- | --- |
| T0 | 0% | 29% | 0% |
| T1 | 0% | 29% | 0% |
| T2 | 0% | 34% | 0% |
| T3 | 47% | 54% | 47% |

So the "independent governance axis" is, in this data, essentially a T3 detector. It
cannot be used to test that capability and policy are separable, and it must never be
fed to the classifier.

**Fix:** regenerate governance from a process independent of `gold_tier`.

### P3 — Padding artifacts leak tier and add distractors

Every prompt is padded with a 5-way qualifier sentence and a `Context: ...` suffix.
The qualifier is chosen by `qualifiers[i % 5]`, where `i` is the within-bucket index, so
its frequency differs by tier. Result: T0-signalling vocabulary is dominated by padding
phrases (`concise`, `caveats`, `inventing`, `omit material`) that carry no capability
information. Separately, the `Context` suffix is fabricated detail irrelevant to the
decision — the exact "large state full of irrelevant detail" the Jev jaggedness doc says
degrades accuracy.

**Fix:** assign qualifiers randomly and independently of tier; drop the `Context` suffix
or make it an explicit ablation condition.

### P4 — Labels are circular, and tier definitions overlap

`gold_tier` is the bucket the template was authored into, and the template text was
written knowing its tier. We are measuring "can Jev recover the author's intent", not
model adequacy. T1/T2/T3 definitions also overlap on soft criteria (polish, instruction
density, professional quality), so there is no inter-annotator ground truth. The
empirical cascade (run a stratified sample on real models per tier, judge pass/fail)
remains the only true validation.

### P5 — Genre mismatch with the interception target

The data is business prose: email, decks, memos, some code. The product intercepts
agent-harness traffic (Claude Code, Codex, pi): long system prompts, tool schemas,
repository context, multi-turn loops. Real intercepted prompts look nothing like these.
A high score here will not transfer. Add a small harness-realistic slice (even 100 rows)
before trusting any routing result.

### P6 — Referenced attachments are absent

Many prompts say "these 30 quotes", "this workbook", "the supplied metrics". Jev sees
only the prompt, so it judges the *description* of the work. Legitimate as a predictive
task, but the eval is a lookalike of production, not production.

### Minor

- Shuffle does not stratify; tier mix differs slightly dev vs test.
- `business_function` is regex-derived from the prompt **including** the random context
  suffix, so it is noisy.
- `tools_or_attachments_implied` regex is crude.
- Split sizes: dev 200 (T0 71 / T1 45 / T2 62 / T3 22), test 800.

## Recommended dataset v2 changes

1. Split by template, not row. Keep the shipped v1 frozen for reference.
2. Generate governance independently of `gold_tier`.
3. Randomise qualifiers independently of tier; remove or flag the `Context` suffix.
4. Add a small harness-realistic slice (agent/harness-style prompts).
5. Ship a baseline harness alongside the data so every result is reported as
   "Jev vs. naive Bayes vs. 1-NN vs. majority" on the template-holdout split.

## Eval protocol to implement (from README, plus our additions)

- Jev `state` = `prompt` only. Never `gold_tier`, `category`, `rationale`, governance.
- One Choice question over T0–T3; record choice, all probabilities, confidence, latency,
  model version, token usage.
- Independent requests; concurrency allowed.
- Report: template-holdout accuracy, cost-weighted confusion matrix, T3 recall
  (asymmetric loss), calibration, confidence threshold sweep, simulated savings.
- Run the four cheap baselines on the same split.
