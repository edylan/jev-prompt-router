# Label improvements — capability-v1 + rubric v2.1

## What was wrong

The audit found the T1/T2 labels partly encoded **volume/scope** rather than
capability, and the boundary was fuzzy. Jev's biggest error was T1→T2 (89 rows on
the stratified test), so getting this boundary right matters more than any other.

## The labelling rule (`capability-v1`)

- A tier reflects the **capability the task requires**, never volume, length,
  item count, or taxonomy size. Processing more items is code's job.
- **T1** transforms provided content: rewrite, summarise, extract, reformat,
  adapt, translate, classify, list, convert.
- **T2** produces something not in the input: analysis, diagnosis, design,
  recommendation, prioritisation, defensible judgement.
- **T3** adds deep ambiguity, conflicting evidence, high stakes, long horizon, or
  cross-system integration.

## Fixes applied

Two templates were authored T2 but are single-pass transformations, so they are
now T1 (each row carries a `label_fix` field):

| was | now | template |
| --- | --- | --- |
| T2 | T1 | "Adapt the same product-delay announcement for customers, internal staff, and implementation partners…" |
| T2 | T1 | "Classify 300 inbound procurement requests against the supplied 25-category taxonomy…" |

I searched for *all* scale-only label errors by stripping quantities and
comparing same-category cross-tier templates. Only these two were clean cases
(nothing else exceeded 0.45 similarity after strip), which is the key finding:
**the remaining boundary noise is definitional, not a set of typos.**

## Definition sharpened — rubric v2.1

The model was being asked to hit a boundary that the wording did not make
decidable. v2.1 adds a discriminator question with explicit anchors:

- `produces_analysis` — *"requires producing new analysis, diagnosis, design,
  recommendation, prioritisation, or a defensible judgement, as opposed to
  transforming, summarising, extracting, reformatting, adapting, translating, or
  classifying the content already provided."*
  - true: diagnosing a failure, designing an approach, recommending a decision, ranking options
  - false: rewriting, summarising, extracting, reformatting, adapting, translating, classifying — however long the input

Mapping is now: `deep → T3`; `produces_analysis or multistep → T2`;
`single_step and small context → T0`; otherwise `T1`.

## Effect measured offline (cached Nouls)

| | accuracy | T1 recall | cost error |
| --- | --- | --- | --- |
| before label fixes | 72.1% | 41.2% | 0.424 |
| after label fixes | **72.4%** | **41.8%** | **0.419** |

Marginal — as expected for two templates. This **confirms the labels were not the
main error source; the definition was.** The v2.1 discriminator cannot be scored
against the old Nouls and needs a fresh run.

## Ids were renumbered

Relabelling moves templates between tier buckets, which changes the template key,
the slot rendering, and therefore the row order and `biz-####` ids. Offline
evaluation therefore joins cached Nouls **by prompt text**, not by id (926 of 928
business rows covered; the two relabelled templates render new prompt variants
and so have no cached Nouls).

## Tomorrow

```bash
# dev (fresh Nouls with the v2.1 discriminator)
.venv/bin/python eval/dashboard_server.py --results eval/results/dev.jsonl --open
.venv/bin/python eval/tune.py --nouls eval/results/dev.jsonl --export
# blind test
.venv/bin/python eval/dashboard_server.py --results eval/results/test.jsonl --open
python3 eval/report.py --results eval/results/test.jsonl
```

Watch: **T1 recall**, **T1→T2 confusion**, and **within±1** — those are what the
discriminator is meant to move. If T1 recall does not improve, the T1/T2
distinction is not recoverable from a single prompt and should be merged.

---

# Outcome — rubric v2.1 test (2026-09-21)

## The discriminator was rejected

The 5-feature rule (`produces_analysis` included), tuned on dev, scored **68.9%** on
the blind test vs **72.2%** for the 4-feature rule. The signal is real —
`produces_analysis` averages 0.51 for T1 vs 0.82 for T2 — but it does not
generalise. Rubric reverted to **v2.2** (four Nouls, thresholds).

## Two bugs found and fixed

1. **Duplicated mapping logic.** `jev_runner.map_tier` was a stale copy that
   ignored both `produces_analysis` and the tuner's exported `mapping_model`. The
   runner therefore executed the **4-feature thresholds (72.5%)** while the report
   and dashboard scored the tuner's decision tree (**68.4%**). The reported number
   was not what ran. All three now resolve the tier through
   `routing.tier_from_nouls` — verified `stored == effective` on all 737 rows.
2. **`report.py` threshold table** used the stored choice rather than the
   recomputed tier. Fixed.

Also: the tuner's learned models (logistic regression, decision trees) have now
overfit dev **twice** and lost to the plain thresholds on test. Thresholds are the
default; the learned models are behind `--learned`.

## Correct result — business blind test (737 rows)

| predictor | acc | within±1 | macro F1 | T3 recall | cost error | template acc |
| --- | --- | --- | --- | --- | --- | --- |
| **Jev v2.2** | **72.5%** | **98.2%** | 0.719 | **87.2%** | **0.412** | **75.6%** |
| naive Bayes | 72.6% | 95.9% | 0.721 | 84.0% | 0.621 | 65.3% |
| 1-NN | 65.9% | 94.7% | 0.655 | 79.1% | 0.939 | 62.7% |
| word count | 49.0% | 94.0% | 0.482 | 58.3% | 1.141 | 52.8% |

Jev ties naive Bayes on raw accuracy, and beats it on cost-weighted error, within±1
and template accuracy. Still not a decisive win.

## The finding that matters: T1 vs T2 is not separable from a prompt

Collapse T1 and T2 into one class and accuracy jumps:

| granularity | accuracy |
| --- | --- |
| four tiers (T0/T1/T2/T3) | 72.5% |
| **T0 / {T1,T2} / T3** | **85.8%** |

The model reliably distinguishes *local* from *cloud-general* from *frontier*,
but essentially cannot tell a cheap-hosted task from a flash-frontier one using
the prompt alone. That is a structural limit of the signal, not a tuning gap —
we have now tried two question designs and both plateaued at the same place.

## Harness slice (24 test rows — small)

Jev 83.3% / within±1 100% / T3 recall 100% / cost error 0.167. But 1-NN and naive
Bayes both hit **100%** on this sample, so it is too small to claim transfer.

## Decision to make

Either:

1. **Adopt 3-tier routing** — T0 (local) / T1·T2 (cheapest safe cloud) / T3
   (frontier). Reliable, simple, and matches what the classifier can actually do.
   Within the merged tier, route to the model the CIO's policy allows at the
   lowest cost, accepting that "flash vs cheap-hosted" is not decided by capability.
2. **Keep 4 tiers** and resolve T1 vs T2 from *richer state* than the prompt —
   tool calls, repo/turn context, conversation history, attachments — rather than
   asking one question to guess it.

