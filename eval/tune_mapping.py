#!/usr/bin/env python3
"""Inspect the decomposed Noul signal and tune the code mapping on a dev run.

No API calls: the Noul values are stored in the results, so mapping is free to
re-tune. Reports per-tier signal and the accuracy / T3-recall tradeoff.

    python3 eval/tune_mapping.py --results eval/results/dev-v2.jsonl
"""
import argparse, collections, itertools, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from baselines import metrics  # noqa: E402
from routing import TIERS, IDX  # noqa: E402

FEATS = ["single_step", "multistep", "deep", "context"]


def apply_rule(n, d, m, s, c):
    if n.get("deep", 0) >= d:
        return "T3"
    if n.get("multistep", 0) >= m:
        return "T2"
    if n.get("single_step", 0) >= s and n.get("context", 0) < c:
        return "T0"
    return "T1"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(HERE, "results", "dev-v2.jsonl"))
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl"))
    a = ap.parse_args()

    rows = {json.loads(l)["id"]: json.loads(l) for l in open(a.data) if l.strip()}
    recs = [json.loads(l) for l in open(a.results) if l.strip()]
    recs = [r for r in recs if (r.get("jev") or {}).get("nouls")]
    gold = [rows[r["id"]]["gold_tier"] for r in recs]
    N = [r["jev"]["nouls"] for r in recs]
    print(f"{len(recs)} rows with Noul values")

    print("\n=== Noul signal by gold tier (mean, and share > 0.5) ===")
    print(f"  {'tier':5s} {'n':>4s} " + " ".join(f"{f:>13s}" for f in FEATS))
    for t in TIERS:
        idx = [i for i, g in enumerate(gold) if g == t]
        cell = []
        for f in FEATS:
            vals = [N[i].get(f, 0) for i in idx]
            cell.append(f"{sum(vals)/len(vals):.2f} ({sum(v>0.5 for v in vals)/len(vals):.0%})")
        print(f"  {t:5s} {len(idx):4d} " + " ".join(f"{x:>13s}" for x in cell))

    print("\n=== Grid search over mapping thresholds ===")
    grid = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    results = []
    for d, m, s, c in itertools.product(grid, repeat=4):
        pred = [apply_rule(n, d, m, s, c) for n in N]
        mm = metrics(gold, pred)
        results.append((mm["cost"], mm["acc"], mm["t3_recall"], mm["macro_f1"], (d, m, s, c)))
    results.sort()
    by_acc = sorted(results, key=lambda r: -r[1])
    print(f"  {'objective':22s} {'acc':>7s} {'macroF1':>8s} {'T3rec':>7s} {'costErr':>8s}   thresholds d,m,s,c")
    for label, r in [("min cost error", results[0]), ("max accuracy", by_acc[0])]:
        c_, acc, t3, f1, th = r
        print(f"  {label:22s} {acc:7.1%} {f1:8.3f} {t3:7.1%} {c_:8.3f}   {th}")
    # best accuracy subject to T3 recall >= 0.95
    hi = [r for r in results if r[2] >= 0.95]
    if hi:
        r = max(hi, key=lambda r: r[1])
        print(f"  {'max acc @ T3rec>=95%':22s} {r[1]:7.1%} {r[3]:8.3f} {r[2]:7.1%} {r[0]:8.3f}   {r[4]}")
    # a few points along the frontier
    print("\n  frontier (best accuracy per T3-recall band):")
    for lo in [0.5, 0.7, 0.85, 0.95, 1.0]:
        band = [r for r in results if r[2] >= lo]
        if band:
            r = max(band, key=lambda r: r[1])
            print(f"    T3rec>={lo:.2f}  acc={r[1]:5.1%} macroF1={r[3]:.3f} costErr={r[0]:.3f}  th={r[4]}")

    # compare to the shipped v1 choice and the naive-bayes bar
    print("\n  reference: v1 single-Choice acc 62.0% T3rec 38.1% costErr 0.624 | naive-bayes acc 78.9% costErr 0.444")


if __name__ == "__main__":
    main()
