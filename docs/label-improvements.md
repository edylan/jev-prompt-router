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
