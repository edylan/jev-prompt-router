#!/usr/bin/env python3
"""Report for a Jev run: quality, calibration, baselines head-to-head, errors.

    python3 eval/report.py --data datasets/v2/business-prompts-v2.jsonl --results eval/results/dev.jsonl
    python3 eval/report.py --results eval/results/test.jsonl --train-split development
"""
import argparse, collections, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from baselines import PREDICTORS, metrics, template_accuracy  # noqa: E402
from routing import load_policy, load_registry, summarize, effective_tier, TIERS, IDX  # noqa: E402


def bar(v, width=28, ch="#"):
    n = int(round(v * width))
    return ch * n + "·" * (width - n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl"))
    ap.add_argument("--results", required=True)
    ap.add_argument("--train-split", default=None, help="split to train baselines on (default: the other one)")
    ap.add_argument("--bins", type=int, default=10)
    ap.add_argument("--mind-conf", type=float, default=None, help="mark confidence threshold on the calibration table")
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.data) if l.strip()]
    for r in rows:
        r["_text"] = r["prompt"]
    results = {}
    for l in open(a.results):
        if l.strip():
            r = json.loads(l)
            results[r["id"]] = r
    by_id = {r["id"]: r for r in rows}
    ev_ids = [r["id"] for r in rows if r["id"] in results]
    ok = [i for i in ev_ids if not (results[i].get("jev") or {}).get("error")]
    err = [i for i in ev_ids if (results[i].get("jev") or {}).get("error")]
    ev_rows = [by_id[i] for i in ok]
    gold = [by_id[i]["gold_tier"] for i in ok]
    pred = [effective_tier(results[i]) for i in ok]

    # training split for baselines: the other split by default (template-disjoint from eval)
    eval_splits = {by_id[i]["split"] for i in ok}
    train_split = a.train_split or ("test" if eval_splits == {"development"} else "development")
    train = [r for r in rows if r["split"] == train_split and r["id"] not in results]

    print(f"data={os.path.relpath(a.data)} results={os.path.relpath(a.results)}")
    print(f"evaluated {len(ok)} rows ({sorted(eval_splits)}) · errors {len(err)} · baselines trained on '{train_split}' ({len(train)} rows, template-disjoint)")
    s = summarize(rows, results, load_policy(), load_registry())
    q, c, cf = s["quality"], s["cost"], s["confidence"]

    print("\n=== JEV vs BASELINES (same rows) ===")
    print(f"  {'predictor':14s} {'acc':>7s} {'w1':>7s} {'macroF1':>8s} {'T3rec':>7s} {'costErr':>8s} {'tplAcc':>7s}")
    jm = metrics(gold, pred)
    jta, jtn = template_accuracy(ev_rows, pred)
    print(f"  {'JEV':14s} {jm['acc']:7.1%} {jm['within1']:7.1%} {jm['macro_f1']:8.3f} {jm['t3_recall']:7.1%} {jm['cost']:8.3f} {jta:7.1%}")
    for name, fn in PREDICTORS.items():
        p = fn(train, ev_rows)
        m = metrics(gold, p)
        ta, tn = template_accuracy(ev_rows, p)
        print(f"  {name:14s} {m['acc']:7.1%} {m['within1']:7.1%} {m['macro_f1']:8.3f} {m['t3_recall']:7.1%} {m['cost']:8.3f} {ta:7.1%}")
    print(f"  ({jtn} templates)")

    print("\n=== PER-TIER ===")
    print(f"  {'tier':5s} {'n':>4s} {'prec':>7s} {'rec':>7s} {'f1':>7s}")
    for t in TIERS:
        d = q["per_tier"][t]
        print(f"  {t:5s} {d['support']:4d} {d['precision']:7.1%} {d['recall']:7.1%} {d['f1']:7.3f}")

    print("\n=== CONFUSION (rows: gold, cols: Jev) ===")
    print("        " + "".join(f"{t:>7s}" for t in TIERS))
    for g in TIERS:
        print(f"  {g:5s} " + "".join(f"{q['confusion'][g][p]:7d}" for p in TIERS))

    print("\n=== CALIBRATION (confidence -> observed accuracy) ===")
    bins = collections.defaultdict(lambda: [0, 0.0])
    for i in ok:
        conf = results[i]["jev"].get("confidence")
        if conf is None:
            continue
        b = min(a.bins - 1, int(conf * a.bins))
        bins[b][0] += 1
        bins[b][1] += int(results[i]["jev"]["choice"] == by_id[i]["gold_tier"])
    ece = 0.0
    for b in range(a.bins):
        n, corr = bins.get(b, [0, 0.0])
        if not n:
            continue
        acc = corr / n
        mid = (b + 0.5) / a.bins
        ece += (n / len(ok)) * abs(acc - mid)
        print(f"  {b/a.bins:.1f}-{(b+1)/a.bins:.1f} n={n:3d} acc={acc:5.1%} {bar(acc)}")
    print(f"  ECE = {ece:.3f}   mean confidence = {cf.get('mean', 0):.3f}   below {cf.get('threshold')}: {cf.get('below_threshold')}")

    print("\n=== CONFIDENCE THRESHOLD (trust only conf >= t) ===")
    print(f"  {'t':>5s} {'coverage':>9s} {'acc@t':>7s} {'escalated':>10s}")
    confs = [(results[i]["jev"].get("confidence") or 0, results[i]["jev"]["choice"] == by_id[i]["gold_tier"]) for i in ok]
    for t in [0.0, 0.5, 0.6, 0.7, 0.8, 0.9]:
        kept = [c for c, _ in confs if c >= t]
        ka = [int(g) for c, g in confs if c >= t]
        print(f"  {t:5.2f} {len(kept)/len(confs):9.1%} {(sum(ka)/len(ka) if ka else 0):7.1%} {len(confs)-len(kept):10d}")

    print("\n=== COST (estimate) ===")
    print(f"  Jev classification: ${c.get('classification_usd',0):.5f} over {c.get('jev_input_tokens',0):,} input tokens")
    print(f"  routed ${c.get('routed_usd',0):.3f} vs baseline ${c.get('baseline_usd',0):.3f}  (saved {100*c.get('savings_pct',0):.1f}%)")
    print(f"  latency p50 {s['latency'].get('p50_ms')} ms  p95 {s['latency'].get('p95_ms')} ms")

    wrong = [(i, by_id[i], results[i]) for i in ok if results[i]["jev"]["choice"] != by_id[i]["gold_tier"]]
    under = [w for w in wrong if IDX[w[2]["jev"]["choice"]] < IDX[w[1]["gold_tier"]]]
    over = [w for w in wrong if IDX[w[2]["jev"]["choice"]] > IDX[w[1]["gold_tier"]]]
    print(f"\n=== ERRORS: {len(wrong)}/{len(ok)} ({len(wrong)/len(ok):.1%}) — {len(under)} under-routed, {len(over)} over-routed ===")
    for tag, group in (("UNDER", under), ("OVER", over)):
        for i, row, rec in sorted(group, key=lambda w: w[2]["jev"].get("confidence") or 0)[:8]:
            j = rec["jev"]
            print(f"  [{tag}] {row['id']} {row['category']:26s} gold={row['gold_tier']} jev={j['choice']} conf={j.get('confidence'):.2f} | {row['prompt'][:88]}")


if __name__ == "__main__":
    main()
