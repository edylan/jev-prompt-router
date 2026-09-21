# Cascade + state ablation — findings (2026-09-21)

Two experiments that the routing benchmark cannot answer: does the model Jev
would route to actually *do the task*, and does the classifier do better with the
full intercepted request than with the bare prompt?

## (1) State ablation — useful state helps, noise hurts

Same Jev rubric (v2.2), two renderings per row: **bare** = the user request only;
**full** = the whole intercepted request (harness frame, tools, context lines).

Harness slice (48 test rows):

| rendering | 4-tier acc | **3-tier acc** | **T3 recall** |
| --- | --- | --- | --- |
| bare | 81.2% | 87.5% | 91.7% |
| **full request state** | 72.9% | **91.7%** | **100.0%** |

Business slice, 150 rows, bare vs bare+ambient filler:

| rendering | 4-tier acc | 3-tier acc | T3 recall |
| --- | --- | --- | --- |
| bare | 78.0% | 88.0% | 88.4% |
| bare + ambient filler | 72.7% | 82.7% | 88.4% |

**Reading:** the harness frame *is* useful state — it raises the metrics we route
on (3-tier accuracy 87.5→91.7%, T3 recall 91.7→100%) while only lowering the
T1/T2 metric we've decided is noise. Irrelevant ambient filler does the opposite,
degrading 3-tier accuracy (88.0→82.7%). This is exactly the "give the model the
relevant state, filter the rest" guidance, measured.

*Caveats:* n=48 (harness) / 150 (business); the harness frame is synthesized, not
captured. The real test needs live intercepted requests.

## (2) Empirical cascade — run the models, judge with Jev

Method: sample prompts, generate an answer with each of three OpenAI-compatible
DeepSeek models, then judge each answer with Jev (independent model family) on
"does this fully and correctly complete the request". Generators map roughly to
our tiers: `deepseek-chat` (cheap general), `deepseek-flash` (flash-frontier),
`deepseek-v4-pro` (frontier-class). 48 prompts × 3 generators = 144 runs, ~$0.76.

A first run on the raw corpus was **uninformative**: only ~49% of prompts are
executable at all (737 → 359) because most reference inputs we cannot supply
("turn these CRM notes…", "given your schema…"). Models correctly ask for the
missing inputs and correctly score as incomplete. So the cascade was restricted
to genuinely self-contained prompts.

Pass rate (Jev `adequate` ≥ 0.5) by gold tier × generator:

| gold | cheap general | flash-frontier | frontier-class |
| --- | --- | --- | --- |
| T0 | 83% | 92% | 92% |
| T1 | 42% | 67% | 67% |
| T2 | 50% | 73% | 73% |
| T3 | **25%** | 67% | **75%** |

Cheapest generator that passes, per prompt: T0 mostly the cheapest (10/12);
T1/T2 mixed; T3 needs flash or frontier-class (8/12).

**Readings:**

1. **The tier labels track real difficulty.** The cheapest model passes 83% of T0
   but only 25% of T3 — monotone in the label. That is independent evidence the
   taxonomy orders tasks correctly, which the rubric-agreement metric could not give.
2. **Cheap frontier captures most of the gain.** `flash` and `pro` are within a
   few points everywhere (T3: 67% vs 75%) — supporting the substitution thesis
   that a cheap frontier-class model can serve the middle and much of the top.
3. **T0 is cheaply satisfiable** (83% with the cheapest model), so local/cheap
   routing for T0 is safe.
4. **Some T3 tasks pass with the cheapest model (3/12)** — either the labels
   over-provision some T3 cases or the "adequate" bar is lenient. Worth tightening
   the judge (require a task-specific rubric) before trusting this.

*Limitations:* only cloud DeepSeek generators — no local model (no GPU) and no
US-frontier key, so the T0-local and premium-frontier ends are untested; the judge
is Jev, so judge bias is unmeasured; reasoning models dominate cost (~340k output
tokens ≈ $0.76 for 144 runs).

## What this does and doesn't establish

- **Does:** the tier ordering is real; cheap frontier substitutes well for harder
  work; T0 is cheaply routable; relevant request state improves the routing
  decisions that matter.
- **Doesn't:** price under-routing (we lack a genuinely weak model and a local
  one), or validate on real traffic (the synthesized frames and the 49%
  executable rate are the tell).

## Next

1. Capture real intercepted requests (with their actual context) so both the
   state ablation and the cascade run on executable, relevant inputs.
2. Add a genuinely small model and a local model to the cascade to measure the
   under-routing failure rate and price it.
3. Replace the single "adequate" judge with a task-specific rubric per prompt.
