# eval — Jev routing benchmark

Everything needed to classify the v2 prompts with Jev, score it against the
synthetic rubric, simulate routing/cost, and watch it fill in live.

## Setup

```bash
pip install typesafe-sdk
# .env at the repo root:  TYPESAFE_API_KEY=...
```

The SDK reads `TYPESAFE_API_KEY` from the environment; `jev_runner.py` also
loads the repo-root `.env` for you.

## Watch it without spending anything (simulated)

```bash
# terminal 1 — write simulated results, one every 20ms
python3 eval/simulate_results.py --split development --delay 0.02

# terminal 2 — serve the dashboard
python3 eval/dashboard_server.py --results eval/results/sim.jsonl --open
```

Open <http://127.0.0.1:8787>. The inbox fills row by row and the CIO summary
recomputes on every poll. Simulated results are marked `simulated=true`.

## Drive it from the dashboard (for screen recording)

Start the server pointed at the results file you want written:

```bash
python3 eval/dashboard_server.py --results eval/results/dev.jsonl --open
```

**Policy toggles** — change these live; the summary and every row's routed
model re-cost instantly, because routing is recomputed from the stored Jev
verdict on each poll:

- **Allow CN-origin models** — on by default. Off, T3 routes to the premium US
  frontier; on, T3 maps to DeepSeek/Qwen `T3·C1` and spend drops. High-sensitivity
  prompts still exclude CN vendors via the allowlist.
- **High-sensitivity requires allowlist** — blocks non-allowlisted cloud for
  `data_sensitivity = high`.
- **Enforce data residency** — restricts non-local models by residency.
- **Escalate below** — confidence threshold; below it, the required tier moves
  up one.
- **Frontier baseline** — the model used for the "every prompt to premium"
  comparison. Shown in the header so no viewer misses the counterfactual.

Toggles are in memory; **reset** reloads `eval/policy.json`.

**Start classification** — records a run end to end:

1. `Mode` → `Jev — real API` (or leave `Simulated rehearsal` to rehearse the
   screen recording for free).
2. Pick `Split`, `Slice`, `Limit`, `Concurrency`; `clear results first` wipes
   the output file before starting.
3. Press **Start classification**. Rows fill in live; **Stop** terminates it;
   the log panel tails the runner output.

Real mode calls the TypeSafe API and spends credits; it asks for confirmation.
Launch the server with `--disable-run` for a view-only dashboard.

## Score the baselines (no API)

```bash
python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl
python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl --ambient   # with distractor suffix
python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl --leaky     # legacy row-split for contrast
python3 eval/baselines.py --data datasets/v2/harness-prompts-v2.jsonl --slice harness
```

## Run Jev

```bash
# 1. validate the payload, no API call
python3 eval/jev_runner.py --split development --limit 1 --dry-run

# 2. cheap pilot on the 279-row dev split
python3 eval/jev_runner.py --split development --concurrency 6 --out eval/results/dev.jsonl

# 3. watch it live
python3 eval/dashboard_server.py --results eval/results/dev.jsonl --open

# 4. blind test split (do not tune on this)
python3 eval/jev_runner.py --split test --concurrency 8 --out eval/results/test.jsonl
```

The runner is resumable (`--resume`, default on), writes one JSON line per
result as it completes, and records choice, all probabilities, confidence,
model version, token usage, latency, and the routed model + estimated cost.

Flags: `--slice business|harness`, `--ambient` (send `prompt_with_ambient`),
`--order dataset|shuffle|interleave`, `--limit`, `--model`.

## Approve the routing policy before trusting cost numbers

- `eval/model_registry.json` — models, capability tiers, cost bands, vendors,
  origins, and **list prices pulled from OpenRouter** (`pricing_fetched_at`
  records the date; local models are $0). Replace with your contracted rates.
- `eval/policy.json` — defaults: `allow_cn_origin: true` (DeepSeek/Qwen are
  frontier-capable at a fraction of US-frontier prices, and we expect them to
  be served from US-hosted endpoints too), high-sensitivity requires a
  non-CN allowlist, residency off, escalation below 0.60, and baseline
  `anthropic/claude-opus-4.5`.

The **baseline is a named, visible choice**, not a hidden default: it is shown
in the header and in the headline. It is a counterfactual, not your measured
current spend. Savings are an **upper bound** — they price the routing decision,
not the quality of the routed answer, so under-routing risk is not yet priced.

The classifier only ever outputs a capability tier. Which model gets chosen,
and what it costs, is decided here in code.

## Files

| file | purpose |
| --- | --- |
| `jev_runner.py` | calls Jev, writes results incrementally |
| `rubric.json` | frozen rubric v1.0 — question, criteria, boundary rules |
| `baselines.py` | majority / word-count / 1-NN / naive Bayes |
| `report.py` | full run report: Jev vs baselines, confusion, calibration, errors |
| `tune.py` | offline mapping tuner (uses cached Nouls; no API calls) |
| `audit_labels.py` | label/topical-confound audit |
| `routing.py` | shared policy, model selection, cost, and summary logic |
| `simulate_results.py` | writes clearly-marked simulated results for demos |
| `dashboard_server.py` | stdlib server for the live dashboard |
| `dashboard.html` | the inbox + CIO summary UI |
| `model_registry.json` | illustrative models and prices |
| `policy.json` | routing policy |
| `results/` | run outputs (`*.jsonl`) |

## Caveats

- `gold_tier` is a synthetic rubric prior (see `docs/dataset-v2.md`), so
  accuracy measures agreement with our rubric, not empirical model adequacy.
- Costs are estimates from illustrative list prices, not invoices.
- Delete `eval/results/sim*.jsonl` before real runs so simulated and real
  results are never mixed.
