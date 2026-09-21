#!/usr/bin/env python3
"""Shared routing, cost, and summary logic for the Jev router benchmark.

Deterministic, dependency-free. Used by the runner, the simulator, and the
dashboard server so every view of the data agrees.

Capability tier (T0-T3) is what Jev classifies. Cost band, vendor, origin, and
governance are a separate axis applied here in code, exactly as designed.
"""
import json, collections, math, os, statistics

TIERS = ["T0", "T1", "T2", "T3"]
IDX = {t: i for i, t in enumerate(TIERS)}
HERE = os.path.dirname(os.path.abspath(__file__))


def load_json(path):
    with open(path) as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def load_registry_doc(path=None):
    return load_json(path or os.path.join(HERE, "model_registry.json"))


def load_registry(path=None):
    return load_registry_doc(path)["models"]


def load_policy(path=None):
    return load_json(path or os.path.join(HERE, "policy.json"))


_RUBRIC = None


def load_rubric(path=None):
    global _RUBRIC
    if _RUBRIC is None:
        p = path or os.path.join(HERE, "rubric.json")
        _RUBRIC = load_json(p) if os.path.exists(p) else {}
    return _RUBRIC


FEATURE_ORDER = ["single_step", "multistep", "deep", "context"]


def _linear_tier(nouls, model):
    x = [float(nouls.get(f, 0.0)) for f in model.get("features", FEATURE_ORDER)]
    scores = [sum(c * xi for c, xi in zip(coef, x)) + b for coef, b in zip(model["coef"], model["intercept"])]
    return model["classes"][max(range(len(scores)), key=lambda i: scores[i])]


def _tree_tier(nouls, model):
    node = model["tree"]
    while "leaf" not in node:
        v = float(nouls.get(node["feature"], 0.0))
        node = node["left"] if v <= node["threshold"] else node["right"]
    return node["leaf"]


def tier_from_nouls(nouls, rubric=None):
    """Decomposed rubric: Noul values -> tier. Uses a learned mapping_model when
    present (fitted by eval/tune.py), otherwise the hand thresholds."""
    r = rubric or load_rubric()
    if r.get("mode") != "decomposed":
        return None
    mm = r.get("mapping_model")
    if mm:
        try:
            if mm.get("type") == "linear":
                return _linear_tier(nouls, mm)
            if mm.get("type") == "tree":
                return _tree_tier(nouls, mm)
        except Exception:  # noqa: BLE001 - fall back to thresholds
            pass
    thr = r.get("mapping_thresholds", {})
    d, m = thr.get("deep", 0.5), thr.get("multistep", 0.5)
    p = thr.get("produces_analysis")
    s, c = thr.get("single_step", 0.5), thr.get("context", 0.5)
    if nouls.get("deep", 0) >= d:
        return "T3"
    if (p is not None and nouls.get("produces_analysis", 0) >= p) or nouls.get("multistep", 0) >= m:
        return "T2"
    if nouls.get("single_step", 0) >= s and nouls.get("context", 0) < c:
        return "T0"
    return "T1"


def effective_tier(rec):
    """Tier for a result: re-derive from stored Nouls when present, so a change
    to the rubric thresholds re-scores old runs without new API calls."""
    j = rec.get("jev") or {}
    if j.get("nouls"):
        t = tier_from_nouls(j["nouls"])
        if t:
            return t
    return j.get("choice")


def estimate_tokens(text):
    return max(1, round(len(text) / 4))


# ------------------------------------------------------------------ eligibility & routing
def is_eligible(model, gov, policy):
    if model["origin"] == "CN" and not policy.get("allow_cn_origin", False):
        return False
    if gov:
        if gov.get("data_sensitivity") == "high" and policy.get("high_sensitivity_requires_allowlist", True):
            if model["serving_locus"] != "local" and model["vendor"] not in policy.get("vendor_allowlist", []):
                return False
        if policy.get("enforce_residency") and model["serving_locus"] != "local":
            if gov.get("data_residency_requirement") not in policy.get("allowed_residencies", []):
                return False
    return True


def model_cost(model, input_tokens, output_tokens):
    return (input_tokens / 1e6) * model["input_usd_per_mtok"] + (output_tokens / 1e6) * model["output_usd_per_mtok"]


def pick_model(required_tier, gov, policy, models, input_tokens, output_tokens_by_tier):
    """Cheapest eligible model at or above the required tier. Returns (model, escalated, reason)."""
    start = IDX[required_tier]
    for i in range(start, len(TIERS)):
        t = TIERS[i]
        cands = [m for m in models if m["capability_tier"] == t and is_eligible(m, gov, policy)]
        if cands:
            out_tokens = output_tokens_by_tier.get(t, 800)
            best = min(cands, key=lambda m: (model_cost(m, input_tokens, out_tokens), m["input_usd_per_mtok"]))
            reason = "cheapest_eligible_in_tier" if i == start else "escalated_up_for_policy"
            return best, i > start, reason
    # nothing eligible anywhere: fall back to the highest-capability eligible model
    cands = [m for m in models if is_eligible(m, gov, policy)]
    if not cands:
        return None, True, "no_eligible_model"
    best = max(cands, key=lambda m: IDX[m["capability_tier"]])
    return best, True, "fallback_highest_eligible"


def policy_escalate(choice, confidence, policy):
    """Confidence-gated escalation: below threshold, move up one tier."""
    if confidence is not None and confidence < policy.get("escalate_below_confidence", 0.0):
        return TIERS[min(len(TIERS) - 1, IDX[choice] + 1)], True
    return choice, False


def route_row(row, chosen_tier, confidence, policy, models):
    gov = row.get("governance")
    prompt = row.get("prompt", "")
    in_tokens = estimate_tokens(prompt)
    routed_tier, escalated_conf = policy_escalate(chosen_tier, confidence, policy)
    model, escalated_policy, reason = pick_model(routed_tier, gov, policy, models, in_tokens, policy["output_tokens_by_tier"])
    out_tokens = policy["output_tokens_by_tier"].get(routed_tier, 800)
    cost = model_cost(model, in_tokens, out_tokens) if model else 0.0
    baseline_model = next((m for m in models if m["id"] == policy.get("baseline_model_id")), None)
    baseline = model_cost(baseline_model, in_tokens, out_tokens) if baseline_model else 0.0
    return {
        "policy": {k: policy[k] for k in ("allow_cn_origin", "high_sensitivity_requires_allowlist", "escalate_below_confidence") if k in policy},
        "chosen_model": model["id"] if model else None,
        "chosen_model_display": model["display"] if model else None,
        "chosen_tier": model["capability_tier"] if model else None,
        "cost_band": model["cost_band"] if model else None,
        "origin": model["origin"] if model else None,
        "serving_locus": model["serving_locus"] if model else None,
        "escalated_for_confidence": escalated_conf,
        "escalated_for_policy": escalated_policy,
        "reason": reason,
        "est_input_tokens": in_tokens,
        "est_output_tokens": out_tokens,
        "est_cost_usd": cost,
        "baseline_cost_usd": baseline,
        "saving_usd": baseline - cost,
    }


# ------------------------------------------------------------------ metrics
def cost_weight(gold, pred):
    g, p = IDX.get(gold), IDX.get(pred)
    if g is None or p is None:
        return 0
    if p == g:
        return 0
    return 3 * (g - p) if p < g else (p - g)


def _per_tier(gold, pred):
    out = {}
    for t in TIERS:
        tp = sum(g == t and p == t for g, p in zip(gold, pred))
        fp = sum(g != t and p == t for g, p in zip(gold, pred))
        fn = sum(g == t and p != t for g, p in zip(gold, pred))
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        out[t] = {"precision": prec, "recall": rec, "f1": (2 * prec * rec / (prec + rec) if prec + rec else 0.0), "support": sum(g == t for g in gold)}
    return out


# ---------------------------------------------------------------- 3-tier routing model
# T1 and T2 are not separable from a prompt (see docs/label-improvements.md), so the
# router collapses them into T12 and models the middle tier as a *mixture*: a share
# `f` of T12 work is served by cheap frontier-class models (T3, cost band C1), the
# rest by standard cloud. `f` is a policy assumption (default 0.65), reported as a
# 0.50-0.75 band, not a Jev prediction.
ROUTING_TIERS = ["T0", "T12", "T3"]


def routing_tier(tier):
    if tier == "T0":
        return "T0"
    if tier == "T3":
        return "T3"
    return "T12"


def expected_cost_3tier(req_tier, gov, in_tokens, policy, models, f):
    """Expected routed cost for one prompt under the 3-tier mixture model."""
    ot = policy.get("output_tokens_by_routing_tier", {"T0": 300, "T12": 700, "T3": 1600})
    t = routing_tier(req_tier)

    def c(m, key):
        return model_cost(m, in_tokens, ot.get(key, 700))

    def cheapest(pred, key):
        cands = [m for m in models if pred(m) and is_eligible(m, gov, policy)]
        return min(cands, key=lambda m: c(m, key)) if cands else None

    if t == "T0":
        m = cheapest(lambda m: m["capability_tier"] == "T0", "T0")
        return c(m, "T0") if m else None
    if t == "T3":
        m = cheapest(lambda m: m["capability_tier"] == "T3", "T3")
        return c(m, "T3") if m else None
    # T12 is served by at least flash-frontier (T2); the substitution share `f` goes to
    # the cheapest frontier-class model (T3) instead. We never route the uncertain middle
    # tier to T1 models, since we cannot tell T1 from T2.
    std = cheapest(lambda m: m["capability_tier"] == "T2", "T12")
    cf = cheapest(lambda m: m["capability_tier"] == "T3", "T12")
    if cf is None:
        return c(std, "T12") if std else None
    if std is None:
        return c(cf, "T12")
    return f * c(cf, "T12") + (1 - f) * c(std, "T12")


def summarize(rows, results, policy, models, limit=None):
    """rows: dataset rows; results: {id: result}. Missing ids are pending."""
    by_id = {r["id"]: r for r in rows}
    done = [results[r["id"]] for r in rows if r["id"] in results]
    ok = [x for x in done if not (x.get("jev") or {}).get("error")]
    errored = [x for x in done if (x.get("jev") or {}).get("error")]

    gold = [by_id[x["id"]]["gold_tier"] for x in ok]
    pred = [effective_tier(x) for x in ok]
    n = len(ok)
    conf = [(x.get("jev") or {}).get("confidence") for x in ok if (x.get("jev") or {}).get("confidence") is not None]

    quality = {"n": n}
    if n:
        acc = sum(g == p for g, p in zip(gold, pred)) / n
        per_tier = _per_tier(gold, pred)
        macro_f1 = sum(per_tier[t]["f1"] for t in TIERS) / len(TIERS)
        confusion = {g: {p: 0 for p in TIERS} for g in TIERS}
        for g, p in zip(gold, pred):
            if p in confusion.get(g, {}):
                confusion[g][p] += 1
        def _m3(t):
            return "T0" if t == "T0" else ("T3" if t == "T3" else "T12")
        acc3 = sum(1 for g, p in zip(gold, pred) if p is not None and _m3(g) == _m3(p)) / n
        quality.update({
            "accuracy": acc, "macro_f1": macro_f1,
            "accuracy_3tier": acc3,
            "t3_recall": per_tier["T3"]["recall"],
            "cost_weighted_mean": sum(cost_weight(g, p) for g, p in zip(gold, pred)) / n,
            "per_tier": per_tier, "confusion": confusion,
            "correct": sum(g == p for g, p in zip(gold, pred)),
        })

    confidence = {"n": len(conf)}
    if conf:
        thr = policy.get("escalate_below_confidence", 0.6)
        hist = [0] * 10
        for c in conf:
            hist[min(9, int(c * 10))] += 1
        confidence.update({
            "mean": statistics.mean(conf), "p10": sorted(conf)[int(0.1 * (len(conf) - 1))],
            "below_threshold": sum(c < thr for c in conf), "threshold": thr, "histogram": hist,
        })

    route_by_id = {}
    for x in ok:
        choice = effective_tier(x)
        if choice not in IDX:
            continue
        row = by_id[x["id"]]
        route_by_id[x["id"]] = route_row(row, choice, (x.get("jev") or {}).get("confidence"), policy, models)
    routes = list(route_by_id.values())
    cost = {"n": len(routes)}
    if routes:
        routed = sum(r["est_cost_usd"] for r in routes)
        baseline = sum(r["baseline_cost_usd"] for r in routes)
        jev_in = sum((x.get("jev") or {}).get("input_tokens", 0) for x in ok)
        jev_cost = (jev_in / 1e6) * policy.get("jev_input_usd_per_mtok", 42.0)
        # oracle: route using the gold tier
        oracle = 0.0
        for x in ok:
            row = by_id[x["id"]]
            m, _, _ = pick_model(row["gold_tier"], row.get("governance"), policy, models, estimate_tokens(row["prompt"]), policy["output_tokens_by_tier"])
            oracle += model_cost(m, estimate_tokens(row["prompt"]), policy["output_tokens_by_tier"].get(row["gold_tier"], 800)) if m else 0.0
        cost.update({
            "classification_usd": jev_cost, "jev_input_tokens": jev_in,
            "routed_usd": routed, "baseline_usd": baseline, "oracle_routed_usd": oracle,
            "savings_usd": baseline - routed,
            "savings_pct": (1 - routed / baseline) if baseline else 0.0,
            "net_savings_usd": (baseline - routed) - jev_cost,
            "avg_routed_usd": routed / len(routes), "avg_baseline_usd": baseline / len(routes),
            "escalated": sum(1 for r in routes if r["escalated_for_confidence"] or r["escalated_for_policy"]),
        })

    # 3-tier mixture model. T1/T2 are not separable from a prompt, so the middle tier is
    # priced as a mixture of cheap frontier-class (T3,C1) and standard cloud, over a band
    # of substitution rates. This is an assumption, not a Jev prediction.
    f_default = policy.get("cheap_frontier_substitution", 0.65)
    baseline_model = next((m for m in models if m["id"] == policy.get("baseline_model_id")), None)
    ot3 = policy.get("output_tokens_by_routing_tier", {"T0": 300, "T12": 700, "T3": 1600})
    tiers_ok = [(by_id[x["id"]], effective_tier(x)) for x in ok]
    tiers_ok = [(r, t) for r, t in tiers_ok if t in IDX]
    if tiers_ok and baseline_model:
        base3 = sum(model_cost(baseline_model, estimate_tokens(r["prompt"]), ot3.get(routing_tier(t), 700)) for r, t in tiers_ok)

        def _routed(f):
            return sum((expected_cost_3tier(t, r.get("governance"), estimate_tokens(r["prompt"]), policy, models, f) or 0.0) for r, t in tiers_ok)
        three = {"n": len(tiers_ok), "f_default": f_default, "baseline_usd": base3, "band": {}}
        for f in (0.50, 0.65, 0.75):
            rc = _routed(f)
            three["band"][f"{f:.2f}"] = {"routed_usd": rc, "savings_usd": base3 - rc, "savings_pct": (1 - rc / base3) if base3 else 0.0}
        for label, f in (("all_standard", 0.0), ("all_cheap_frontier", 1.0)):
            rc = _routed(f)
            three[label] = {"routed_usd": rc, "savings_pct": (1 - rc / base3) if base3 else 0.0}
        cost["three_tier"] = three

    mix = {
        "gold_tiers": dict(collections.Counter(by_id[x["id"]]["gold_tier"] for x in ok)),
        "jev_tiers": dict(collections.Counter(p for p in pred if p)),
        "models": dict(collections.Counter(r["chosen_model"] for r in routes if r.get("chosen_model"))),
        "cost_bands": dict(collections.Counter(r["cost_band"] for r in routes if r.get("cost_band"))),
    }

    def group(field):
        out = collections.defaultdict(lambda: {"n": 0, "correct": 0, "routed_usd": 0.0, "baseline_usd": 0.0})
        for x in ok:
            row = by_id[x["id"]]
            key = row.get(field) or "unknown"
            g = out[key]
            g["n"] += 1
            g["correct"] += int(x.get("jev", {}).get("choice") == row["gold_tier"])
            if x["id"] in route_by_id:
                g["routed_usd"] += route_by_id[x["id"]]["est_cost_usd"]
                g["baseline_usd"] += route_by_id[x["id"]]["baseline_cost_usd"]
        for k, g in out.items():
            g["accuracy"] = g["correct"] / g["n"] if g["n"] else 0.0
        return dict(out)

    lat = [(x.get("jev") or {}).get("latency_ms") for x in ok if (x.get("jev") or {}).get("latency_ms") is not None]
    latency = {"n": len(lat)}
    if lat:
        s = sorted(lat)
        latency.update({"mean_ms": statistics.mean(lat), "p50_ms": s[len(s) // 2], "p95_ms": s[int(0.95 * (len(s) - 1))]})

    total = len(rows) if limit is None else min(limit, len(rows))
    return {
        "progress": {"total": total, "classified": len(done), "ok": len(ok), "errors": len(errored), "pending": max(0, total - len(done)), "pct": (len(done) / total) if total else 0.0},
        "quality": quality, "confidence": confidence, "cost": cost, "mix": mix,
        "by_function": group("business_function"), "by_category": group("category"),
        "by_harness": group("harness"), "by_style": group("prompt_style"),
        "latency": latency,
        "model_meta": {"jev_model": (ok[0].get("jev") or {}).get("model") if ok else None},
    }


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--registry", default=None)
    ap.add_argument("--policy", default=None)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.data) if l.strip()]
    results = {r["id"]: r for r in load_jsonl(a.results)}
    s = summarize(rows, results, load_policy(a.policy), load_registry(a.registry))
    print(json.dumps(s, indent=2, default=str))
