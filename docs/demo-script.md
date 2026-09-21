# Live-analysis demo — shot list

## Pre-flight (before you hit record)

```bash
cd ~/Development/prompt-splitter
./eval/dashboard.sh test
```

Confirm on screen: header **LIVE**, progress **0 / 737**, **Mode** = `Jev — real API`,
**Split** = `test`, baseline pill **Claude Opus 4.5 · $5/$25**. Leave the terminal open.

Jev is free right now, so re-record as many takes as you like — just press **clear results** and start again.

## Shots

**1 · Framing (15s).** The empty dashboard. "This classifies 737 corporate prompts
into what capability they actually need, then prices routing them to the cheapest
adequate model." Point at the baseline pill and the honesty banner — say them out
loud now so they can't be missed later.

**2 · Roll (watch it fill).** Mode `Jev — real API` · Split `test` · Slice `business` ·
Concurrency `6` · **clear results first** checked · **▶ Start**. The inbox fills.
Call out: ~100 ms per decision, the confidence bar under each verdict, and the
routed model changing per row.

**3 · Benchmark panel.** As results land, the panel underneath fills: scorecard,
confusion heatmap, calibration, and the baselines head-to-head. Let it finish at
**737 / 737** (~30–60 s at concurrency 6).

**4 · The result.** Say the honest headline:
- four tiers: **72.5%** — statistically tied with a plain bag-of-words baseline;
- collapsed to **local / cloud-general / frontier: 85.8%**;
- **T3 recall 87.2%**, and **98.2% of predictions are within one tier**.
Point at the confusion matrix: the errors are the cheap-vs-flash boundary, which
we proved is not recoverable from a prompt.

**5 · The cost story.** The headline sentence (baseline → routed), then the
**3-tier routing** line: savings **88.6% → 87.8%** as the share of the merged middle
tier sent to frontier-class models goes 50% → 75%. Read the honesty banner aloud:
upper bound, chosen baseline, list prices, synthetic labels.

**6 · Governance lever.** Toggle **Allow CN-origin models** off. The band drops to
**~67–70%** and the model mix switches to GPT-5 / GPT-5-mini. Toggle back. Say:
"same routing decisions, different policy — no re-inference."

**7 · Close.** "Three-tier routing at 85.8%, roughly 88% modelled savings, and one
thing still unmeasured: whether the cheaper model's answers are good enough. That's
the empirical cascade." Then stop the server (**Ctrl-C**).

## Numbers to have ready

| | |
| --- | --- |
| Jev | ~100 ms p50 / ~167 ms p95, $0.042/Mtok, **~$0.02 per 1,000** classifications |
| 4-tier accuracy | 72.5% (ties naive Bayes 72.6%) |
| 3-tier accuracy | **85.8%** |
| T3 recall | 87.2% · within±1 98.2% |
| Savings band | **88.6 / 88.1 / 87.8%** (CN allowed) · **~67–70%** (blocked) |
| Cascade | cheapest model passes **83% of T0 → 25% of T3** |

## If something breaks

- The **log panel** at the bottom of the dashboard shows the runner's output.
- Any error: press **clear results**, then **▶ Start** again.
- Server died: `./eval/dashboard.sh test`, reload the browser tab.
