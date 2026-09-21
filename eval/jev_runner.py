#!/usr/bin/env python3
"""Jev runner for the prompt-routing benchmark.

Classifies each prompt into a capability tier (T0-T3) with one Jev Choice
question, then applies the routing policy and writes one result per line so the
dashboard fills in live.

Setup:
    pip install typesafe-sdk
    # .env at the repo root with TYPESAFE_API_KEY=...

Validate the request without spending:
    python3 eval/jev_runner.py --split development --limit 1 --dry-run

Run:
    python3 eval/jev_runner.py --split development --out eval/results/dev.jsonl
    python3 eval/jev_runner.py --split test --limit 50 --out eval/results/test50.jsonl
"""
import argparse, asyncio, json, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from routing import load_registry, load_policy, route_row, TIERS  # noqa: E402

TIER_DEFS = {
    "T0": "A capable local model of roughly 12B parameters or less. Bounded rewriting, extraction, formatting, simple code, and clear single-step tasks with limited context.",
    "T1": "An inexpensive hosted general model. A small local model is not dependable enough because of context size, instruction density, synthesis, or polish, but advanced reasoning is not required.",
    "T2": "A high-capability, cost-efficient cloud model. Reliable multi-step synthesis, professional analysis, repository work, tool use, and moderately complex judgment.",
    "T3": "A premium frontier or deliberate-reasoning model. Deep ambiguity, long-horizon planning, high-stakes judgment, complex cross-system work, or tasks where under-routing is costly.",
}
QUESTION = ("What is the minimum model capability tier sufficient to complete this request reliably and "
            "professionally, assuming the model receives the referenced materials and ordinary tools named "
            "in the request?")
RUBRIC_VERSION = "inline"

# The frozen rubric lives in eval/rubric.json and is the source of truth. The
# inline values above are only a fallback if the file is missing.
_RUBRIC_PATH = os.path.join(HERE, "rubric.json")
if os.path.exists(_RUBRIC_PATH):
    with open(_RUBRIC_PATH) as _f:
        _RUBRIC = json.load(_f)
    TIER_DEFS = _RUBRIC.get("criteria", TIER_DEFS)
    QUESTION = _RUBRIC.get("question", QUESTION)
    RUBRIC_VERSION = _RUBRIC.get("rubric_version", RUBRIC_VERSION)


def load_dotenv(path):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def order_rows(rows, how):
    if how == "dataset":
        return rows
    if how == "shuffle":
        r = list(rows); random.Random(0).shuffle(r); return r
    # interleave: round-robin across gold tiers so the inbox fills with a spread
    buckets = {t: [r for r in rows if r["gold_tier"] == t] for t in TIERS}
    out, i = [], 0
    while any(buckets.values()):
        for t in TIERS:
            if buckets[t]:
                out.append(buckets[t].pop(0))
        i += 1
        if i > 100000:
            break
    return out


async def classify_one(client, sem, row, prompt_field, policy, models):
    async with sem:
        t0 = time.perf_counter()
        rec = {
            "id": row["id"], "split": row["split"], "prompt_style": row.get("prompt_style"),
            "category": row.get("category"), "business_function": row.get("business_function"),
            "harness": row.get("harness"), "gold_tier": row["gold_tier"],
            "prompt": row[prompt_field], "simulated": False, "rubric_version": RUBRIC_VERSION,
            "jev": {"error": None}, "route": None, "correct": None, "cost_weight": None,
        }
        try:
            from typesafe_sdk import Choice
            res = await client.system_one(row[prompt_field], {"tier": Choice(instructions=QUESTION, criteria=TIER_DEFS)})
            ans = res.choices["tier"]
            usage = getattr(res, "usage", None)
            rec["jev"] = {
                "choice": ans.choice,
                "confidence": getattr(ans, "confidence", None),
                "probabilities": dict(getattr(ans, "probabilities", {}) or {}),
                "model": getattr(res, "model", None),
                "input_tokens": getattr(usage, "input_tokens", None) if usage else None,
                "output_tokens": getattr(usage, "output_tokens", None) if usage else None,
                "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
                "error": None,
            }
            if ans.choice in ("T0", "T1", "T2", "T3"):
                rec["route"] = route_row(row, ans.choice, rec["jev"]["confidence"], policy, models)
                rec["correct"] = ans.choice == row["gold_tier"]
        except Exception as e:  # noqa: BLE001
            rec["jev"] = {"error": f"{type(e).__name__}: {e}", "latency_ms": round((time.perf_counter() - t0) * 1000, 1)}
        return rec


async def run(args):
    load_dotenv(os.path.join(HERE, "..", ".env"))
    if not os.environ.get("TYPESAFE_API_KEY"):
        print("ERROR: TYPESAFE_API_KEY is not set. Put it in .env at the repo root.", file=sys.stderr)
        return 2
    rows = [json.loads(l) for l in open(args.data) if l.strip()]
    if args.slice:
        rows = [r for r in rows if r.get("prompt_style") == args.slice]
    if args.split and args.split != "all":
        rows = [r for r in rows if r["split"] == args.split]
    rows = order_rows(rows, args.order)
    if args.limit:
        rows = rows[: args.limit]

    policy, models = load_policy(args.policy), load_registry(args.registry)
    prompt_field = "prompt_with_ambient" if args.ambient else "prompt"

    done = set()
    if args.resume and os.path.exists(args.out):
        done = {json.loads(l)["id"] for l in open(args.out) if l.strip()}
    todo = [r for r in rows if r["id"] not in done]
    print(f"rows={len(rows)} todo={len(todo)} (already done: {len(done)})  model={args.model} concurrency={args.concurrency} rubric=v{RUBRIC_VERSION}")
    print(f"output={args.out}")

    if args.dry_run:
        print("\n--- dry run: request payload for the first row ---")
        print(json.dumps({"state": todo[0][prompt_field] if todo else rows[0][prompt_field],
                          "model": args.model,
                          "questions": {"tier": {"type": "choice", "instructions": QUESTION, "criteria": TIER_DEFS}}}, indent=2)[:4000])
        print("\nDry run only. No API call was made.")
        return 0

    from typesafe_sdk import AsyncTypeSafeClient
    sem = asyncio.Semaphore(args.concurrency)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    f = open(args.out, "a")
    t0 = time.perf_counter()
    n = 0
    try:
        async with AsyncTypeSafeClient(model=args.model) as client:
            tasks = [asyncio.create_task(classify_one(client, sem, r, prompt_field, policy, models)) for r in todo]
            for fut in asyncio.as_completed(tasks):
                rec = await fut
                f.write(json.dumps(rec) + "\n")
                f.flush()
                n += 1
                if args.progress_every and n % args.progress_every == 0:
                    rate = n / max(1e-6, time.perf_counter() - t0)
                    print(f"  {n}/{len(todo)}  {rate:5.1f}/s")
    finally:
        f.close()
    print(f"done {n} in {time.perf_counter() - t0:.1f}s -> {args.out}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl"))
    ap.add_argument("--out", default=os.path.join(HERE, "results", "run.jsonl"))
    ap.add_argument("--split", default="development", choices=["all", "development", "test"])
    ap.add_argument("--slice", default=None, choices=[None, "business", "harness"])
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--model", default="jev-latest")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--order", default="interleave", choices=["dataset", "shuffle", "interleave"])
    ap.add_argument("--ambient", action="store_true", help="send prompt_with_ambient instead of prompt")
    ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--registry", default=None)
    ap.add_argument("--policy", default=None)
    ap.add_argument("--progress-every", type=int, default=25)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
