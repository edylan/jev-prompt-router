# Blind test findings — 2026-09-21

Run: `jev-latest` (jev-1.13.0), **rubric v2.0**, tuned mapping (deep 0.8, multistep 0.8,
single_step 0.4, context 0.4). Data: business **test** split, 649 rows. Zero errors.
Cost $0.0124 (296k input tokens). Latency p50 107 ms / p95 172 ms.

Baselines trained on the **development** split (279 rows, template-disjoint), scored on
the same 649 rows.

## Headline: Jev does not clearly beat a bag-of-words baseline

| predictor | accuracy | macro F1 | T3 recall | cost error | template acc |
| --- | --- | --- | --- | --- | --- |
| **Jev v2 (tuned)** | **69.3%** | 0.680 | 87.4% | **0.465** | **73.3%** |
| naive Bayes | **70.1%** | 0.688 | **94.7%** | 0.740 | 62.3% |
| 1-NN | 66.4% | 0.656 | 83.7% | 1.014 | 56.7% |
| word count | 40.5% | 0.390 | 17.4% | 1.284 | 38.1% |
| majority | 22.7% | 0.092 | 0.0% | 4.817 | 25.9% |

Jev ties naive Bayes on row accuracy (−0.8 pt, within noise), **loses 7.3 pts of T3
recall**, but **wins on template-level accuracy (+11 pts) and cost-weighted error
(−0.275)**. So it generalises across scenarios better than the lexical model and makes
less costly mistakes, but it is not a clear win.

## The dev number did not generalise

Dev (tuned, in-sample) said 84.6%. Blind says 69.3% — a **15-point optimism gap**.
Two causes:

1. **Thresholds were tuned on dev.** A *post-hoc* grid search on the test labels only
   reaches 70.4% (diagnostic only, not a valid result), so the mapping is not the main
   limit — the Noul signal is.
2. **The split is not tier-stratified.** Dev is T3-poor, test is T3-rich:

   | split | T0 | T1 | T2 | T3 |
   | --- | --- | --- | --- | --- |
   | development (279) | 85 | 80 | 72 | 42 |
   | test (649) | 147 | 152 | 160 | 190 |

   T3 is 15% of dev but 29% of test. The split is template-disjoint but the row
   allocation was not balanced by tier, so dev was not representative. This is a real
   benchmark flaw and it biases both the tuned thresholds and the dev estimate.

## Failure shape

| gold \ Jev | T0 | T1 | T2 | T3 |
| --- | --- | --- | --- | --- |
| T0 (147) | 95 | 43 | 9 | 0 |
| T1 (152) | 12 | 57 | 83 | 0 |
| T2 (160) | 0 | 11 | 132 | 17 |
| T3 (190) | 0 | 0 | 24 | 166 |

- **T1 is the weak class: recall 37.5%** (83 of 152 pushed to T2) — exactly the boundary
  the audit flagged as label-noisy.
- **T3 recall 87.4%**; 24 frontier tasks under-routed to T2 (12.6% of T3) — the costly
  direction.
- 199/649 errors (30.7%): 47 under-routed, 152 over-routed.
- Per-tier F1: T0 0.748 · T1 0.433 · T2 0.647 · T3 0.890.

## Calibration

ECE 0.137. The 0.5–0.6 bin is only 44.4% accurate (171 rows), so low confidence is real
signal. Trusting conf ≥ 0.6 gives 78.2% on 73.7% coverage; ≥ 0.8 gives 81.9% on 14.5%.

## Cost

Routed $1.919 vs baseline $17.176 → 88.8% saving. Still an **upper bound**: 30.7% of
routings are wrong and 12.6% of frontier tasks are under-routed, and the quality cost of
those is not measured.

## Verdict

The router is **not yet demonstrably better than a bag-of-words baseline** on this
benchmark. It is better at scenario-level generalisation and cost-weighted error, which
is genuinely promising, but 30.7% error and 12.6% frontier under-routing are not
shippable. Do not present the savings figure as a product claim yet.

## Next

1. **Rebalance the split by tier** (stratify row allocation, not just templates) and
   re-run dev/test so dev is representative.
2. **Re-tune with class weighting** toward T3, and treat T1 as the label-noise class —
   possibly merge or re-define T1/T2.
3. **Run the empirical cascade** — the only way to know whether under-routing actually
   degrades answers, and to validate the labels themselves.
4. The harness slice (48 test rows) is still unrun; it is the closest proxy to real
   intercepted traffic and the baselines collapse there.
