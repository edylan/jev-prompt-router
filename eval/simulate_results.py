#!/usr/bin/env python3
"""Write SIMULATED Jev results so the dashboard can be built and demoed without
spending API calls. Clearly marked simulated=true and never to be used as a
result. Delete eval/results/sim.jsonl before a real run.

    python3 eval/simulate_results.py --split development --delay 0.05
    python3 eval/simulate_results.py --split test --limit 200 --delay 0.02 --out eval/results/sim-test.jsonl
"""
import argparse, json, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from routing import load_registry, load_policy, route_row, TIERS, IDX  # noqa: E402


def order_rows(rows):
    buckets = {t: [r for r in rows if r["gold_tier"] == t] for t in TIERS}
    out = []
    while any(buckets.values()):
        for t in TIERS:
            if buckets[t]:
                out.append(buckets[t].pop(0))
    return out


def simulate(row, rng, accuracy):
    gold = row["gold_tier"]
    gi = IDX[gold]
    correct = rng.random() < accuracy
    if correct:
        choice = gold
    else:
        offsets = [d for d in (-2, -1, 1, 2) if 0 <= gi + d < 4]
        weights = [1.0 / (abs(d)) for d in offsets]
        choice = TIERS[rng.choices([gi + d for d in offsets], weights=weights)[0]]
    confidence = rng.uniform(0.62, 0.97) if correct else rng.uniform(0.38, 0.74)
    probs = {}
    for t in TIERS:
        d = abs(IDX[t] - IDX[choice])
        probs[t] = 0.0 if d > 2 else (confidence if d == 0 else (1 - confidence) / (2 ** d))
    s = sum(probs.values()) or 1.0
    probs = {k: round(v / s, 4) for k, v in probs.items()}
    return {"choice": choice, "confidence": round(confidence, 3), "probabilities": probs,
            "model": "jev-1.13.0-simulated", "input_tokens": max(1, round(len(row["prompt"]) / 4)),
            "output_tokens": 4, "latency_ms": round(rng.uniform(260, 900), 1), "error": None}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "results", "sim.jsonl"))
    ap.add_argument("--split", default="development", choices=["all", "development", "test"])
    ap.add_argument("--slice", default=None, choices=[None, "business", "harness"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--accuracy", type=float, default=0.74)
    ap.add_argument("--delay", type=float, default=0.03)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    rows = [json.loads(l) for l in open(a.data) if l.strip()]
    if a.slice:
        rows = [r for r in rows if r.get("prompt_style") == a.slice]
    if a.split != "all":
        rows = [r for r in rows if r["split"] == a.split]
    rows = order_rows(rows)
    if a.limit:
        rows = rows[: a.limit]

    policy, models = load_policy(), load_registry()
    rng = random.Random(a.seed)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    with open(a.out, "w") as f:
        for i, row in enumerate(rows, 1):
            jev = simulate(row, rng, a.accuracy)
            rec = {
                "id": row["id"], "split": row["split"], "prompt_style": row.get("prompt_style"),
                "category": row.get("category"), "business_function": row.get("business_function"),
                "harness": row.get("harness"), "gold_tier": row["gold_tier"], "prompt": row["prompt"],
                "simulated": True, "jev": jev,
                "route": route_row(row, jev["choice"], jev["confidence"], policy, models),
                "correct": jev["choice"] == row["gold_tier"],
            }
            f.write(json.dumps(rec) + "\n")
            f.flush()
            if a.delay:
                time.sleep(a.delay)
            if i % 25 == 0:
                print(f"  {i}/{len(rows)}")
    print(f"wrote {len(rows)} SIMULATED results -> {a.out} (not real Jev output)")


if __name__ == "__main__":
    main()
