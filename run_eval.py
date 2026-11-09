#!/usr/bin/env python3
"""Run AuditBench against a model.

Standard library only. Three modes:

  1) API run via OpenRouter (reproducible):
       export OPENROUTER_API_KEY=...        (never put the key in a file you share)
       python run_eval.py --model <openrouter-model-id> --label <name> --samples 3

  2) Export prompts to paste into any chat app by hand:
       python run_eval.py --export-manual
     then save each reply as manual/<label>/<task_id>__<n>.txt  (n = 1..samples) and run:
       python run_eval.py --import-manual manual/<label> --label <label>

  3) Grade/aggregate: python report.py
Raw model replies are stored in results/<label>.jsonl; grading happens in report.py, so a
fixed grader can be re-applied without re-running any model.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))["tasks"]
RESULTS = HERE / "results"


def load_dotenv():
    """Read KEY=VALUE lines from .env next to this script (if present) without overriding real env vars."""
    f = HERE / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if v.strip() and not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")


def call_openrouter(base_url, key, model, prompt, temperature, max_tokens, retries=6):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=body,
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                 "User-Agent": "auditbench/1.0"},
    )
    delay = 4
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                data = json.loads(r.read())
            if "choices" in data and data["choices"]:
                ch = data["choices"][0]
                content = (ch.get("message") or {}).get("content") or ""
                meta = {"finish_reason": ch.get("finish_reason"), "usage": data.get("usage"),
                        "served_model": data.get("model"), "provider": data.get("provider")}
                if not content.strip() and ch.get("finish_reason") != "length":
                    raise RuntimeError("empty reply (finish_reason={})".format(ch.get("finish_reason")))
                return content, meta
            err = data.get("error", data)
            raise RuntimeError(str(err)[:300])
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:300]
            if e.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise RuntimeError("HTTP {}: {}".format(e.code, msg))
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
            if attempt < retries - 1:
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
            raise RuntimeError(str(e))


def load_done(path):
    done = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                if not r.get("error"):  # failed API calls are retried on the next run
                    done.add((r["task_id"], r["sample"]))
    return done


def append(path, rec):
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", help="OpenRouter model id, e.g. a model from https://openrouter.ai/models?q=free")
    ap.add_argument("--label", help="name used for the results file (default: model id)")
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--base-url", default="https://openrouter.ai/api/v1")
    ap.add_argument("--export-manual", action="store_true")
    ap.add_argument("--import-manual", metavar="DIR")
    ap.add_argument("--tasks", help="comma-separated task ids to run (default: all)")
    a = ap.parse_args()

    tasks = TASKS
    if a.tasks:
        want = set(a.tasks.split(","))
        tasks = [t for t in TASKS if t["id"] in want]

    if a.export_manual:
        out = HERE / "manual" / "prompts"
        out.mkdir(parents=True, exist_ok=True)
        for t in tasks:
            (out / (t["id"] + ".txt")).write_text(t["prompt"], encoding="utf-8")
        print("Wrote {} prompts to {}".format(len(tasks), out))
        print("Paste each into a NEW chat (no tools / no code execution), save the full reply as "
              "manual/<label>/<task_id>__<n>.txt, then use --import-manual.")
        return

    RESULTS.mkdir(exist_ok=True)

    if a.import_manual:
        if not a.label:
            sys.exit("--label is required with --import-manual")
        src = Path(a.import_manual)
        path = RESULTS / (a.label + ".jsonl")
        done = load_done(path)
        n = 0
        for t in tasks:
            for k in range(1, a.samples + 1):
                f = src / "{}__{}.txt".format(t["id"], k)
                if f.exists() and f.read_text(encoding="utf-8").strip() and (t["id"], k) not in done:
                    append(path, {"model": a.label, "mode": "manual_chat", "task_id": t["id"],
                                  "sample": k, "response": f.read_text(encoding="utf-8")})
                    n += 1
        print("Imported {} replies into {}".format(n, path))
        return

    if not a.model:
        sys.exit("give --model (API run), --export-manual, or --import-manual")
    load_dotenv()
    local = "localhost" in a.base_url or "127.0.0.1" in a.base_url
    key = os.environ.get("OPENROUTER_API_KEY") or ("local" if local else None)
    if not key:
        sys.exit("Set OPENROUTER_API_KEY (environment variable or .env file). A free OpenRouter key works for free models.")
    label = (a.label or a.model).replace("/", "_").replace(":", "_")
    path = RESULTS / (label + ".jsonl")
    done = load_done(path)
    total = len(tasks) * a.samples
    i = 0
    for k in range(1, a.samples + 1):
        for t in tasks:
            i += 1
            if (t["id"], k) in done:
                continue
            try:
                resp, meta = call_openrouter(a.base_url, key, a.model, t["prompt"], a.temperature, a.max_tokens)
                err = None
            except RuntimeError as e:
                resp, err, meta = "", str(e), {}
            rec = {"model": a.model, "mode": "local" if local else "api", "base_url": a.base_url,
                   "temperature": a.temperature, "max_tokens": a.max_tokens,
                   "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "task_id": t["id"], "sample": k, "response": resp}
            rec.update(meta)
            if err:
                rec["error"] = err
            append(path, rec)
            print("[{}/{}] {} sample {} {}".format(i, total, t["id"], k, "ERROR " + err if err else "ok"), flush=True)
    print("Done. Raw replies in", path, "-> now run: python report.py")


if __name__ == "__main__":
    main()
