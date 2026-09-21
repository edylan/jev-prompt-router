#!/usr/bin/env python3
"""Live dashboard server with policy toggles and a start/stop run control.

    python3 eval/dashboard_server.py --results eval/results/dev.jsonl --open
    python3 eval/dashboard_server.py --results eval/results/sim.jsonl --open       # rehearsal
    python3 eval/dashboard_server.py --results eval/results/dev.jsonl --disable-run  # view only

GET  /                 the dashboard
GET  /api/state        rows + results + summary + policy + run status
POST /api/policy       partial policy update {allow_cn_origin, escalate_below_confidence, ...}
POST /api/policy/reset reload policy.json
POST /api/run          start a classification run {mode, split, slice, limit, concurrency, order, reset}
POST /api/stop         stop the running job
GET  /api/log          tail of the run log
"""
import argparse, hashlib, json, os, subprocess, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
from routing import load_registry_doc, load_policy, load_jsonl, summarize, route_row, effective_tier  # noqa: E402

LOCK = threading.Lock()
STATE = {}
ALLOWED_POLICY = {"allow_cn_origin", "high_sensitivity_requires_allowlist", "enforce_residency",
                  "escalate_below_confidence", "baseline_model_id", "allowed_residencies"}


def policy_sig(policy):
    return hashlib.sha1(json.dumps(policy, sort_keys=True).encode()).hexdigest()[:10]


def load_rows(path):
    rows = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            r = json.loads(line)
            rows.append({k: r.get(k) for k in ("id", "split", "prompt_style", "category", "business_function", "harness", "gold_tier", "prompt", "governance")})
    return rows


def read_results(path):
    return {r["id"]: r for r in load_jsonl(path) if "id" in r}


def log_tail(n=60):
    p = STATE["log"]
    if not os.path.exists(p):
        return ""
    with open(p, errors="replace") as f:
        return "".join(f.readlines()[-n:])


def run_status():
    proc = STATE.get("proc")
    running = proc is not None and proc.poll() is None
    started = STATE.get("started_at")
    return {
        "running": running, "mode": STATE.get("mode"), "opts": STATE.get("run_opts"),
        "pid": proc.pid if proc else None,
        "elapsed_s": round(time.time() - started, 1) if (running and started) else STATE.get("last_elapsed"),
        "returncode": proc.poll() if proc else STATE.get("last_returncode"),
    }


def interleave(rows):
    """Same deterministic order as jev_runner --order interleave (round-robin by tier)."""
    buckets = {t: [r for r in rows if r["gold_tier"] == t] for t in ("T0", "T1", "T2", "T3")}
    out = []
    while any(buckets.values()):
        for t in ("T0", "T1", "T2", "T3"):
            if buckets[t]:
                out.append(buckets[t].pop(0))
    return out


def select_run_rows(rows, split, slice_, limit):
    """Mirror how the runner selects rows, so the progress bar matches the run."""
    r = [x for x in rows if not slice_ or x.get("prompt_style") == slice_]
    if split and split != "all":
        r = [x for x in r if x["split"] == split]
    r = interleave(r)
    return r[:limit] if limit else r


def build_cmd(o):
    results = STATE["results"]
    if o.get("reset"):
        os.makedirs(os.path.dirname(results), exist_ok=True)
        open(results, "w").close()
    if o["mode"] == "sim":
        cmd = [sys.executable, os.path.join(HERE, "simulate_results.py"), "--data", STATE["data"],
               "--out", results, "--split", o["split"], "--delay", "0.05"]
        if o.get("slice"):
            cmd += ["--slice", o["slice"]]
    else:
        cmd = [sys.executable, os.path.join(HERE, "jev_runner.py"), "--data", STATE["data"],
               "--out", results, "--split", o["split"], "--concurrency", str(o["concurrency"]), "--order", o["order"]]
        if o.get("slice"):
            cmd += ["--slice", o["slice"]]
        if o.get("ambient"):
            cmd += ["--ambient"]
    if o.get("limit"):
        cmd += ["--limit", str(o["limit"])]
    return cmd


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")
        except Exception:  # noqa: BLE001
            return {}

    # ---------------- GET
    def do_GET(self):
        if self.path.startswith("/api/state"):
            with LOCK:
                policy, models = STATE["policy"], STATE["models"]
                results = read_results(STATE["results"])
                active = STATE.get("active_ids")
                rows = [r for r in STATE["rows"] if r["id"] in active] if active else STATE["rows"]
                by_id = {r["id"]: r for r in rows}
                light = {}
                for k, rec in results.items():
                    lite = {kk: vv for kk, vv in rec.items() if kk != "prompt"}
                    j = rec.get("jev") or {}
                    row = by_id.get(k)
                    tier = effective_tier(rec)
                    if row and tier in ("T0", "T1", "T2", "T3"):
                        lite["route"] = route_row(row, tier, j.get("confidence"), policy, models)
                        lite["jev"] = {**j, "choice": tier}
                        lite["correct"] = tier == row["gold_tier"]
                    light[k] = lite
                summary = summarize(rows, results, policy, models)
                self._send(200, json.dumps({
                    "rows": rows, "results": light, "summary": summary,
                    "policy": policy,
                    "models": [{"id": m["id"], "display": m["display"], "capability_tier": m["capability_tier"], "cost_band": m["cost_band"], "origin": m["origin"], "vendor": m["vendor"], "serving_locus": m["serving_locus"], "input_usd_per_mtok": m["input_usd_per_mtok"], "output_usd_per_mtok": m["output_usd_per_mtok"]} for m in models],
                    "pricing": {"source": STATE["registry_doc"].get("pricing_source"), "fetched_at": STATE["registry_doc"].get("pricing_fetched_at"), "note": STATE["registry_doc"].get("note")},
                    "run": run_status(),
                    "log": log_tail(),
                    "meta": {"generated_at": STATE["generated_at"], "results_path": STATE["results"],
                             "simulated": STATE["simulated"], "policy_sig": policy_sig(policy),
                             "can_run": STATE["can_run"]},
                }, default=str))
        elif self.path.startswith("/api/log"):
            self._send(200, json.dumps({"log": log_tail(200)}))
        elif self.path.startswith("/health"):
            self._send(200, json.dumps({"ok": True}))
        else:
            with open(os.path.join(HERE, "dashboard.html"), "rb") as f:
                self._send(200, f.read(), "text/html; charset=utf-8")

    # ---------------- POST
    def do_POST(self):
        body = self._body()
        if self.path.startswith("/api/policy/reset"):
            with LOCK:
                STATE["policy"] = load_policy(STATE["policy_path"])
                self._send(200, json.dumps({"policy": STATE["policy"]}))
            return
        if self.path.startswith("/api/policy"):
            with LOCK:
                for k, v in body.items():
                    if k in ALLOWED_POLICY:
                        STATE["policy"][k] = v
                self._send(200, json.dumps({"policy": STATE["policy"], "policy_sig": policy_sig(STATE["policy"])}))
            return
        if self.path.startswith("/api/run"):
            if not STATE["can_run"]:
                self._send(403, json.dumps({"error": "run disabled (--disable-run)"}))
                return
            with LOCK:
                proc = STATE.get("proc")
                if proc is not None and proc.poll() is None:
                    self._send(409, json.dumps({"error": "a run is already in progress"}))
                    return
                o = {
                    "mode": body.get("mode", "sim"), "split": body.get("split", "development"),
                    "slice": body.get("slice") or None, "limit": int(body.get("limit") or 0),
                    "concurrency": max(1, min(32, int(body.get("concurrency") or 6))),
                    "order": body.get("order", "interleave"), "ambient": bool(body.get("ambient")),
                    "reset": bool(body.get("reset", True)),
                }
                os.makedirs(os.path.dirname(STATE["results"]), exist_ok=True)
                STATE["active_ids"] = {r["id"] for r in select_run_rows(STATE["rows"], o["split"], o["slice"], o["limit"])}
                cmd = build_cmd(o)
                STATE["log"] = os.path.join(HERE, "results", "run.log")
                logf = open(STATE["log"], "a")
                logf.write(f"\n=== {time.strftime('%Y-%m-%d %H:%M:%S')} {' '.join(cmd)} ===\n")
                logf.flush()
                STATE["proc"] = subprocess.Popen(cmd, stdout=logf, stderr=subprocess.STDOUT, cwd=ROOT)
                STATE["mode"] = o["mode"]
                STATE["simulated"] = o["mode"] == "sim"
                STATE["run_opts"] = o
                STATE["started_at"] = time.time()
                STATE["last_returncode"] = None
                STATE["last_elapsed"] = None
                self._send(200, json.dumps({"started": True, "run": run_status(), "cmd": cmd}))
            return
        if self.path.startswith("/api/stop"):
            with LOCK:
                proc = STATE.get("proc")
                if proc is not None and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                    STATE["last_returncode"] = proc.returncode
                    STATE["last_elapsed"] = round(time.time() - STATE["started_at"], 1)
                    self._send(200, json.dumps({"stopped": True, "run": run_status()}))
                else:
                    self._send(200, json.dumps({"stopped": False, "run": run_status()}))
            return
        self._send(404, json.dumps({"error": "not found"}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=os.path.join(HERE, "..", "datasets", "v2", "business-prompts-v2.jsonl"))
    ap.add_argument("--results", default=os.path.join(HERE, "results", "sim.jsonl"))
    ap.add_argument("--registry", default=None)
    ap.add_argument("--policy", default=None)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8787)
    ap.add_argument("--open", action="store_true")
    ap.add_argument("--disable-run", action="store_true", help="view-only; hide/deny start")
    a = ap.parse_args()

    policy_path = a.policy or os.path.join(HERE, "policy.json")
    registry_doc = load_registry_doc(a.registry)
    STATE.update({
        "rows": load_rows(a.data), "data": a.data, "results": a.results,
        "policy": load_policy(policy_path), "policy_path": policy_path,
        "models": registry_doc["models"], "registry_doc": registry_doc, "generated_at": "2026-09-21",
        "simulated": "sim" in os.path.basename(a.results),
        "proc": None, "mode": None, "run_opts": None, "started_at": None,
        "active_ids": None,
        "last_returncode": None, "last_elapsed": None, "can_run": not a.disable_run,
        "log": os.path.join(HERE, "results", "run.log"),
    })
    url = f"http://{a.host}:{a.port}/"
    print(f"dashboard: {url}\n  data:    {a.data}\n  results: {a.results} ({'SIMULATED' if STATE['simulated'] else 'live'})\n  run:     {'enabled' if STATE['can_run'] else 'disabled'}")
    if a.open:
        import webbrowser
        webbrowser.open(url)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
