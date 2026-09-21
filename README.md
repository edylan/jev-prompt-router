# Fillm

**Inference routing for the enterprise.** Silent, capability-aware LLM routing for enterprise fleets. An agent is pushed
to employee machines, intercepts LLM traffic from coding/agent harnesses
(Claude Code, Codex, pi, …), classifies what each prompt actually needs, and
routes it to the cheapest model that can do the job — while giving CIOs the
token-spend and model-usage visibility they currently lack at fleet scale.

**Near term:** the routing brain + the CIO dashboard, proven on a synthetic
corpus of 1,000 corporate prompts. **End state:** every corporate GPU becomes
shared inference capacity that any employee's prompt can be scheduled onto.

## The one design rule

**Capability tier (`T0`–`T3`) is classified by the model. Cost, vendor,
origin, and governance are decided in code.** Jev never names a model or a
price; a deterministic policy layer maps the tier to the cheapest eligible
model. That keeps the classifier stable when prices and vendors change, and
keeps policy explicit.

| tier | meaning |
| --- | --- |
| T0 | local, ~≤12B (Gemma-class on an employee GPU) |
| T1 | inexpensive hosted general model |
| T2 | flash-frontier / high-capability efficient cloud |
| T3 | full-frontier or deliberate-reasoning model |

Capability is orthogonal to cost: a frontier-capable but cheap model
(DeepSeek/Qwen "Pro" class) is `T3 · C1`, not a separate tier.

## Repo layout

```
docs/
  design.md           product + architecture decisions, taxonomy, routing
  dataset-review.md   critique of the v1 dataset and why v2 exists
  dataset-v2.md        v2 dataset, validation, baselines, protocol
  rubric.md           frozen tier rubric (v1.0)
datasets/v2/
  generate.mjs        deterministic generator (seed 0x5eed2026)
  bank-v1.json        194 cleaned v1 scenarios
  bank-new.mjs        +100 authored scenarios and slot dictionaries
  bank-new2.mjs       +45 slot-rich scenarios
  harness-bank.mjs    24 agent scenarios × Claude Code / Codex / pi
  *-v2.jsonl / .csv   1,000 rows (928 business + 72 harness)
  manifest-v2.json    counts, integrity, independence checks
eval/
  README.md           how to run everything
  jev_runner.py       Jev classifier (ready; not yet run)
  rubric.json         frozen rubric v1.0 (loaded by the runner)
  baselines.py        majority / word-count / 1-NN / naive Bayes
  routing.py          policy, model selection, cost, summary
  dashboard_server.py live dashboard server with policy + run control
  dashboard.html      prompt inbox + CIO summary
  simulate_results.py demo without spending API calls
  model_registry.json OpenRouter list prices, capability tiers, cost bands
  policy.json         routing policy
```

## Quickstart

```bash
# 1. baselines on the v2 benchmark (no API)
python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl --leaky

# 2. see the dashboard with clearly-marked simulated data
python3 eval/simulate_results.py --split development --delay 0.02        # terminal 1
python3 eval/dashboard_server.py --results eval/results/sim.jsonl --open # terminal 2

# 3. run Jev (needs pip install typesafe-sdk and .env with TYPESAFE_API_KEY)
python3 eval/jev_runner.py --split development --limit 1 --dry-run
python3 eval/jev_runner.py --split development --out eval/results/dev.jsonl
```

Full commands: `eval/README.md`.

## Status

- [x] Align on product, taxonomy, and the capability/policy split (`docs/design.md`)
- [x] Critique v1 and specify v2 (`docs/dataset-review.md`)
- [x] Build the v2 benchmark with a leak-free template split (`docs/dataset-v2.md`)
- [x] Honest baselines + a live dashboard
- [ ] Run Jev on the dev split; freeze criteria and confidence threshold
- [ ] Run the blind test split
- [ ] Empirical cascade: real models per tier, judge pass/fail
- [ ] Interception sidecar (harness-config redirection — see `docs/design.md`)
- [ ] The CIO dashboard on real intercepted traffic
- [ ] The GPU hive

## Caveats

`gold_tier` is a synthetic rubric prior, so accuracy measures agreement with our
rubric, not empirical model adequacy. Governance fields are synthetic and
deliberately independent of tier. Prices are OpenRouter list prices (see
`pricing_fetched_at` in `eval/model_registry.json`), not contracted rates, and
local models are priced at $0. Cost savings price the routing decision only —
quality risk from under-routing is not yet measured. Effective independent units
are the 335 templates, not the 1,000 rows.
