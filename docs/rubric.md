# Routing rubric — frozen

**Version 1.0 · frozen 2026-09-21** · source of truth: `eval/rubric.json`
(the runner loads it; the inline copy in `jev_runner.py` is only a fallback).

This is the exact Choice question and the four tier definitions Jev is asked.
They are frozen **before** the blind test split, so the test result is a real
measurement rather than a fitted one. The development split validates the
rubric; it does not change it. Any change means a new `rubric_version`.

## Question

> What is the minimum model capability tier sufficient to complete this request
> reliably and professionally, assuming the model receives the referenced
> materials and ordinary tools named in the request?

Answer semantics: **minimum sufficient tier** (a floor, not "best value").

## Criteria

| tier | definition |
| --- | --- |
| T0 | A capable local model of roughly 12B parameters or less. Bounded rewriting, extraction, formatting, simple code, and clear single-step tasks with limited context. |
| T1 | An inexpensive hosted general model. A small local model is not dependable enough because of context size, instruction density, synthesis, or polish, but advanced reasoning is not required. |
| T2 | A high-capability, cost-efficient cloud model. Reliable multi-step synthesis, professional analysis, repository work, tool use, and moderately complex judgment. |
| T3 | A premium frontier or deliberate-reasoning model. Deep ambiguity, long-horizon planning, high-stakes judgment, complex cross-system work, or tasks where under-routing is costly. |

## Boundary rules

1. Choose the minimum tier, not the best possible answer.
2. Judge only the intrinsic capability the request needs; ignore vendor, price,
   and the requester's organization.
3. If two tiers could both work, choose the lower one only when the task is a
   clear single step with limited context.
4. Treat deep ambiguity, conflicting evidence, cross-system integration,
   long-horizon planning, or high-stakes judgment as T3.
5. A request that merely names tools or attachments does not raise the tier by
   itself; the required judgment does.

## Frozen decisions

- `state` sent to Jev is the row's `prompt` only — never the label, category,
  rationale, governance, or another row.
- Confidence escalation threshold: **0.60**, evaluated in code after the Choice.
- Baseline model for the savings counterfactual: **Claude Opus 4.5**.
- Classifier output is a capability tier only. Cost, vendor, origin, and
  governance are resolved in code (`eval/routing.py`).

## Why this matters

The rubric is a synthetic prior: agreement with it measures agreement with our
definition, not model adequacy. Freezing it is what makes the blind test
meaningful; the empirical cascade (run real models per tier, judge pass/fail)
is still required to validate the definitions themselves.
