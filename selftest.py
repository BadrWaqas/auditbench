#!/usr/bin/env python3
"""Self-test: proves the answer keys and the grader are sound WITHOUT calling any model.

  1. Recomputes every answer key with a second, independent float implementation.
  2. Oracle (perfect answers) must score 100; a "say none + copy analyst figure" baseline
     must fail every flawed task; a "right flaw, analyst's number" baseline must get 0 value points.
  3. Grader robustness: prose around JSON, code fences, % signs, label formatting, garbage.
"""
import json
from pathlib import Path

from grader import grade, parse_response

HERE = Path(__file__).resolve().parent
TASKS = json.loads((HERE / "tasks.json").read_text(encoding="utf-8"))["tasks"]
BYID = {t["id"]: t for t in TASKS}
fails = []


def check(name, cond):
    print(("PASS  " if cond else "FAIL  ") + name)
    if not cond:
        fails.append(name)


# ---------- 1. independent recomputation of keys (plain floats, different code path)
def simpson_key(d):
    nA, sA, nB, sB = d["nA"], d["sA"], d["nB"], d["sB"]
    N = float(sum(nA) + sum(nB))
    tot = 0.0
    for i in range(len(nA)):
        tot += (nA[i] + nB[i]) / N * (sB[i] / nB[i] - sA[i] / nA[i])
    return round(tot * 100, 2)


def base_key(d):
    from fractions import Fraction as F
    p, s, sp = F(d["prev"]), F(d["sens"]), F(d["spec"])
    # odds form: posterior odds = prior odds * LR^2
    odds = (p / (1 - p)) * (s / (1 - sp)) ** 2
    return round(float(odds / (1 + odds)) * 100, 2)


def f1_key(d):
    p = d["tp"] / (d["tp"] + d["fp"])
    r = d["tp"] / (d["tp"] + d["fn"])
    return round(2 * p * r / (p + r) * 100, 2)


def bh_key(d):
    ps = sorted(x / 10000 for x in d["p_x10000"])
    m = len(ps)
    thresholds = [(i + 1) * 0.05 / m for i in range(m)]
    best = 0
    for i, (p, th) in enumerate(zip(ps, thresholds), start=1):
        if p <= th + 1e-12:
            best = i
    return best


def tuning_key(d):
    i = max(range(len(d["val"])), key=lambda j: d["val"][j])
    return round(d["test"][i] / 800 * 100, 2)


def preproc_key(d):
    vals = [x for i, x in enumerate(d["income"]) if d["split"][i] == "train" and i not in d["missing"]]
    return round(sum(vals) / len(vals), 2)


def count_key(d):
    return sum(1 for _, day in d["features"] if day <= 14)


def ab_key(d):
    n, cA, cB = d["n"], d["cA"], d["cB"]
    return round((sum(cB) / sum(n) - sum(cA) / sum(n)) * 100, 2)  # equal allocation => overall diff


def censor_key(d):
    import datetime as dt
    a = dt.date.fromisoformat(d["analysis"])
    keep = [r for r in d["rows"] if (dt.date.fromisoformat(r[1]) - a).days + 30 <= 0]
    return round(sum(r[3] for r in keep) / sum(r[2] for r in keep) * 100, 2)


def rtm_key(d):
    ch = [r[3] - r[2] for r in d["rows"] if r[1] == "coached"]
    wl = [r[3] - r[2] for r in d["rows"] if r[1] == "waitlist"]
    return round(sum(ch) / len(ch) - sum(wl) / len(wl), 2)


def group_key(d):
    train_p = {r[1] for r in d["rows"] if r[2] == "train"}
    clean = [r[3] for r in d["rows"] if r[2] == "test" and r[1] not in train_p]
    return round(sum(clean) / len(clean) * 100, 2)


def survivor_key(d):
    return round(sum(r[3] for r in d["rows"]) / len(d["rows"]), 2)


def window_key(d):
    return sum(1 for f in d["features"] if f[2] <= "2026-01-31")  # ISO dates compare as strings


def cv_key(d):
    return None  # control: key is the analyst's figure, checked below


INDEP = {
    "hard_cohort_censoring": censor_key, "hard_regression_to_mean": rtm_key,
    "hard_patient_leakage": group_key, "hard_survivorship": survivor_key,
    "hard_feature_windows": window_key,
    "hard_patient_leakage_xl": group_key, "hard_survivorship_xl": survivor_key,
    "simpson_2_strata": simpson_key, "simpson_4_strata": simpson_key,
    "base_rate_double_positive": base_key, "imbalanced_f1": f1_key,
    "multiple_comparisons_bh": bh_key, "test_set_tuning": tuning_key,
    "preprocessing_leakage": preproc_key, "target_leakage_timing": count_key,
    "control_balanced_ab": ab_key, "control_legit_lagged_features": count_key,
}
for t in TASKS:
    if t["id"] in ("hard_control_cv_tuning", "hard_control_post_treatment"):
        check("hard control {}: key equals the analyst's figure".format(t["id"]), t["key"]["value"] == t["analyst_value"])
        continue
    k2 = INDEP[t["id"]](t["data"])
    check("independent key matches: {} ({} vs {})".format(t["id"], t["key"]["value"], k2),
          abs(k2 - t["key"]["value"]) <= 0.011)

# structural invariants
for t in TASKS:
    d = t["data"]
    if t["id"].startswith("simpson"):
        rA = [s / n for s, n in zip(d["sA"], d["nA"])]
        rB = [s / n for s, n in zip(d["sB"], d["nB"])]
        OA, OB = sum(d["sA"]) / sum(d["nA"]), sum(d["sB"]) / sum(d["nB"])
        check("{}: B wins in every stratum but loses overall".format(t["id"]),
              all(b > a for a, b in zip(rA, rB)) and OA > OB)
    if t["id"] == "multiple_comparisons_bh":
        check("BH count differs from naive and Bonferroni (a model must actually do BH)",
              d["naive"] != t["key"]["value"] and d["bonferroni"] != t["key"]["value"])
    if t["id"] == "hard_patient_leakage":
        tp = {r[1] for r in d["rows"] if r[2] == "train"}
        check("hard_patient_leakage: some test patients also appear in train", any(r[2] == "test" and r[1] in tp for r in d["rows"]))
    if t["id"] == "hard_cohort_censoring":
        check("hard_cohort_censoring: exactly 8 mature cohorts and a partially-matured 9th", d["n_mature"] == 8 and d["rows"][8][3] > 0)
    if t["id"] == "hard_control_post_treatment":
        r = {(x[0], x[1]): (x[2], x[3]) for x in d["rows"]}
        rate = lambda k: r[k][0] / r[k][1]
        pooled = (r[("yes", "drug")][0] + r[("no", "drug")][0]) / (r[("yes", "drug")][1] + r[("no", "drug")][1]) - \
                 (r[("yes", "placebo")][0] + r[("no", "placebo")][0]) / (r[("yes", "placebo")][1] + r[("no", "placebo")][1])
        check("post-treatment control: drug loses within both strata but wins pooled, and key = pooled diff",
              rate(("yes", "drug")) < rate(("yes", "placebo")) and rate(("no", "drug")) < rate(("no", "placebo"))
              and abs(round(pooled * 100, 2) - t["key"]["value"]) <= 0.011)
    if t["id"] == "test_set_tuning":
        check("best-by-test config differs from best-by-validation", d["best_val"] != d["best_test"])
    check("prompt contains no answer key leak: {}".format(t["id"]),
          str(t["key"]["value"]) not in t["prompt"].split("=== WHAT corrected_value MEANS ===")[1]
          or t["is_control"])

# ---------- 2. oracle and baselines
def reply(flaw, value):
    return 'Working...\n```json\n{{"flaw": "{}", "corrected_value": {}, "reasoning": "x"}}\n```'.format(flaw, value)


oracle = [grade(t, reply(t["key"]["flaw"], t["key"]["value"])) for t in TASKS]
check("oracle scores 100/100 on every task", all(g["score"] == 100 for g in oracle))

always_none = [grade(t, reply("none", t["analyst_value"])) for t in TASKS]
flawed_g = [g for g, t in zip(always_none, TASKS) if not t["is_control"]]
ctrl_g = [g for g, t in zip(always_none, TASKS) if t["is_control"]]
check("'always none, copy analyst figure' fails every flawed task", not any(g["passed"] for g in flawed_g))
check("'always none, copy analyst figure' passes every control", all(g["passed"] for g in ctrl_g))

flaw_only = [grade(t, reply(t["key"]["flaw"], t["analyst_value"])) for t in TASKS]
check("right label + analyst's number gets 0 value points on flawed tasks",
      not any(g["value_ok"] for g, t in zip(flaw_only, TASKS) if not t["is_control"]))
check("right label + analyst's number scores exactly 50 on flawed tasks",
      all(g["score"] == 50 for g, t in zip(flaw_only, TASKS) if not t["is_control"]))

false_flag = grade(BYID["control_balanced_ab"], reply("simpsons_paradox", BYID["control_balanced_ab"]["key"]["value"]))
check("false alarm on a sound analysis is flagged and not a pass",
      false_flag["false_flag"] and not false_flag["passed"])

# ---------- 3. parser robustness
t = BYID["simpson_2_strata"]
k = t["key"]["value"]
cases = {
    "prose + fenced json": "I think...\n```json\n" + json.dumps({"flaw": "simpsons_paradox", "corrected_value": k, "reasoning": "r"}) + "\n```",
    "flaw with spaces/caps": json.dumps({"flaw": "Simpsons Paradox", "corrected_value": k}),
    "value as string with %": json.dumps({"flaw": "simpsons_paradox", "corrected_value": "{}%".format(k)}),
    "two objects: last wins": '{"flaw": "none", "corrected_value": 1} then final: ' + json.dumps({"flaw": "simpsons_paradox", "corrected_value": k}),
    "braces in reasoning text": 'set {a,b} ... ' + json.dumps({"flaw": "simpsons_paradox", "corrected_value": k, "reasoning": "uses {x}"}),
}
for name, txt in cases.items():
    check("parser accepts: " + name, grade(t, txt)["passed"])
broken = '{"flaw": "simpsons_paradox", "corrected_value": %s, "reasoning": Missing opening quote here."}' % k
check("fallback parser: invalid JSON with unambiguous fields is still graded (no false fail)", grade(t, broken)["passed"])
check("fallback parser: prose mentioning a label without the JSON key is NOT graded",
      not grade(t, "I think it is simpsons_paradox and the value is %s" % k)["parse_ok"])
check("garbage scores 0", grade(t, "no json here")["score"] == 0)
check("unknown label is not accepted", not grade(t, json.dumps({"flaw": "bad_stuff", "corrected_value": k}))["flaw_ok"])
check("value outside tolerance rejected", not grade(t, json.dumps({"flaw": "simpsons_paradox", "corrected_value": k + 0.5}))["value_ok"])
check("value inside tolerance accepted", grade(t, json.dumps({"flaw": "simpsons_paradox", "corrected_value": k + 0.01}))["value_ok"])
c = BYID["multiple_comparisons_bh"]
check("count tasks need exact value", not grade(c, json.dumps({"flaw": "multiple_comparisons", "corrected_value": c["key"]["value"] + 1}))["value_ok"])

print("\n{} checks failed".format(len(fails)) if fails else "\nAll checks passed")
raise SystemExit(1 if fails else 0)
