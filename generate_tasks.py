#!/usr/bin/env python3
"""Generate the AuditBench tasks (tasks.json).

Every answer key is computed here from the same numbers that appear in the
prompt, using exact fractions, so a key cannot disagree with its own table.
Run:  python generate_tasks.py      (deterministic, SEED below)
"""
import json
import random
from fractions import Fraction as F
from pathlib import Path

import hard_tier

SEED = 20261108

FLAWS = [
    "simpsons_paradox",
    "preprocessing_leakage",
    "target_leakage",
    "imbalanced_accuracy",
    "base_rate_fallacy",
    "test_set_tuning",
    "multiple_comparisons",
    "none",
]

PREAMBLE = """You are a senior data scientist reviewing a colleague's analysis.
Read the scenario below. Decide whether the analysis contains a methodological flaw, and compute the corrected number.

Rules:
- You have no tools and cannot run code. Work the arithmetic out yourself.
- "flaw" must be exactly one of: {flaws}
- Use "none" if the analysis is sound. In that case "corrected_value" is the analyst's reported figure, unchanged.
- "corrected_value" is a single number (no units, no % sign), defined at the end of the scenario.
- Finish your reply with ONE JSON object and nothing after it, in exactly this form:
{{"flaw": "<one label>", "corrected_value": <number>, "reasoning": "<one or two sentences>"}}
""".format(flaws=", ".join(FLAWS))


def r2(x):
    return round(float(x), 2)


def csv(header, rows):
    return "\n".join([",".join(header)] + [",".join(str(c) for c in r) for r in rows])


def build_prompt(scenario, question, analyst_value):
    return (
        PREAMBLE
        + "\n=== SCENARIO ===\n"
        + scenario.strip()
        + "\n\n=== WHAT corrected_value MEANS ===\n"
        + question.strip()
        + "\nThe analyst's reported figure, in the same units, is: {}\n".format(analyst_value)
    )


# ---------------------------------------------------------------- Simpson
def make_simpson(rng, strata, labels, scenario_intro, rate_word, unit_word, claim_name, ids, tot_range):
    k = len(strata)
    for _ in range(100000):
        base = sorted([rng.uniform(0.35, 0.92) for _ in range(k)], reverse=True)
        wA = sorted([rng.uniform(0.05, 1.0) for _ in range(k)], reverse=True)
        wB = sorted([rng.uniform(0.05, 1.0) for _ in range(k)])
        totA = rng.randint(*tot_range)
        totB = rng.randint(*tot_range)
        nA = [max(25, round(totA * w / sum(wA))) for w in wA]
        nB = [max(25, round(totB * w / sum(wB))) for w in wB]
        gain = [rng.uniform(0.02, 0.07) for _ in range(k)]
        sA = [round(n * b) for n, b in zip(nA, base)]
        sB = [round(n * min(0.99, b + g)) for n, b, g in zip(nB, base, gain)]
        rA = [F(s, n) for s, n in zip(sA, nA)]
        rB = [F(s, n) for s, n in zip(sB, nB)]
        if not all(b > a for a, b in zip(rA, rB)):
            continue
        OA, OB = F(sum(sA), sum(nA)), F(sum(sB), sum(nB))
        if not OA > OB:
            continue
        N = sum(nA) + sum(nB)
        std = sum(F(a + b, N) * (rb - ra) for a, b, ra, rb in zip(nA, nB, rA, rB)) * 100
        naive = (OB - OA) * 100
        if std < 1 or abs(naive) < 1:
            continue
        rows = []
        for i, s in enumerate(strata):
            rows.append((s, ids[0], sA[i], nA[i]))
            rows.append((s, ids[1], sB[i], nB[i]))
        table = csv([labels[0], "group", "successes", unit_word], rows)
        analyst = r2(naive)
        claim = (
            "Pooled over all strata: {a} {SA}/{NA} = {ra:.1f}%, {b} {SB}/{NB} = {rb:.1f}%. "
            "{b} minus {a} = {d:+.2f} percentage points, so {a} is better. Recommendation: adopt {a}."
        ).format(
            a=ids[0], b=ids[1], SA=sum(sA), NA=sum(nA), SB=sum(sB), NB=sum(nB),
            ra=float(OA) * 100, rb=float(OB) * 100, d=analyst,
        )
        scenario = scenario_intro + "\n\n" + table + "\n\nAnalyst's write-up:\n" + claim
        question = (
            "The standardized difference ({b} minus {a}) in {rw}, in percentage points: compute each stratum's "
            "rate difference ({b} rate minus {a} rate) and weight it by that stratum's share of ALL {uw} "
            "(both groups combined). Round to 2 decimals."
        ).format(a=ids[0], b=ids[1], rw=rate_word, uw=unit_word)
        return scenario, question, analyst, r2(std), {"strata": strata, "nA": nA, "sA": sA, "nB": nB, "sB": sB}
    raise RuntimeError("no simpson instance found")


# ---------------------------------------------------------------- Base rate
def make_base_rate(rng):
    prev = rng.choice([F(4, 1000), F(8, 1000), F(12, 1000), F(20, 1000)])
    sens = rng.choice([F(88, 100), F(92, 100), F(95, 100), F(97, 100)])
    spec = rng.choice([F(90, 100), F(93, 100), F(96, 100)])
    num = prev * sens * sens
    den = num + (1 - prev) * (1 - spec) * (1 - spec)
    ppv2 = num / den * 100
    analyst = r2((1 - (1 - spec) ** 2) * 100)
    scenario = (
        "A clinic screens for a rare condition. Known test properties: sensitivity {s}%, specificity {sp}%. "
        "Prevalence in the screened population is {p}%. A patient from this population is tested twice with two "
        "independent repeat tests (errors independent given true status) and is positive both times.\n\n"
        "Analyst's write-up:\nThe chance a healthy person tests positive twice is only (1 - {spf})^2, so a patient with "
        "two positive results has a {a}% probability of having the condition. We can tell patients they almost "
        "certainly have it."
    ).format(s=float(sens * 100), sp=float(spec * 100), p=float(prev * 100), spf=float(spec), a=analyst)
    question = (
        "The true probability (in percent) that the patient has the condition given both tests were positive. "
        "Round to 2 decimals."
    )
    return scenario, question, analyst, r2(ppv2), {"prev": str(prev), "sens": str(sens), "spec": str(spec)}


# ---------------------------------------------------------------- Imbalanced accuracy
def make_imbalanced(rng):
    for _ in range(10000):
        N = rng.choice([4000, 5000, 8000])
        pos = rng.randint(int(N * 0.018), int(N * 0.03))
        tp = round(pos * rng.uniform(0.25, 0.45))
        fn = pos - tp
        fp = rng.randint(8, 45)
        tn = N - pos - fp
        acc = F(tp + tn, N)
        base = F(N - pos, N)
        if acc < F(96, 100) or acc - base > F(3, 100):
            continue
        f1 = F(2 * tp, 2 * tp + fp + fn) * 100
        analyst = r2(acc * 100)
        scenario = (
            "A hospital builds a model to flag patients who will develop sepsis. On a held-out set of {N} patients "
            "the confusion matrix (positive = sepsis) is:\n\n"
            "TP={tp}, FP={fp}, FN={fn}, TN={tn}\n\n"
            "Analyst's write-up:\nAccuracy is {a}%, which is excellent. The model is ready for deployment."
        ).format(N=N, tp=tp, fp=fp, fn=fn, tn=tn, a=analyst)
        question = "The F1 score of the positive (sepsis) class, in percent. Round to 2 decimals."
        return scenario, question, analyst, r2(f1), {"tp": tp, "fp": fp, "fn": fn, "tn": tn}
    raise RuntimeError("no imbalanced instance")


# ---------------------------------------------------------------- Multiple comparisons (BH)
METRICS = [
    "click_through_rate", "add_to_cart_rate", "checkout_rate", "revenue_per_visitor", "bounce_rate",
    "session_length", "pages_per_session", "return_visit_rate", "email_signup_rate", "search_usage_rate",
    "wishlist_adds", "coupon_use_rate", "app_installs", "cart_abandonment", "review_submissions",
    "support_contacts", "share_clicks", "scroll_depth", "video_plays", "newsletter_opens",
]


def bh_count(ps, q=F(5, 100)):
    srt = sorted(ps)
    m = len(srt)
    k = 0
    for i, p in enumerate(srt, start=1):
        if p <= F(i, m) * q:
            k = i
    return k


def make_multiple(rng):
    for _ in range(10000):
        pv = (
            [rng.randint(4, 20) for _ in range(2)]        # 0.0004 - 0.0020
            + [rng.randint(45, 72)]                      # 0.0045 - 0.0072
            + [rng.randint(150, 450) for _ in range(2)]  # 0.015 - 0.045
            + [rng.randint(700, 9500) for _ in range(15)]
        )
        rng.shuffle(pv)
        ps = [F(x, 10000) for x in pv]
        naive = sum(1 for p in ps if p < F(5, 100))
        bonf = sum(1 for p in ps if p * len(ps) < F(5, 100))
        bh = bh_count(ps)
        if bh >= 1 and bh < naive and bh != bonf and len(set(pv)) == len(pv):
            rows = [(m, "{:.4f}".format(x / 10000)) for m, x in zip(METRICS, pv)]
            table = csv(["metric", "p_value"], rows)
            scenario = (
                "An e-commerce team ran one A/B test of a new homepage and tested {n} metrics (all {n} p-values are listed).\n\n"
                "{t}\n\nAnalyst's write-up:\n{k} metrics have p < 0.05, so the new homepage significantly improves "
                "{k} metrics. Ship it and report all {k} wins."
            ).format(n=len(ps), t=table, k=naive)
            question = (
                "The number of the {n} metrics that remain significant after applying the Benjamini-Hochberg "
                "procedure at a false discovery rate of 5% (step-up: find the largest rank k with p_(k) <= k/{n} x 0.05, "
                "and reject the k smallest p-values)."
            ).format(n=len(ps))
            return scenario, question, naive, bh, {"p_x10000": pv, "naive": naive, "bonferroni": bonf}
    raise RuntimeError("no multiple-comparisons instance")


# ---------------------------------------------------------------- Test set tuning
def make_tuning(rng):
    names = [
        "lr0.30_depth3", "lr0.30_depth6", "lr0.10_depth3", "lr0.10_depth6", "lr0.10_depth9", "lr0.05_depth3",
        "lr0.05_depth6", "lr0.05_depth9", "lr0.01_depth3", "lr0.01_depth6", "lr0.01_depth9", "lr0.30_depth9",
    ]
    for _ in range(100000):
        val = [rng.randint(668, 712) for _ in names]
        test = [v + rng.randint(-22, 22) for v in val]
        if len(set(val)) != len(val) or len(set(test)) != len(test):
            continue
        bv = max(range(len(names)), key=lambda i: val[i])
        bt = max(range(len(names)), key=lambda i: test[i])
        if bv == bt or test[bt] - test[bv] < 12:
            continue
        rows = [(n, v, t) for n, v, t in zip(names, val, test)]
        table = csv(["config", "val_correct_of_800", "test_correct_of_800"], rows)
        analyst = r2(F(test[bt], 800) * 100)
        scenario = (
            "A team trained a classifier with 12 hyperparameter configurations. Each was scored on a validation "
            "set (800 examples) and on a held-out test set (800 examples).\n\n{t}\n\nAnalyst's write-up:\n"
            "I evaluated all 12 configurations and picked the one with the highest test accuracy, {c}. "
            "Its test accuracy is {a}%, which is our final reported performance."
        ).format(t=table, c=names[bt], a=analyst)
        question = (
            "The honest estimate of test accuracy, in percent: the test accuracy of the configuration that a "
            "correct workflow would select (using validation data only). Round to 2 decimals."
        )
        key = r2(F(test[bv], 800) * 100)
        return scenario, question, analyst, key, {"names": names, "val": val, "test": test, "best_val": bv, "best_test": bt}
    raise RuntimeError("no tuning instance")


# ---------------------------------------------------------------- Preprocessing leakage
def make_preproc(rng):
    for _ in range(100000):
        n = 16
        splits = ["train"] * 11 + ["test"] * 5
        rng.shuffle(splits)
        inc = [round(rng.uniform(18, 95), 1) for _ in range(n)]
        tr = [i for i in range(n) if splits[i] == "train"]
        te = [i for i in range(n) if splits[i] == "test"]
        miss = set(rng.sample(tr, 2) + rng.sample(te, 2))
        obs_all = [inc[i] for i in range(n) if i not in miss]
        obs_tr = [inc[i] for i in tr if i not in miss]
        mean_all = F(round(sum(obs_all) * 10), 10) / len(obs_all)
        mean_tr = F(round(sum(obs_tr) * 10), 10) / len(obs_tr)
        if abs(float(mean_all - mean_tr)) < 1.0:
            continue
        churn = [rng.randint(0, 1) for _ in range(n)]
        rows = [(i + 1, splits[i], "NA" if i in miss else inc[i], churn[i]) for i in range(n)]
        table = csv(["customer_id", "split", "income_k_eur", "churned"], rows)
        analyst = r2(mean_all)
        scenario = (
            "A bank predicts customer churn. The dataset below is already assigned to a train/test split. "
            "'NA' means income is missing.\n\n{t}\n\nAnalyst's pipeline write-up:\n"
            "Step 1: fill every missing income with the mean of the observed incomes across the whole dataset "
            "({a}). Step 2: standardize income using the same whole-dataset statistics. Step 3: fit the model on "
            "the train rows and evaluate on the test rows. Test AUC = 0.93."
        ).format(t=table, a=analyst)
        question = (
            "The income value (in thousands of EUR) that should have been used to fill the missing incomes in a "
            "leak-free pipeline: the mean of the observed incomes in the TRAIN rows only. Round to 2 decimals."
        )
        return scenario, question, analyst, r2(mean_tr), {"income": inc, "split": splits, "missing": sorted(miss)}
    raise RuntimeError("no preproc instance")


# ---------------------------------------------------------------- Target leakage (timing)
USABLE = [
    ("plan_type", 0), ("country", 0), ("signup_channel", 0), ("age_band", 0), ("device_type", 0),
    ("first_week_logins", 7), ("onboarding_completed", 10), ("support_tickets_first_14d", 14),
]
LEAKY = [
    ("days_active_first_30d", 30), ("refund_issued", 52), ("data_export_requested", 75),
    ("final_invoice_paid", 88), ("cancellation_survey_completed", 91),
]
LEGIT_SUSPICIOUS = [
    ("refund_count_prior_year", -90), ("previous_subscription_cancelled", -200),
    ("days_since_last_support_ticket_at_signup", 0), ("chargeback_history_flag", -120),
    ("trial_logins_first_week", 7), ("plan_type", 0), ("country", 0), ("onboarding_completed", 10),
]


def feature_table(feats):
    return csv(["feature", "first_recorded_on_day_relative_to_signup"], feats)


def make_leakage(rng):
    u = rng.sample(USABLE, 5)
    l = rng.sample(LEAKY, 3)
    feats = u + l
    rng.shuffle(feats)
    usable = sum(1 for _, d in feats if d <= 14)
    scenario = (
        "A SaaS company predicts which new customers will cancel within 90 days of signup. The model scores each "
        "customer on day 14 after signup, so only information recorded on or before day 14 is available at scoring time.\n\n"
        "{t}\n\nAnalyst's write-up:\nI trained gradient boosting on all {n} features above and got test AUC 0.99. "
        "This is a very strong model. Deploy it."
    ).format(t=feature_table(feats), n=len(feats))
    question = (
        "The number of the listed features that can legitimately be used at scoring time (recorded on or before "
        "day 14). Give a count."
    )
    return scenario, question, len(feats), usable, {"features": feats}


def make_control_features(rng):
    feats = list(LEGIT_SUSPICIOUS)
    rng.shuffle(feats)
    scenario = (
        "A SaaS company predicts which new customers will cancel within 90 days of signup. The model scores each "
        "customer on day 14 after signup, so only information recorded on or before day 14 is available at scoring time.\n\n"
        "{t}\n\nAnalyst's write-up:\nI trained gradient boosting on all {n} features above and got test AUC 0.76. "
        "That is a modest but useful lift over the current heuristic. Proceed to a pilot."
    ).format(t=feature_table(feats), n=len(feats))
    question = (
        "The number of the listed features that can legitimately be used at scoring time (recorded on or before "
        "day 14). Give a count."
    )
    return scenario, question, len(feats), len(feats), {"features": feats}


# ---------------------------------------------------------------- Control: clean balanced A/B
def make_control_ab(rng):
    for _ in range(10000):
        n = [rng.randint(900, 1600), rng.randint(900, 1600)]
        base = [rng.uniform(0.04, 0.06), rng.uniform(0.07, 0.10)]
        gain = [rng.uniform(0.004, 0.012), rng.uniform(0.004, 0.012)]
        cA = [round(x * b) for x, b in zip(n, base)]
        cB = [round(x * (b + g)) for x, b, g in zip(n, base, gain)]
        rA = [F(c, x) for c, x in zip(cA, n)]
        rB = [F(c, x) for c, x in zip(cB, n)]
        if not all(b > a for a, b in zip(rA, rB)):
            continue
        N = 2 * sum(n)
        std = sum(F(2 * x, N) * (rb - ra) for x, ra, rb in zip(n, rA, rB)) * 100
        OA, OB = F(sum(cA), sum(n)), F(sum(cB), sum(n))
        assert (OB - OA) * 100 == std  # equal allocation in each stratum
        key = r2(std)
        rows = []
        for i, dev in enumerate(["mobile", "desktop"]):
            rows.append((dev, "A", cA[i], n[i]))
            rows.append((dev, "B", cB[i], n[i]))
        table = csv(["device", "group", "conversions", "users"], rows)
        scenario = (
            "An online shop A/B-tested a new checkout page (B) against the old one (A). Users were randomized to A or B "
            "with equal allocation within each device type.\n\n{t}\n\nAnalyst's write-up:\n"
            "Pooled: A {SA}/{NA} = {ra:.2f}%, B {SB}/{NB} = {rb:.2f}%. B minus A = {d:+.2f} percentage points. "
            "The difference has the same sign on mobile and on desktop. Roll out B."
        ).format(t=table, SA=sum(cA), NA=sum(n), SB=sum(cB), NB=sum(n),
                 ra=float(OA) * 100, rb=float(OB) * 100, d=key)
        question = (
            "The standardized difference (B minus A) in conversion rate, in percentage points: compute each device's "
            "rate difference (B rate minus A rate) and weight it by that device's share of ALL users (both groups "
            "combined). Round to 2 decimals."
        )
        return scenario, question, key, key, {"n": n, "cA": cA, "cB": cB}
    raise RuntimeError("no control instance")


def main():
    rng = random.Random(SEED)
    specs = []

    def add(task_id, flaw, difficulty, kind, built, tol):
        scenario, question, analyst, key, data = built
        specs.append({
            "id": task_id,
            "tier": "core",
            "kind": kind,
            "difficulty": difficulty,
            "is_control": flaw == "none",
            "key": {"flaw": flaw, "value": key, "tol": tol},
            "analyst_value": analyst,
            "prompt": build_prompt(scenario, question, analyst),
            "data": data,
        })

    s = make_simpson(
        rng, ["mild sprain", "severe sprain"], ["injury_grade"],
        "A physiotherapy clinic compared two rehabilitation programs (P1 and P2) for ankle sprains. Success = back to "
        "full activity within 6 weeks. Patients were assigned by their physiotherapist. Data by injury grade:",
        "success rate", "patients", "P", ["P1", "P2"], (500, 700))
    add("simpson_2_strata", "simpsons_paradox", "medium", "stratified_confounding", s, 0.02)
    s = make_simpson(
        rng, ["bronze", "silver", "gold", "platinum"], ["customer_tier"],
        "An online retailer compared two promotional email versions (E1 and E2). Success = purchase within 7 days. "
        "Emails were sent by regional marketing teams who chose the version. Data by customer tier:",
        "purchase rate", "customers", "E", ["E1", "E2"], (6000, 9000))
    add("simpson_4_strata", "simpsons_paradox", "hard", "stratified_confounding", s, 0.02)
    add("base_rate_double_positive", "base_rate_fallacy", "medium", "bayes", make_base_rate(rng), 0.02)
    add("imbalanced_f1", "imbalanced_accuracy", "easy", "imbalance", make_imbalanced(rng), 0.02)
    add("multiple_comparisons_bh", "multiple_comparisons", "hard", "fdr", make_multiple(rng), 0.0)
    add("test_set_tuning", "test_set_tuning", "medium", "selection", make_tuning(rng), 0.02)
    add("preprocessing_leakage", "preprocessing_leakage", "medium", "leakage", make_preproc(rng), 0.02)
    add("target_leakage_timing", "target_leakage", "medium", "leakage", make_leakage(rng), 0.0)
    add("control_balanced_ab", "none", "control", "control", make_control_ab(rng), 0.02)
    add("control_legit_lagged_features", "none", "control", "control", make_control_features(rng), 0.0)

    specs += hard_tier.build(SEED)

    # integrity: for flawed tasks the analyst figure must not already be the key
    for t in specs:
        if not t["is_control"]:
            assert abs(t["analyst_value"] - t["key"]["value"]) > 10 * max(t["key"]["tol"], 0.01), t["id"]
        else:
            assert t["analyst_value"] == t["key"]["value"], t["id"]

    out = Path(__file__).with_name("tasks.json")
    out.write_text(encoding="utf-8", data=json.dumps({"seed": SEED, "flaw_labels": FLAWS, "flaw_labels_hard": hard_tier.FLAWS_HARD, "tasks": specs}, indent=2))
    print("wrote", out, "with", len(specs), "tasks")
    for t in specs:
        print("  {:32s} flaw={:22s} key={}".format(t["id"], t["key"]["flaw"], t["key"]["value"]))


if __name__ == "__main__":
    main()
