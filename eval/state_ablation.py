#!/usr/bin/env python3
"""State ablation: does classifying the full intercepted request beat the bare prompt?

Runs the same Jev rubric over two renderings of each row:
  bare = just the user request
  full = the whole intercepted request (harness frame, tools, context lines)

    python3 eval/state_ablation.py --slice harness
"""
import argparse, asyncio, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from routing import tier_from_nouls, TIERS, IDX  # noqa: E402


def load_dotenv(path):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def bare_of(prompt):
    return prompt.split("[user] ", 1)[-1].strip() if "[user] " in prompt else prompt.strip()


async def classify(client, sem, state, questions):
    async with sem:
        try:
            res = await client.system_one(state, questions)
            nouls = {k: float(res.nouls[k].noul) for k in questions}
            return tier_from_nouls(nouls), nouls
        except Exception as e:  # noqa: BLE001
            return None, {"error": f"{type(e).__name__}: {e}"}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "all-prompts-v2.jsonl"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--slice", default="harness", choices=["business", "harness", "all"])
    ap.add_argument("--limit", type=int, default=120)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "state_ablation.jsonl"))
    a = ap.parse_args()
    load_dotenv(os.path.join(HERE, "..", ".env"))

    from typesafe_sdk import AsyncTypeSafeClient, Noul
    rubric = json.load(open(os.path.join(HERE, "rubric.json")))
    questions = {name: Noul(instructions=spec["instructions"]) for name, spec in rubric["questions"].items()}

    rows = [json.loads(l) for l in open(a.data) if l.strip()]
    if a.slice != "all":
        rows = [r for r in rows if r.get("prompt_style") == a.slice]
    rows = [r for r in rows if r["split"] == a.split][: a.limit]
    print(f"{len(rows)} rows | slice={a.slice} split={a.split} | rubric v{rubric['rubric_version']}")

    sem = asyncio.Semaphore(a.concurrency)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    out = open(a.out, "w")
    async with AsyncTypeSafeClient() as client:
        tasks = {r["id"]: asyncio.gather(classify(client, sem, bare_of(r["prompt"]), questions),
                                         classify(client, sem, r["prompt"], questions)) for r in rows}
        for r in rows:
            (bt, bn), (ft, fn) = await tasks[r["id"]]
            out.write(json.dumps({"id": r["id"], "gold_tier": r["gold_tier"], "bare_tier": bt, "full_tier": ft,
                                  "bare_nouls": bn, "full_nouls": fn}) + "\n")
            out.flush()
    out.close()

    recs = [json.loads(l) for l in open(a.out)]
    valid = [r for r in recs if r["bare_tier"] and r["full_tier"]]
    g = [r["gold_tier"] for r in valid]
    def m3(t): return "T0" if t == "T0" else ("T3" if t == "T3" else "T12")
    print(f"\n{'condition':8s} {'acc4':>7s} {'acc3':>7s} {'T3rec':>7s} {'agreement':>10s}")
    for label, key in (("bare", "bare_tier"), ("full", "full_tier")):
        p = [r[key] for r in valid]
        acc4 = sum(x == y for x, y in zip(g, p)) / len(valid)
        acc3 = sum(m3(x) == m3(y) for x, y in zip(g, p)) / len(valid)
        t3 = [r for r in valid if r["gold_tier"] == "T3"]
        t3r = sum(r[key] == "T3" for r in t3) / len(t3) if t3 else 0
        agree = sum(r["bare_tier"] == r["full_tier"] for r in valid) / len(valid)
        print(f"{label:8s} {acc4:7.1%} {acc3:7.1%} {t3r:7.1%} {agree:10.1%}")
    print(f"\n(agreement column = bare vs full for that condition; n={len(valid)})")


if __name__ == "__main__":
    asyncio.run(main())
