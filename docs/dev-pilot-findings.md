# Dev pilot findings — 2026-09-21

Run: `jev-latest` (jev-1.13.0), rubric v1.0, frozen question/criteria.
Data: `datasets/v2/business-prompts-v2.jsonl` dev split (279 rows) and
`datasets/v2/harness-prompts-v2.jsonl` dev split (24 rows). Zero errors.
Cost: $0.0061 (144k input tokens). Latency p50 101 ms / p95 149 ms.

## Headline: the current design does not beat a bag-of-words baseline

Baselines trained on the **test** split (649 rows), evaluated on the **same
279 dev rows** — template-disjoint, so this is a fair comparison:

| predictor | accuracy | macro F1 | T3 recall | cost error | template acc |
| --- | --- | --- | --- | --- | --- |
| **Jev (single Choice)** | **62.0%** | 0.593 | **38.1%** | 0.624 | 50.0% |
| naive Bayes | **78.9%** | 0.788 | 92.9% | 0.444 | 77.3% |
| 1-NN | 77.1% | 0.795 | 95.2% | 0.484 | 76.1% |
| word count | 52.3% | 0.517 | 95.2% | 0.950 | 55.7% |
| majority | 15.1% | 0.065 | 100.0% | 1.746 | 31.8% |

Jev is **16.9 points behind naive Bayes**. A lexical model recovers the tier
better than the System One model does.

## Failure shape: collapse toward T2

| gold \ Jev | T0 | T1 | T2 | T3 |
| --- | --- | --- | --- | --- |
| T0 (85) | **75** | 10 | 0 | 0 |
| T1 (80) | 0 | 18 | **62** | 0 |
| T2 (72) | 0 | 8 | **64** | 0 |
| T3 (42) | 0 | 0 | **26** | 16 |

- Predicted distribution: T0 75 · T1 36 · **T2 152** · T3 16.
- T1 recall 22.5%, T3 recall 38.1% (26 of 42 hard tasks under-routed to T2).
- Errors: 106/279 (38%) — 34 under-routed, 72 over-routed.

## Calibration is weak and non-monotonic

ECE 0.118. Bins are not ordered by accuracy (0.3–0.4 → 34.3% but 0.2–0.3 →
90.9%, n=11; 0.8–0.9 → 52.5%). High confidence is still informative at the top
end: threshold 0.90 gives 85.5% on 22% coverage.

## Escalating low confidence trades accuracy for T3 recall

| policy | acc | macro F1 | T3 recall | cost error |
| --- | --- | --- | --- | --- |
| none | 62.0% | 0.593 | 38.1% | 0.624 |
| escalate < 0.5 | 56.3% | 0.527 | 66.7% | 0.634 |
| escalate < 0.6 | 54.5% | 0.510 | 76.2% | 0.638 |
| escalate < 0.8 | 41.6% | 0.386 | 83.3% | 0.817 |

Escalation recovers T3 recall but costs overall accuracy and does not improve
cost-weighted error. It is a patch, not a fix.

## Harness slice (24 rows — small, directional)

Jev 50.0% vs baselines 25.0–37.5%: Jev beats the collapsed lexical baselines on
agent-style traffic, but gets **T1 and T3 recall of 0%** (predicts T0 for all T0
and T2 for all T2). n=24 over 8 templates, so treat as a hint only.

## Interpretation

1. **The judgment is too coarse.** One holistic Choice over four abstract,
   overlapping tiers asks for a relative comparison across fuzzy boundaries.
   T1 ("polish, instruction density") and T2 ("professional analysis, moderately
   complex judgment") are not operationally separable as written. Jev's pull to
   the middle tier is the expected symptom.
2. **The benchmark may be partly lexical.** A bag-of-words model reaching 78.9%
   on template-disjoint rows means tier is strongly predicted by vocabulary. Some
   of that is real signal; some may be the synthetic templates making tier ≈ topic.
   This needs a sanity check before we treat 78.9% as the bar.
3. **The savings story is on hold.** Under-routing 62% of T3 tasks is exactly the
   failure the cost model ignores. Do not present savings yet.

## Recommendation (do not run the blind test yet)

1. **Decompose the question.** One request, several atomic questions combined in
   code (fan-out / composite scoring):
   - Noul: is this a single bounded step with limited context? (T0 anchor)
   - Noul: does it require integrating a large or complex body of context?
   - Noul: does it require multi-step synthesis or moderately complex judgment?
   - Noul: does it involve deep ambiguity, conflicting evidence, high-stakes
     judgment, long-horizon planning, or cross-system work? (T3 anchor)
   Map the pattern to a tier in code; keep the tier rubric semantics unchanged but
   bump to `rubric_version: 2.0` because the question design changes.
2. **Audit the labels at the T1/T2 boundary.** Sample 30 boundary prompts, check
   whether our own rubric would label them the same way twice.
3. **Re-run dev**, compare against the same baselines, and only then consider the
   blind test.
