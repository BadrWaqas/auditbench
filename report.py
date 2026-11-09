#!/usr/bin/env python3
"""Grade every results/*.jsonl and write RESULTS.md + results_summary.json (also printed).

Scores are reported per tier (core = 10 textbook tasks, hard = 6 realistic tasks). A "run" is one sample of
every task in a tier; the tier score is the mean over complete runs (+/- population sd across runs).
Also reported: flaw-spotting vs. number-computing accuracy and false alarms on sound analyses (controls).
"""
import json
import statistics as st
from pathlib import Path

from grader import grade

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))["tasks"]
BYID = {t["id"]: t for t in TASKS}
TIERS = ["core", "hard"]


API_ERRORS = {}


def load(path):
    recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    # an API/transport error is not a model answer: it is counted separately and never graded
    API_ERRORS[path.stem] = sum(1 for r in recs if r.get("error"))
    recs = [r for r in recs if not r.get("error")]
    for r in recs:
        r["g"] = grade(BYID[r["task_id"]], r["response"])
    return recs


def pct(x, n):
    return "{:.0f}%".format(100 * x / n) if n else "-"


def tier_score(recs, tier):
    ids = [t["id"] for t in TASKS if t.get("tier", "core") == tier]
    per_run = []
    for k in sorted({r["sample"] for r in recs}):
        rr = {r["task_id"]: r for r in recs if r["sample"] == k and r["task_id"] in ids}
        if len(rr) == len(ids):
            per_run.append(sum(r["g"]["score"] for r in rr.values()) / len(ids))
    if not per_run:
        return None, None, 0
    return st.mean(per_run), (st.pstdev(per_run) if len(per_run) > 1 else 0.0), len(per_run)


def summarize(label, recs):
    flawed = [r for r in recs if not BYID[r["task_id"]]["is_control"]]
    ctrl = [r for r in recs if BYID[r["task_id"]]["is_control"]]
    s = {"label": label, "model": recs[0].get("model", label), "mode": recs[0].get("mode", "?"), "n": len(recs),
         "errors": API_ERRORS.get(label, 0),
         "pass": pct(sum(r["g"]["passed"] for r in recs), len(recs)),
         "flaw_acc": pct(sum(r["g"]["flaw_ok"] for r in flawed), len(flawed)),
         "value_acc": pct(sum(r["g"]["value_ok"] for r in flawed), len(flawed)),
         "false_flag": pct(sum(r["g"]["false_flag"] for r in ctrl), len(ctrl)),
         "missed": pct(sum(r["g"]["missed_flaw"] for r in flawed), len(flawed))}
    for tier in TIERS:
        m, sd, n = tier_score(recs, tier)
        s[tier] = {"mean": m, "sd": sd, "runs": n}
        tr = [r for r in recs if BYID[r["task_id"]].get("tier", "core") == tier]
        s[tier]["pass"] = pct(sum(r["g"]["passed"] for r in tr), len(tr))
    return s


def fmt(t):
    return "-" if t["mean"] is None else "{:.1f} ± {:.1f} ({} run{})".format(t["mean"], t["sd"], t["runs"], "" if t["runs"] == 1 else "s")


def main():
    files = sorted((HERE / "results").glob("*.jsonl"))
    if not files:
        print("No results yet. Run run_eval.py first.")
        return
    data = {f.stem: load(f) for f in files}
    sums = [summarize(k, v) for k, v in data.items()]
    sums.sort(key=lambda s: (-(s["hard"]["mean"] if s["hard"]["mean"] is not None else -1), -(s["core"]["mean"] or 0)))
    labels = [s["label"] for s in sums]

    L = ["# AuditBench results\n",
         "Per task: 50 pts for the correct flaw label + 50 pts for the corrected number. Tier score = mean over "
         "complete runs of that tier (± sd across runs). Percent columns pool every graded answer.\n",
         "| Model | How run | Core tier /100 ({} tasks) | Hard tier /100 ({} tasks) | Answers fully correct | ".format(
             sum(1 for t in TASKS if t.get("tier", "core") == "core"), sum(1 for t in TASKS if t.get("tier") == "hard")) +
         "Flaw label right (flawed tasks) | Number right (flawed tasks) | Said 'none' on a flawed task | "
         "False alarm on sound analyses | API errors |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for s in sums:
        L.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            s["model"], s["mode"], fmt(s["core"]), fmt(s["hard"]), s["pass"], s["flaw_acc"], s["value_acc"],
            s["missed"], s["false_flag"], s["errors"]))
    L.append("")
    L.append("## Pass rate per task (samples fully correct / samples run)\n")
    L.append("| Tier | Task | Key | " + " | ".join(labels) + " |")
    L.append("|---|---|---|" + "---|" * len(labels))
    for t in TASKS:
        cells = []
        for lab in labels:
            rr = [r for r in data[lab] if r["task_id"] == t["id"]]
            cells.append("{}/{}".format(sum(r["g"]["passed"] for r in rr), len(rr)) if rr else "-")
        L.append("| {} | {} | {} = {} | {} |".format(t.get("tier", "core"), t["id"], t["key"]["flaw"], t["key"]["value"],
                                                  " | ".join(cells)))
    L.append("")
    L.append("## Reasoning effort (mean completion tokens per answer, where the API reported usage)\n")
    L.append("| Task | " + " | ".join(labels) + " |")
    L.append("|---|" + "---|" * len(labels))
    for t in TASKS:
        cells = []
        for lab in labels:
            toks = [r["usage"]["completion_tokens"] for r in data[lab] if r["task_id"] == t["id"]
                    and isinstance(r.get("usage"), dict) and r["usage"].get("completion_tokens")]
            cells.append("{:,.0f}".format(sum(toks) / len(toks)) if toks else "-")
        if any(c != "-" for c in cells):
            L.append("| {} | {} |".format(t["id"], " | ".join(cells)))
    L.append("")
    L.append("## Every wrong answer\n")
    for lab in labels:
        wrong = [r for r in data[lab] if not r["g"]["passed"]]
        L.append("**{}**: {} wrong of {}".format(lab, len(wrong), len(data[lab])))
        for r in wrong:
            t = BYID[r["task_id"]]
            why = "no parseable JSON" if not r["g"]["parse_ok"] else (
                "wrong label and number" if not (r["g"]["flaw_ok"] or r["g"]["value_ok"]) else
                "right label, wrong number" if r["g"]["flaw_ok"] else "wrong label, right number")
            extra = " [{}]".format(r["error"][:80]) if r.get("error") else (
                " [finish_reason={}]".format(r["finish_reason"]) if r.get("finish_reason") == "length" else "")
            L.append("- {} (sample {}): said {} / {}; key {} / {}. {}{}".format(
                r["task_id"], r["sample"], r["g"]["flaw_pred"], r["g"]["value_pred"], t["key"]["flaw"],
                t["key"]["value"], why, extra))
        L.append("")
    text = "\n".join(L)
    (HERE / "RESULTS.md").write_text(text, encoding="utf-8")
    per_task = {lab: {t["id"]: [r["g"] for r in data[lab] if r["task_id"] == t["id"]] for t in TASKS} for lab in labels}
    (HERE / "results_summary.json").write_text(json.dumps({"models": sums, "per_task": per_task}, indent=1),
                                               encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
