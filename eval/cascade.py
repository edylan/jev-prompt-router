#!/usr/bin/env python3
"""Empirical cascade: run the routed models on sampled prompts, judge with Jev.

Answers the question the routing eval cannot: does the *weakest* model that Jev
would allow actually produce an acceptable answer? Generators are OpenAI-compatible
(DeepSeek via the pi provider here); the judge is Jev (independent model family).

    python3 eval/cascade.py --per-tier 20 --dry-run
    python3 eval/cascade.py --per-tier 20 --out eval/results/cascade.jsonl

We only have cloud generators here (no local GPU, no US-frontier key), so T0 and
premium-frontier remain untested; this measures the cheap/standard/flash/frontier axis.
"""
import argparse, asyncio, json, os, re, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from routing import effective_tier, routing_tier  # noqa: E402

TIERS = ["T0", "T1", "T2", "T3"]
GENERATORS = [
    {"id": "deepseek-chat", "label": "cheap general (T1-ish)", "api_model": "deepseek-chat", "max_tokens": 1200, "reasoning": False, "cost_in": 0.27, "cost_out": 1.10},
    {"id": "deepseek-flash", "label": "flash-frontier (T2-ish)", "api_model": "deepseek-flash", "max_tokens": 8000, "reasoning": True, "cost_in": 0.30, "cost_out": 1.20},
    {"id": "deepseek-v4-pro", "label": "frontier-class (T3-ish)", "api_model": "deepseek-v4-pro", "max_tokens": 8000, "reasoning": True, "cost_in": 1.32, "cost_out": 3.96},
]
# Prompts that assume inputs we cannot supply (files, notes, schemas, transcripts) are not
# executable by any model, so they measure nothing. Filter them out of the cascade.
NEEDS_INPUT = re.compile(r"\b(this|these|the following|below|above|attached|supplied|provided|given|notes|transcript|workbook|report|excerpt|thread|schema|spreadsheet|excel|logs?|repo|files?|code|list)\b", re.I)
SYSTEM = ("You are an assistant completing a work request. Produce the deliverable directly and "
          "concisely. If essential information is genuinely missing and cannot be inferred, say so "
          "explicitly instead of inventing it.")


def deepseek_key():
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"]
    with open(os.path.expanduser("~/.pi/agent/auth.json")) as f:
        return json.load(f)["deepseek"]["key"]


def generate(gen, prompt):
    import urllib.request
    body = json.dumps({"model": gen["api_model"],
                       "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
                       "max_tokens": gen["max_tokens"], "temperature": 0.0, "stream": False}).encode()
    req = urllib.request.Request("https://api.deepseek.com/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {deepseek_key()}", "Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=240) as r:
        d = json.load(r)
    msg = d["choices"][0]["message"]
    u = d.get("usage", {})
    return {"text": (msg.get("content") or "").strip(), "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "tokens_in": u.get("prompt_tokens"), "tokens_out": u.get("completion_tokens"),
            "finish": d["choices"][0].get("finish_reason")}


JUDGE_Q = {
    "adequate": ("noul", "The response fully and correctly completes the request to a standard a competent "
                          "colleague would accept without rework. Judge the deliverable, not the style."),
    "handles_gaps": ("noul", "If the request depends on information that was not provided, the response explicitly "
                             "flags what is missing instead of silently inventing it. If nothing was missing, answer true."),
    "fabricates": ("noul", "The response invents specific facts, figures, names, or sources that were not given and "
                           "cannot be reasonably assumed."),
    "quality": ("score", ["unusable or empty", "partially useful but with material gaps", "acceptable", "strong and complete"]),
}


def build_judge():
    from typesafe_sdk import Noul, Score
    qs = {}
    for name, (kind, spec) in JUDGE_Q.items():
        qs[name] = Noul(instructions=spec) if kind == "noul" else Score(instructions="Overall quality of the response.", criteria=spec)
    return qs


async def judge(client, sem, prompt, answer):
    async with sem:
        try:
            res = await client.system_one({"request": prompt, "response": answer["text"]}, build_judge())
            return {"adequate": res.nouls["adequate"].noul, "handles_gaps": res.nouls["handles_gaps"].noul,
                    "fabricates": res.nouls["fabricates"].noul, "quality": res.scores["quality"].score}
        except Exception as e:  # noqa: BLE001
            return {"error": f"{type(e).__name__}: {e}"}


def load_dotenv(path):
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


async def run(args):
    load_dotenv(os.path.join(HERE, "..", ".env"))
    import asyncio as _a
    from typesafe_sdk import AsyncTypeSafeClient

    rows = [json.loads(l) for l in open(args.data) if l.strip()]
    if args.slice != "all":
        rows = [r for r in rows if r.get("prompt_style") == args.slice]
    rows = [r for r in rows if r["split"] == args.split]
    # prefer self-contained prompts: those that don't reference attachments we cannot supply
    selfcont = [r for r in rows if not r.get("tools_or_attachments_implied")]
    execable = [r for r in selfcont if not NEEDS_INPUT.search(r["prompt"])]
    print(f"split={args.split} slice={args.slice}: {len(rows)} rows | {len(selfcont)} without attachment flags | "
          f"{len(execable)} genuinely executable (self-contained)")
    rows = execable if args.executable_only else selfcont
    by_tier = {t: [r for r in rows if r["gold_tier"] == t][: args.per_tier] for t in TIERS}
    sample = [r for t in TIERS for r in by_tier[t]]
    print(f"sample: {len(sample)} prompts  " + " ".join(f"{t}={len(by_tier[t])}" for t in TIERS))

    plan = [(r, g) for r in sample for g in GENERATORS]
    print(f"calls: {len(plan)} generations + {len(plan)} Jev judgments")
    if args.dry_run:
        r, g = plan[0]
        print(json.dumps({"generator": g["api_model"], "system": SYSTEM, "user": r["prompt"][:200],
                          "judge_questions": JUDGE_Q}, indent=2)[:1200])
        print("dry run only; no API calls made.")
        return

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    gen_sem = asyncio.Semaphore(args.concurrency)
    out = open(args.out, "w")

    async with AsyncTypeSafeClient() as tc:
        judge_sem = asyncio.Semaphore(max(2, args.concurrency))

        async def one(row, gen):
            async with gen_sem:
                try:
                    ans = await asyncio.to_thread(generate, gen, row["prompt"])
                except Exception as e:  # noqa: BLE001
                    return {"id": row["id"], "gold_tier": row["gold_tier"], "generator": gen["id"],
                            "error": f"{type(e).__name__}: {e}"}
            j = await judge(tc, judge_sem, row["prompt"], ans)
            return {"id": row["id"], "gold_tier": row["gold_tier"], "prompt_style": row.get("prompt_style"),
                    "category": row.get("category"), "prompt": row["prompt"], "generator": gen["id"],
                    "answer": ans["text"][:4000], "tokens_in": ans["tokens_in"], "tokens_out": ans["tokens_out"],
                    "latency_ms": ans["latency_ms"], "judge": j}

        tasks = [asyncio.create_task(one(r, g)) for r, g in plan]
        n = 0
        for fut in asyncio.as_completed(tasks):
            rec = await fut
            out.write(json.dumps(rec) + "\n")
            out.flush()
            n += 1
            if n % 20 == 0:
                print(f"  {n}/{len(plan)}")
    out.close()
    print(f"wrote {n} cascade records -> {args.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "all-prompts-v2.jsonl"))
    ap.add_argument("--split", default="test")
    ap.add_argument("--slice", default="business", choices=["all", "business", "harness"])
    ap.add_argument("--per-tier", type=int, default=20)
    ap.add_argument("--executable-only", action="store_true", help="keep only prompts that do not assume supplied inputs")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--out", default=os.path.join(HERE, "results", "cascade.jsonl"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
