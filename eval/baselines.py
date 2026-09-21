#!/usr/bin/env python3
"""Baseline harness for the Jev router benchmark.

Every number for Jev must be accompanied by these baselines on the same split.
No third-party dependencies.

  python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl
  python3 eval/baselines.py --data datasets/v2/all-prompts-v2.jsonl --slice all
  python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl --ambient
  python3 eval/baselines.py --data datasets/v2/business-prompts-v2.jsonl --leaky

Reported for each predictor:
  - row accuracy and macro-F1
  - T3 recall (frontier-needed; the asymmetric-loss class)
  - cost-weighted error (under-provisioning penalised 3x over over-provisioning)
  - template-level accuracy (majority prediction per template_key)
"""
import argparse, collections, itertools, json, math, random

TIERS = ["T0", "T1", "T2", "T3"]
IDX = {t: i for i, t in enumerate(TIERS)}


def load(path, text_field="prompt"):
    rows = [json.loads(line) for line in open(path) if line.strip()]
    for r in rows:
        r["_text"] = r[text_field]
    return rows


def tokens(s):
    import re
    return re.findall(r"[a-z][a-z\-]+", s.lower())


def cost(gold, pred):
    g, p = IDX[gold], IDX[pred]
    if p == g:
        return 0
    return 3 * (g - p) if p < g else (p - g)  # under-provision worse


# ------------------------------------------------------------------ predictors
def majority(dev, test):
    m = collections.Counter(r["gold_tier"] for r in dev).most_common(1)[0][0]
    return [m for _ in test]


def wordcount(dev, test):
    wc = lambda r: len(r["_text"].split())
    cands = sorted(set(wc(r) for r in dev))
    qs = sorted(set(cands[int(q * (len(cands) - 1))] for q in [i / 40 for i in range(1, 40)]))
    best = (0, None)
    for a, b, c in itertools.combinations(qs, 3):
        pr = ["T0" if wc(r) <= a else "T1" if wc(r) <= b else "T2" if wc(r) <= c else "T3" for r in dev]
        s = sum(p == r["gold_tier"] for p, r in zip(pr, dev)) / len(dev)
        if s > best[0]:
            best = (s, (a, b, c))
    a, b, c = best[1]
    return ["T0" if wc(r) <= a else "T1" if wc(r) <= b else "T2" if wc(r) <= c else "T3" for r in test]


def nearest_neighbour(dev, test):
    dt = [(set(tokens(r["_text"])), r["gold_tier"]) for r in dev]
    out = []
    for r in test:
        t = set(tokens(r["_text"]))
        best_s, best_t = -1.0, "T0"
        for d, tier in dt:
            u = len(t | d)
            if not u:
                continue
            s = len(t & d) / u
            if s > best_s:
                best_s, best_t = s, tier
        out.append(best_t)
    return out


def naive_bayes(dev, test):
    cls = collections.Counter(r["gold_tier"] for r in dev)
    wc = {t: collections.Counter() for t in TIERS}
    tot = {t: 0 for t in TIERS}
    vocab = set()
    for r in dev:
        for w in tokens(r["_text"]):
            wc[r["gold_tier"]][w] += 1
            tot[r["gold_tier"]] += 1
            vocab.add(w)
    V, N = len(vocab), len(dev)
    out = []
    for r in test:
        sc = {}
        for t in TIERS:
            s = math.log(cls[t] / N)
            for w in tokens(r["_text"]):
                s += math.log((wc[t][w] + 1) / (tot[t] + V))
            sc[t] = s
        out.append(max(sc, key=sc.get))
    return out


PREDICTORS = {"majority": majority, "wordcount": wordcount, "1-nn": nearest_neighbour, "naive-bayes": naive_bayes}


# ------------------------------------------------------------------ metrics
def metrics(gold, pred):
    n = len(gold)
    acc = sum(g == p for g, p in zip(gold, pred)) / n
    f1s, recall = [], {}
    for t in TIERS:
        tp = sum(g == t and p == t for g, p in zip(gold, pred))
        fp = sum(g != t and p == t for g, p in zip(gold, pred))
        fn = sum(g == t and p != t for g, p in zip(gold, pred))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        recall[t] = rec
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    macro_f1 = sum(f1s) / len(f1s)
    mean_cost = sum(cost(g, p) for g, p in zip(gold, pred)) / n
    return {"acc": acc, "macro_f1": macro_f1, "t3_recall": recall["T3"], "cost": mean_cost}


def template_accuracy(rows, pred):
    by_t = collections.defaultdict(list)
    for r, p in zip(rows, pred):
        by_t[r["template_key"]].append((r["gold_tier"], p))
    correct = 0
    for _, pairs in by_t.items():
        gold = pairs[0][0]
        votes = collections.Counter(p for _, p in pairs)
        pred_t = max(votes.items(), key=lambda kv: (kv[1], -IDX[kv[0]]))[0]
        correct += pred_t == gold
    return correct / len(by_t), len(by_t)


def evaluate(name, dev, test, leaky=False):
    if leaky:
        rows = dev + test
        random.Random(0).shuffle(rows)
        cut = max(1, int(0.2 * len(rows)))
        dev, test = rows[:cut], rows[cut:]
    gold = [r["gold_tier"] for r in test]
    print(f"\n  {'predictor':14s} {'acc':>7s} {'macroF1':>8s} {'T3rec':>7s} {'cost':>7s} {'tplAcc':>8s} {'tplN':>5s}")
    for name_p, fn in PREDICTORS.items():
        pred = fn(dev, test)
        m = metrics(gold, pred)
        ta, tn = template_accuracy(test, pred)
        print(f"  {name_p:14s} {m['acc']:7.1%} {m['macro_f1']:8.3f} {m['t3_recall']:7.1%} {m['cost']:7.3f} {ta:8.1%} {tn:5d}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="datasets/v2/business-prompts-v2.jsonl")
    ap.add_argument("--field", default="prompt")
    ap.add_argument("--ambient", action="store_true", help="use prompt_with_ambient instead of prompt")
    ap.add_argument("--slice", default="business", choices=["business", "harness", "all"])
    ap.add_argument("--leaky", action="store_true", help="also show an old-style random row split for contrast")
    args = ap.parse_args()

    rows = load(args.data, "prompt_with_ambient" if args.ambient else args.field)
    if args.slice == "business":
        rows = [r for r in rows if r["prompt_style"] == "business"]
    elif args.slice == "harness":
        rows = [r for r in rows if r["prompt_style"] == "harness"]
    dev = [r for r in rows if r["split"] == "development"]
    test = [r for r in rows if r["split"] == "test"]
    print(f"data={args.data} slice={args.slice} field={'prompt_with_ambient' if args.ambient else args.field}")
    print(f"dev={len(dev)} test={len(test)} templates(dev)={len(set(r['template_key'] for r in dev))} templates(test)={len(set(r['template_key'] for r in test))}")
    print("\nTEMPLATE-LEVEL SPLIT (headline; no template spans dev/test)")
    evaluate("template", dev, test)
    if args.leaky:
        print("\nROW-LEVEL SPLIT (legacy diagnostic; templates leak across the split)")
        evaluate("leaky", dev, test, leaky=True)


if __name__ == "__main__":
    main()
