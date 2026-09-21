# Tuning & the stratified split (2026-09-21)

## Why we re-split

The first blind test scored 69.3% after dev said 84.6% — a 15-point gap. One root
cause was the split: dev was **15% T3**, test **29% T3**. Templates were disjoint,
but rows were allocated without regard to tier, so dev was not representative and
the thresholds tuned on it didn't transfer.

`split_version: stratified-1` fixes that: within each `(category, tier)` bucket,
templates are chosen for dev to hit ~20% of that bucket's **rows** (not templates).

| split | rows | T0 | T1 | T2 | T3 |
| --- | --- | --- | --- | --- | --- |
| development | 192 | 27.1% | 26.0% | 23.4% | 23.4% |
| test | 736 | 24.5% | 24.7% | 25.4% | 25.4% |

Templates still span the split zero times; duplicate prompts zero.

## Offline tuner — `eval/tune.py`

Noul values are stored per result, so re-tuning costs **no API calls**. The tuner
joins cached Nouls to the (new) split, fits candidate mappings with
template-grouped cross-validation, and writes the winner into `eval/rubric.json`.

```bash
# tune on dev only (run the dev split first to get fresh Nouls)
.venv/bin/python eval/tune.py --nouls eval/results/dev.jsonl --export

# compare against a test run (diagnostic)
.venv/bin/python eval/tune.py --nouls eval/results/dev.jsonl eval/results/test.jsonl
```

Candidates: the hand thresholds, multinomial logistic regression (C × class
weights), and decision trees (depth × class weights). Objective defaults to
**cost-weighted error** (under-routing penalised 3×); `--objective accuracy`
selects the accuracy-optimal mapping instead.

The exported mapping is evaluated by pure-Python code in `routing.tier_from_nouls`
(linear coefficients or a serialized tree), so there is no runtime dependency on
scikit-learn. scikit-learn is only needed to *fit*.

## Result on the stratified split

Jev = rubric v2.0, thresholds 0.8 / 0.8 / 0.4 / 0.4 (selected by CV cost error).
Baselines trained on dev (192), scored on test (736), template-disjoint.

| predictor | acc | within±1 | macro F1 | T3 recall | cost error | template acc |
| --- | --- | --- | --- | --- | --- | --- |
| **Jev (thresholds)** | **72.1%** | **98.0%** | 0.717 | 86.6% | **0.424** | **76.6%** |
| Jev (logreg C=3 balanced) | 73.2% | — | 0.733 | 87.7% | 0.492 | — |
| naive Bayes | 73.2% | 95.1% | 0.725 | 85.6% | 0.607 | 65.1% |
| 1-NN | 66.0% | 93.8% | 0.655 | 79.1% | 0.946 | 62.5% |
| word count | 48.9% | 94.0% | 0.482 | 58.3% | 1.145 | 52.1% |
| majority | 24.5% | 49.2% | 0.098 | 0.0% | 4.553 | 26.6% |

Read: Jev **ties** naive Bayes on row accuracy, macro-F1 and T3 recall, and
**beats** it on cost-weighted error (0.424 vs 0.607) and template-level accuracy
(76.6% vs 65.1%). **98% of Jev's predictions are within one tier** — its errors are
almost all boundary errors, which matters given the T1/T2 label noise found in the
audit. The learned mappings did not beat the hand thresholds on the chosen
objective, confirming the mapping is not the bottleneck.

Per-tier on test: T0 F1 0.817 · T1 0.490 · T2 0.685 · T3 0.876. T1 remains the
weak class (recall 41.2%) — the label-noise boundary.

## Report bug fixed

`eval/report.py` was using each record's *stored* `jev.choice` for the JEV row
while `routing.summarize` re-derived the tier from Nouls for per-tier and
confusion — so they could disagree once thresholds changed. It now recomputes
everywhere via `effective_tier`.

## Tomorrow's run

```bash
# 1. dev split (192 rows) — fresh Nouls
.venv/bin/python eval/dashboard_server.py --results eval/results/dev.jsonl --open

# 2. re-tune on dev and export into the rubric (free, no API calls)
.venv/bin/python eval/tune.py --nouls eval/results/dev.jsonl --export

# 3. test split, blind (736 rows)
.venv/bin/python eval/dashboard_server.py --results eval/results/test.jsonl --open

# 4. full report + baseline comparison
python3 eval/report.py --results eval/results/test.jsonl
```

## Still open

- **T1/T2 label noise** — the audit found volume being encoded as capability.
  Sharpening or merging that boundary is the biggest remaining lever.
- **Empirical cascade** — run real models per tier and judge pass/fail; blocked on
  non-TypeSafe API keys. This is the only way to price under-routing risk.
- **Harness slice** (48 test rows) — still unrun; baselines collapse there.
