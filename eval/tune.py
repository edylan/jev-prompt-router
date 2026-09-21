#!/usr/bin/env python3
"""Offline mapping tuner — fits the Noul->tier mapping on cached Noul values.

No API calls: it reuses Nouls already stored in result files, so re-tuning is
free. Cross-validates by template, picks the best mapping by cost-weighted error,
and (with --export) writes it into eval/rubric.json as `mapping_model`.

    python3 eval/tune.py --nouls eval/results/dev-v2.jsonl eval/results/test.jsonl
    python3 eval/tune.py --nouls eval/results/*.jsonl --export
"""
import argparse, collections, itertools, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from baselines import metrics  # noqa: E402
from routing import TIERS, IDX, FEATURE_ORDER  # noqa: E402

DATA = os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl")
RUBRIC = os.path.join(HERE, "rubric.json")


def load_dataset(path):
    rows = {}
    for line in open(path):
        if line.strip():
            r = json.loads(line)
            if r.get("prompt_style") == "business":
                rows[r["id"]] = r
    return rows


def load_nouls(paths):
    out = {}
    for p in paths:
        if not os.path.exists(p):
            continue
        for line in open(p):
            if not line.strip():
                continue
            r = json.loads(line)
            n = (r.get("jev") or {}).get("nouls")
            if n:
                out[r["id"]] = n
    return out


FEATS = list(FEATURE_ORDER)


def feats(nouls):
    return [float(nouls.get(f, 0.0)) for f in FEATS]


# ---------------------------------------------------------------- candidate mappings
def make_threshold_rule(thr):
    d, m = thr.get("deep", 0.5), thr.get("multistep", 0.5)
    p = thr.get("produces_analysis")
    s, c = thr.get("single_step", 0.5), thr.get("context", 0.5)
    def rule(n):
        if n.get("deep", 0) >= d:
            return "T3"
        if (p is not None and n.get("produces_analysis", 0) >= p) or n.get("multistep", 0) >= m:
            return "T2"
        if n.get("single_step", 0) >= s and n.get("context", 0) < c:
            return "T0"
        return "T1"
    return rule


def candidates(sklearn_ok, thr):
    yield ("thresholds", make_threshold_rule(thr), None)
    if not sklearn_ok:
        return
    from sklearn.linear_model import LogisticRegression
    from sklearn.tree import DecisionTreeClassifier
    for C in (0.3, 1.0, 3.0):
        for cw in (None, "balanced", {"T0": 1, "T1": 1, "T2": 1, "T3": 2}):
            clf = LogisticRegression(C=C, max_iter=2000, class_weight=cw)
            yield (f"logreg C={C} cw={cw}", clf, "linear")
    for depth in (2, 3, 4):
        for cw in (None, "balanced", {"T0": 1, "T1": 1, "T2": 1, "T3": 2}):
            clf = DecisionTreeClassifier(max_depth=depth, class_weight=cw, random_state=0)
            yield (f"tree depth={depth} cw={cw}", clf, "tree")


def cv_score(model, kind, ids, nouls, gold, groups, n_splits=4):
    """Grouped CV by template. Returns (cost, acc, macroF1, t3recall)."""
    from sklearn.model_selection import GroupKFold
    gkf = GroupKFold(n_splits=n_splits)
    all_pred = {}
    for tr, va in gkf.split(ids, groups=groups):
        tr_ids = [ids[i] for i in tr]
        va_ids = [ids[i] for i in va]
        if kind is None:  # threshold rule: no fitting
            predict = model
        elif kind == "linear":
            from numpy import array
            clf = model.__class__(**model.get_params())
            clf.fit(array([feats(nouls[i]) for i in tr_ids]), [gold[i] for i in tr_ids])
            predict = lambda n, clf=clf: clf.predict([feats(n)])[0]
        else:
            from numpy import array
            clf = model.__class__(**model.get_params())
            clf.fit(array([feats(nouls[i]) for i in tr_ids]), [gold[i] for i in tr_ids])
            predict = lambda n, clf=clf: clf.predict([feats(n)])[0]
        for i in va_ids:
            all_pred[i] = predict(nouls[i])
    g = [gold[i] for i in ids]
    p = [all_pred[i] for i in ids]
    m = metrics(g, p)
    return m["cost"], m["acc"], m["macro_f1"], m["t3_recall"], all_pred


def export_tree(clf, feature_names):
    t = clf.tree_
    def rec(i):
        if t.children_left[i] == -1:
            return {"leaf": str(clf.classes_[int(t.value[i].argmax())])}
        return {"feature": feature_names[t.feature[i]], "threshold": float(t.threshold[i]),
                "left": rec(t.children_left[i]), "right": rec(t.children_right[i])}
    return rec(0)


def export_linear(clf, feature_names):
    return {"type": "linear", "features": feature_names, "classes": [str(c) for c in clf.classes_],
            "coef": [[float(x) for x in row] for row in clf.coef_], "intercept": [float(b) for b in clf.intercept_]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=DATA)
    ap.add_argument("--nouls", nargs="+", default=[os.path.join(HERE, "results", "dev-v2.jsonl"), os.path.join(HERE, "results", "test.jsonl")])
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--objective", default="cost", choices=["cost", "accuracy"])
    a = ap.parse_args()

    rows = load_dataset(a.data)
    nouls = load_nouls(a.nouls)
    ids = [i for i in rows if i in nouls]
    missing = len(rows) - len(ids)
    dev = [i for i in ids if rows[i]["split"] == "development"]
    test = [i for i in ids if rows[i]["split"] == "test"]
    print(f"dataset rows {len(rows)} · with Nouls {len(ids)} (missing {missing}) · dev {len(dev)} · test {len(test)}")
    gold = {i: rows[i]["gold_tier"] for i in ids}
    groups = {i: rows[i]["template_key"] for i in ids}
    global FEATS
    FEATS = [f for f in FEATURE_ORDER if all(f in nouls[i] for i in ids)]
    thr = json.load(open(RUBRIC)).get("mapping_thresholds", {})
    print(f"features available: {FEATS}")

    try:
        import sklearn  # noqa: F401
        ok = True
    except Exception:
        ok = False
        print("(scikit-learn not available: thresholds only)")

    print(f"\n=== candidates (grouped CV on dev, objective={a.objective}) ===")
    print(f"  {'candidate':30s} {'costErr':>8s} {'acc':>7s} {'macroF1':>8s} {'T3rec':>7s}")
    results = []
    for name, model, kind in candidates(ok, thr):
        cost, acc, f1, t3, _ = cv_score(model, kind, dev, nouls, gold, [groups[i] for i in dev])
        results.append((cost if a.objective == "cost" else -acc, name, model, kind, cost, acc, f1, t3))
        print(f"  {name:30s} {cost:8.3f} {acc:7.1%} {f1:8.3f} {t3:7.1%}")
    results.sort(key=lambda r: (r[0], -r[5]))
    best = results[0]
    _, name, model, kind, cost, acc, f1, t3 = best
    print(f"\nselected: {name}  (dev CV costErr {cost:.3f}, acc {acc:.1%}, T3rec {t3:.1%})")

    # refit on all of dev, score test as a diagnostic (this test was already seen once)
    from numpy import array
    if kind is None:
        test_pred = [model(nouls[i]) for i in test]
        exported = None
    else:
        clf = model.__class__(**model.get_params())
        clf.fit(array([feats(nouls[i]) for i in dev]), [gold[i] for i in dev])
        test_pred = [str(clf.predict([feats(nouls[i])])[0]) for i in test]
        exported = export_linear(clf, FEATS) if kind == "linear" else {"type": "tree", "features": FEATS, "tree": export_tree(clf, FEATS)}
    tm = metrics([gold[i] for i in test], test_pred) if test else None
    if tm:
        print(f"held-out test (diagnostic): acc {tm['acc']:.1%} within1 {tm['within1']:.1%} macroF1 {tm['macro_f1']:.3f} T3rec {tm['t3_recall']:.1%} costErr {tm['cost']:.3f}")
    else:
        print("no test Nouls provided: tuning on dev only (run the test split, then re-run this to compare)")

    if a.export:
        rub = json.load(open(RUBRIC))
        if exported:
            rub["mapping_model"] = exported
        else:
            rub.pop("mapping_model", None)
        rub["tuning"] = {
            "method": name,
            "objective": a.objective,
            "trained_on": f"development split ({len(dev)} rows), grouped CV by template",
            "split_version": "stratified-1",
            "cv_cost_error": round(cost, 4), "cv_accuracy": round(acc, 4),
            "cv_macro_f1": round(f1, 4), "cv_t3_recall": round(t3, 4),
        }
        json.dump(rub, open(RUBRIC, "w"), indent=2)
        open(RUBRIC, "a").write("\n")
        print(f"\nexported mapping to {os.path.relpath(RUBRIC)} (method: {name})")


if __name__ == "__main__":
    main()
