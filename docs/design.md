# Fillm — Design Decisions

Status: alignment phase. No routing proxy or dashboard yet. Next input: 1,000-prompt
synthetic dataset with gold labels.

## What we're building

An enterprise agent (MDM-pushable) that silently intercepts LLM traffic from agent
harnesses (Claude Code, Codex, pi, …), classifies the **capability** each prompt
requires, and routes it to the cheapest adequate model. Near-term value = the routing
brain + the CIO cost/usage dashboard. End state = a campus-wide GPU hive.

## Immediate deliverable

Jev-based capability classifier + evaluation harness over 1,000 labeled synthetic
prompts, in Python, including a simulated cost-savings model. No proxy, no dashboard.

## Classification target: capability tier only

The dataset labels and the Jev question are **T0–T3 capability tiers**:

| Tier | Meaning |
| --- | --- |
| T0 | Local, ~≤12B (e.g. Gemma-class on employee GPU) |
| T1 | Inexpensive hosted general model |
| T2 | Flash-frontier / high-capability efficient cloud |
| T3 | Full-frontier or deliberate-reasoning model |

Answer semantics: **minimum sufficient tier** (a floor, not "best value").

### Key principle

Jev classifies *capability requirement* only. It must **not** output vendor, model
name, price, or cost math — Jev is weak on numbers and won't know current pricing.
Capability → model selection is a deterministic lookup in code.

## Separating capability from cost, vendor, and governance

Capability tier is **orthogonal** to what a model costs and where it comes from. The
"cheap Asian model" is not a tier; it is a set of models that happen to be lower cost
and carry different governance flags. A frontier-capable cheap model (DeepSeek/Qwen
"Pro" class) is `capability=T3, cost_band=C1, origin=CN`.

Notation: `T3·C1` = frontier capability, value cost.

### Model registry (code-owned, not model-owned)

Each candidate model is a row:

- `model_id`, `display_name`, `vendor`, `origin_jurisdiction`
- `capability_tier` (T0–T3)
- `cost_band` (C0 local/free, C1 value, C2 standard, C3 premium)
- `input_usd_per_mtok`, `output_usd_per_mtok`
- `serving_locus` (local | cloud)
- `context_window`, `modalities`, `tool_calling`, `latency_class`
- `governance_tags` (residency, export-control, retention, vendor-jurisdiction)

Costs are always computed in code from the registry, never asked of the model.

## Routing algorithm (target shape)

1. **Deterministic pre-filters** (cheap, reliable, code): context > window → exclude;
   vision/multimodal → exclude text-only; already on an adequate tier → pass through.
2. **Jev Choice** over T0–T3 → required tier + probability distribution + confidence.
   One narrow question. State = the single prompt (for now).
3. **Policy gate**: filter registry by governance eligibility (residency, vendor
   allow/deny, sensitivity). A separate policy layer, not part of the classifier answer.
4. **Cost-optimize**: among eligible models with `capability_tier == required`, pick
   lowest `cost_band`, tiebreak latency/availability.
5. **Confidence handling**: below threshold → escalate one tier / fall back to frontier
   (asymmetric: under-provisioning is worse than over-provisioning). Thresholds tuned
   on labeled data.

## Evaluation design

- Splits: 60/20/20 dev/val/test (labels provided; no tuning on test).
- Metrics: cost-weighted confusion matrix; primary = **recall of frontier-needed (T3)**;
  also overall accuracy, per-tier precision/recall, calibration (reliability/ECE),
  abstention & escalation rates, threshold sweep, simulated fleet savings.
- Asymmetric loss: a false "cheap is fine" costs more than a false "needs frontier".
- Batching: compare per-prompt calls vs fan-out batches (many prompts in one state,
  one question each). Watch for context rot / cross-contamination vs the 12× cost and
  10× speed the docs report.

## Jev constraints that shape the harness

- `jev-1.13`: $42/Btok input ($0.042/Mtok); output free. ~64k context / ~32k state.
- Text only — cannot classify image/audio content.
- Not reliable for counting, arithmetic, or dates — keep all numeric work in code.
- Context rot with large irrelevant state — filter state first.
- Not robust to adversarial/injected content in the prompt. A routing product is a
  target: prompts can argue for their own (mis)classification. Test for this.
- Calibrated probabilities are the point — design around confidence, don't ignore it.

## Interception (deferred, opens for v1)

Recommendation: start with **harness-config redirection** — MDM-managed settings
point each harness's base URL at a local sidecar proxy that speaks the provider wire
protocol. No TLS MITM, no enterprise CA, no cert-pinning breakage; you own the
request/response bodies, streaming, token accounting, and per-user attribution. Add
OS-level TLS interception later as an enforcement layer for unmanaged traffic and
non-configured clients. Needs validation of which harnesses expose managed config.

## Route-decision record (draft, pending CIO feedback)

`request_id`, `session_id`, `timestamp`, `user_id`, `device_id`, `team_id`,
`harness`, `provider`, `requested_model`, `required_tier` (Jev),
`tier_probabilities`, `confidence`, `policy_gates_applied`, `chosen_model`,
`chosen_tier`, `cost_band`, `estimated_input_tokens`, `actual_input_tokens`,
`actual_output_tokens`, `estimated_cost_usd` (code-computed), `latency_to_first_token`,
`total_latency_ms`, `route_reason` (prefilter | jev | escalation | fallback),
`outcome` (ok | error | escalated). Feeds both the dashboard and the future GPU queue.

## Open questions

- Label provenance for the 1,000 prompts (human, frontier judge, or empirical sweep).
- Does T3 conflate "frontier capability" with "deliberate reasoning"? If the dataset
  mixes them, consider an auxiliary flag (e.g. a Noul for extended reasoning).
- Domain/language/length distribution of the synthetic set.
- Whether the dataset includes harness/system/tool context or bare prompts.
- Interception method (deferred).
