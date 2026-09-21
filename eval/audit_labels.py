#!/usr/bin/env python3
"""Label audit: is the tier label actually a capability signal, or a topical one?

No API calls. Quantifies the lexical/topical confound and surfaces the fuzziest
T1/T2 and T2/T3 boundary pairs for manual review.

    python3 eval/audit_labels.py
"""
import collections, itertools, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from baselines import PREDICTORS, metrics  # noqa: E402
from routing import TIERS  # noqa: E402

DATA = os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl")


def toks(s):
    return set(re.findall(r"[a-z][a-z\-]+", s.lower()))


def jac(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0


def main():
    rows = [json.loads(l) for l in open(DATA)]
    for r in rows:
        r["_text"] = r["prompt"]
    dev = [r for r in rows if r["split"] == "development"]
    test = [r for r in rows if r["split"] == "test"]
    print(f"{len(rows)} rows · dev {len(dev)} · test {len(test)}")

    print("\n=== Is tier predicted by category alone? ===")
    # majority tier per category, learned on test, applied to dev
    cat_maj = {c: collections.Counter(r["gold_tier"] for r in test if r["category"] == c).most_common(1)[0][0]
               for c in {r["category"] for r in rows}}
    fn_maj = {f: collections.Counter(r["gold_tier"] for r in test if r["business_function"] == f).most_common(1)[0][0]
              for f in {r["business_function"] for r in rows}}
    gold = [r["gold_tier"] for r in dev]
    cpred = [cat_maj[r["category"]] for r in dev]
    fpred = [fn_maj[r["business_function"]] for r in dev]
    for name, p in [("category-majority", cpred), ("function-majority", fpred)]:
        m = metrics(gold, p)
        print(f"  {name:20s} acc={m['acc']:.1%} macroF1={m['macro_f1']:.3f}")
    nb = PREDICTORS["naive-bayes"](test, dev)
    print(f"  {'naive-bayes':20s} acc={metrics(gold, nb)['acc']:.1%}  <- from the pilot")

    print("\n=== Tier mix per category (is a category basically one tier?) ===")
    print(f"  {'category':30s} " + " ".join(f"{t:>4s}" for t in TIERS) + "   modal-share")
    for c in sorted({r["category"] for r in rows}):
        sub = [r for r in rows if r["category"] == c]
        cnt = collections.Counter(r["gold_tier"] for r in sub)
        tot = sum(cnt.values())
        modal = max(cnt.values()) / tot
        print(f"  {c:30s} " + " ".join(f"{cnt.get(t,0):4d}" for t in TIERS) + f"   {modal:5.1%}")

    print("\n=== Fuzziest boundary pairs (same category, different tier) ===")
    for pair in [("T1", "T2"), ("T2", "T3")]:
        a, b = pair
        best = []
        for c in {r["category"] for r in rows}:
            A = [r for r in rows if r["category"] == c and r["gold_tier"] == a]
            B = [r for r in rows if r["category"] == c and r["gold_tier"] == b]
            if not A or not B:
                continue
            # dedupe by template_key, compare one representative each
            repA = list({r["template_key"]: r for r in A}.values())
            repB = list({r["template_key"]: r for r in B}.values())
            for x, y in itertools.product(repA, repB):
                best.append((jac(toks(x["prompt"]), toks(y["prompt"])), c, x, y))
        best.sort(key=lambda x: x[0], reverse=True)
        print(f"\n  --- {a} vs {b}: closest pairs (high overlap = label likely inconsistent) ---")
        for s, c, x, y in best[:5]:
            print(f"  [{s:.2f}] {c}")
            print(f"     {a}: {x['prompt'][:110]}")
            print(f"     {b}: {y['prompt'][:110]}")


if __name__ == "__main__":
    main()
