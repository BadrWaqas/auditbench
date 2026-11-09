"""AuditBench HARD tier: realistic complications an experienced analyst handles routinely.

Each task adds at least one of: a flaw that is not in the 'textbook' list (censoring, regression to the
mean, group leakage, survivorship), date arithmetic, a long table, and a benign red herring. One task is a
sound analysis that superficially resembles test-set tuning (over-flagging trap).
Uses its own RNG (SEED + 1) so the core tier is byte-identical to v1.
"""
import datetime as dt
import random
from fractions import Fraction as F

FLAWS_HARD = [
    "simpsons_paradox", "preprocessing_leakage", "target_leakage", "group_leakage", "imbalanced_accuracy",
    "base_rate_fallacy", "test_set_tuning", "multiple_comparisons", "optional_stopping",
    "regression_to_the_mean", "survivorship_bias", "right_censoring", "none",
]

PREAMBLE_HARD = """You are a senior data scientist reviewing a colleague's analysis before it goes to leadership.
Read the scenario below. Decide whether the analysis contains a methodological flaw that invalidates its main
conclusion, and compute the corrected number. Some details in a scenario may look unusual but be harmless.

Rules:
- You have no tools and cannot run code. Work the arithmetic out yourself.
- "flaw" must be exactly one of: {flaws}
- Use "none" if the analysis is sound. In that case "corrected_value" is the analyst's reported figure, unchanged.
- "corrected_value" is a single number (no units, no % sign), defined at the end of the scenario.
- Finish your reply with ONE JSON object and nothing after it, in exactly this form:
{{"flaw": "<one label>", "corrected_value": <number>, "reasoning": "<one or two sentences>"}}
""".format(flaws=", ".join(FLAWS_HARD))


def r2(x):
    return round(float(x), 2)


def csv(header, rows):
    return "\n".join([",".join(header)] + [",".join(str(c) for c in r) for r in rows])


def prompt(scenario, question, analyst_value):
    return (PREAMBLE_HARD + "\n=== SCENARIO ===\n" + scenario.strip() + "\n\n=== WHAT corrected_value MEANS ===\n"
            + question.strip() + "\nThe analyst's reported figure, in the same units, is: {}\n".format(analyst_value))


# ------------------------------------------------------------------ H1 right censoring (cohort retention)
def h_censoring(rng):
    analysis = dt.date(2026, 3, 1)
    first = dt.date(2025, 12, 1)  # a Monday
    for _ in range(10000):
        rows, mature_s, mature_r, all_s, all_r = [], 0, 0, 0, 0
        n_mature = 0
        for w in range(12):
            start = first + dt.timedelta(days=7 * w)
            end = start + dt.timedelta(days=6)
            signups = rng.randint(380, 720)
            true_rate = rng.uniform(0.31, 0.39)
            mature = end + dt.timedelta(days=30) <= analysis
            if mature:
                ret = round(signups * true_rate)
                mature_s += signups
                mature_r += ret
                n_mature += 1
            else:
                # users who have not yet reached day 30 are counted as 'not retained' by the dashboard
                reached = sum(1 for d in range(7) if start + dt.timedelta(days=d + 30) <= analysis)
                ret = round(signups * true_rate * reached / 7)
            all_s += signups
            all_r += ret
            rows.append((start.isoformat(), end.isoformat(), signups, ret))
        if n_mature != 8:
            continue
        naive = r2(F(all_r, all_s) * 100)
        key = r2(F(mature_r, mature_s) * 100)
        if key - naive < 3:
            continue
        table = csv(["cohort_start", "cohort_end", "signups", "retained_day30"], rows)
        recent = rows[-4:]
        recent_rate = sum(r[3] for r in recent) / sum(r[2] for r in recent) * 100
        scenario = (
            "A subscription app reports day-30 retention by weekly signup cohort. The table was exported from the "
            "product dashboard on {a}. The dashboard counts a user as retained_day30 if the user was active on "
            "day 30 after their own signup date; any user who has not been active on day 30 is counted as not "
            "retained. Note: the cohort starting 2025-12-22 includes the Christmas holidays, so signups are "
            "lower than usual (this is expected seasonality).\n\n{t}\n\nAnalyst's write-up:\n"
            "Overall day-30 retention is {n}% across all 12 cohorts, and the 4 most recent cohorts are down to "
            "{rr:.1f}%. Retention is collapsing; we need an emergency retention project."
        ).format(a=analysis.isoformat(), t=table, n=naive, rr=recent_rate)
        question = (
            "Pooled day-30 retention in percent, computed only over cohorts in which EVERY user has had a full 30 "
            "days by the export date (cohort_end + 30 days <= export date): total retained_day30 divided by total "
            "signups across those cohorts. Round to 2 decimals."
        )
        return scenario, question, naive, key, {"rows": rows, "analysis": analysis.isoformat(), "n_mature": n_mature}
    raise RuntimeError("censoring")


# ------------------------------------------------------------------ H2 regression to the mean
def h_rtm(rng):
    for _ in range(10000):
        rows, ch, wl = [], [], []
        ids = rng.sample(range(101, 181), 20)
        groups = ["coached"] * 10 + ["waitlist"] * 10
        rng.shuffle(groups)
        for i, g in zip(ids, groups):
            q1 = rng.randint(52, 74)
            q2 = q1 + rng.randint(4, 19) + (rng.randint(0, 4) if g == "coached" else 0)
            rows.append(("R{}".format(i), g, q1, q2))
            (ch if g == "coached" else wl).append(q2 - q1)
        naive = F(sum(ch), 10)
        key = F(sum(ch), 10) - F(sum(wl), 10)
        if not (F(1) <= key <= F(4)) or naive < 9:
            continue
        rows.sort(key=lambda r: r[0])
        table = csv(["rep_id", "group", "q1_deals", "q2_deals"], rows)
        mean_q1 = sum(r[2] for r in rows if r[1] == "coached") / 10
        mean_q2 = sum(r[3] for r in rows if r[1] == "coached") / 10
        scenario = (
            "A company has 80 sales reps. After Q1, it took the 20 reps with the LOWEST Q1 deal counts and randomly "
            "assigned 10 of them to a new coaching program; the other 10 were put on a waitlist and received no "
            "coaching until after Q2. Rep R137's Q1 number was entered a day late, but it was verified as correct.\n\n"
            "{t}\n\nAnalyst's write-up:\nCoached reps went from an average of {a:.1f} deals in Q1 to {b:.1f} in Q2, "
            "an improvement of {n} deals per rep. The coaching program clearly works and should be rolled out to "
            "all 80 reps."
        ).format(t=table, a=mean_q1, b=mean_q2, n=r2(naive))
        question = (
            "The estimated effect of coaching in deals per rep: the mean Q1-to-Q2 change of the coached reps minus "
            "the mean Q1-to-Q2 change of the waitlisted reps. Round to 2 decimals."
        )
        return scenario, question, r2(naive), r2(key), {"rows": rows}
    raise RuntimeError("rtm")


# ------------------------------------------------------------------ H3 group (patient) leakage
def h_group(rng):
    for _ in range(100000):
        patients = ["P{:02d}".format(i) for i in rng.sample(range(10, 99), 12)]
        counts = [rng.choice([1, 2, 3, 3, 4, 5]) for _ in patients]
        scans = []
        for p, c in zip(patients, counts):
            scans += [p] * c
        if not 32 <= len(scans) <= 40:
            continue
        rng.shuffle(scans)
        n_test = len(scans) // 3
        split = ["test"] * n_test + ["train"] * (len(scans) - n_test)
        rng.shuffle(split)
        train_p = {p for p, s in zip(scans, split) if s == "train"}
        rows, clean, leak = [], [], []
        for i, (p, s) in enumerate(zip(scans, split), start=1):
            if s == "train":
                rows.append(("S{:03d}".format(i), p, s, "-"))
            else:
                leaked = p in train_p
                c = 1 if rng.random() < (0.97 if leaked else 0.6) else 0
                (leak if leaked else clean).append(c)
                rows.append(("S{:03d}".format(i), p, s, c))
        if not (4 <= len(clean) <= 6) or len(leak) < 5:
            continue
        naive = F(sum(clean) + sum(leak), len(clean) + len(leak)) * 100
        key = F(sum(clean), len(clean)) * 100
        if naive - key < 15:
            continue
        table = csv(["scan_id", "patient_id", "split", "model_correct"], rows)
        scenario = (
            "A hospital trains an image classifier on chest scans. Some patients have several scans. The team "
            "randomly assigned each SCAN to train or test. model_correct is 1 if the final model classified that "
            "test scan correctly (train rows show '-'). The scanner firmware was updated halfway through data "
            "collection; the vendor confirmed images are unaffected.\n\n{t}\n\nAnalyst's write-up:\n"
            "Test accuracy is {n}% on {k} held-out scans. The model generalises well to new patients and is ready "
            "for a pilot in another hospital."
        ).format(t=table, n=r2(naive), k=len(clean) + len(leak))
        question = (
            "Accuracy in percent on the test scans from patients who have NO scan in the training set (an estimate "
            "of performance on genuinely new patients). Round to 2 decimals."
        )
        return scenario, question, r2(naive), r2(key), {"rows": rows}
    raise RuntimeError("group")


# ------------------------------------------------------------------ H4 survivorship bias
def h_survivor(rng):
    for _ in range(10000):
        n_closed = 7
        rows = []
        names = rng.sample(["Atlas", "Birch", "Cobalt", "Delta", "Ember", "Fjord", "Granite", "Harbor", "Iris",
                            "Juniper", "Kestrel", "Lumen", "Meridian", "Nimbus", "Orchard", "Pioneer", "Quarry",
                            "Ridge", "Summit", "Tidal", "Umber", "Vale"], 20)
        status = ["closed"] * n_closed + ["open"] * (20 - n_closed)
        rng.shuffle(status)
        for nm, st in zip(names, status):
            if st == "open":
                rows.append((nm + " Growth Fund", "open", "2026-01-01", rng.randint(38, 142)))
            else:
                y = rng.randint(2018, 2023)
                rows.append((nm + " Growth Fund", "closed", "{}-0{}-01".format(y, rng.randint(1, 9)), rng.randint(-46, 12)))
        open_r = [r[3] for r in rows if r[1] == "open"]
        naive = F(sum(open_r), len(open_r))
        key = F(sum(r[3] for r in rows), 20)
        if naive - key < 15:
            continue
        table = csv(["fund", "status", "return_measured_until", "cumulative_return_pct"], rows)
        scenario = (
            "An investment newsletter studies all 20 'Growth' funds that launched in January 2016 in one market. "
            "7 have since been closed or merged into other funds; for those, the cumulative return is measured "
            "from launch until the closure date. Ridge Growth Fund changed its name in 2021 (its record is "
            "continuous and complete).\n\n{t}\n\nAnalyst's write-up:\nUsing the funds in our current database "
            "(the {k} funds still open), the average 10-year cumulative return of Growth funds launched in 2016 is "
            "{n}%. Readers should expect roughly this from a newly launched Growth fund."
        ).format(t=table, k=len(open_r), n=r2(naive))
        question = (
            "The average cumulative return in percent across ALL 20 funds that launched, using each closed fund's "
            "return up to its closure. Round to 2 decimals."
        )
        return scenario, question, r2(naive), r2(key), {"rows": rows}
    raise RuntimeError("survivor")


# ------------------------------------------------------------------ H5 feature windows vs scoring date
def h_windows(rng):
    feats = [
        ("avg_balance_90d", "2025-11-03", "2026-01-31"), ("txn_count_30d", "2026-01-02", "2026-01-31"),
        ("salary_deposit_flag_60d", "2025-12-03", "2026-01-31"), ("overdraft_days_30d", "2026-01-17", "2026-02-15"),
        ("max_balance_6m", "2025-08-01", "2026-01-31"), ("missed_payments_12m", "2025-02-01", "2026-01-31"),
        ("support_calls_7d", "2026-01-26", "2026-02-01"), ("card_spend_trend_q", "2025-11-01", "2026-01-31"),
        ("collections_contact_flag", "2026-02-01", "2026-03-31"), ("age_of_account_days", "2015-03-10", "2026-01-31"),
        ("balance_at_extract", "2026-03-31", "2026-03-31"), ("app_logins_14d", "2026-01-18", "2026-01-31"),
    ]
    rng.shuffle(feats)
    cutoff = dt.date(2026, 1, 31)
    usable = sum(1 for _, _, e in feats if dt.date.fromisoformat(e) <= cutoff)
    table = csv(["feature", "window_start", "window_end"], feats)
    scenario = (
        "A bank builds a model to predict which customers will default between 2026-02-01 and 2026-03-31. In "
        "production the model will score every customer at 00:00 on 2026-02-01, using only data recorded up to and "
        "including 2026-01-31. Each feature below is computed from data recorded between window_start and "
        "window_end inclusive. The training extract was pulled on 2026-03-31. age_of_account_days starts in 2015 "
        "because it uses the account opening date; that is intended.\n\n{t}\n\nAnalyst's write-up:\n"
        "Using all {n} features, the model reaches AUC 0.97 on a held-out set of customers. We should deploy it "
        "for the 2026-02-01 scoring run."
    ).format(t=table, n=len(feats))
    question = (
        "The number of the listed features that are actually available at scoring time (window_end on or before "
        "2026-01-31). Give a count."
    )
    return scenario, question, len(feats), usable, {"features": feats}


# ------------------------------------------------------------------ H6 sound analysis that resembles test-set tuning
def h_control_cv(rng):
    names = ["lr{:.2f}_depth{}".format(lr, d) for lr in (0.3, 0.1, 0.05, 0.01) for d in (3, 6, 9)]
    for _ in range(10000):
        cv = [rng.randint(8120, 8660) for _ in names]
        if len(set(cv)) != len(cv):
            continue
        best = max(range(len(names)), key=lambda i: cv[i])
        test_acc = F(rng.randint(1675, 1735), 2000) * 100
        rows = [(n, "{:.2f}".format(c / 100)) for n, c in zip(names, cv)]
        table = csv(["config", "mean_5fold_cv_accuracy_on_train_pct"], rows)
        reported = r2(test_acc)
        scenario = (
            "A team tuned a gradient-boosting classifier. They split the data once into a training set (8,000 rows) "
            "and a held-out test set (2,000 rows). All 12 configurations below were compared using 5-fold "
            "cross-validation INSIDE the training set only. The test set was locked away and was not looked at "
            "during tuning. The test set was labelled by a different annotation team, using the same guidelines.\n\n"
            "{t}\n\nAnalyst's write-up:\nI picked the configuration with the best cross-validation score ({c}), "
            "retrained it on the full training set, and evaluated it exactly once on the held-out test set: "
            "{r}% accuracy. That is our reported performance estimate."
        ).format(t=table, c=names[best], r=reported)
        question = "The final test accuracy in percent that should be reported. Round to 2 decimals."
        return scenario, question, reported, reported, {"cv_x100": cv, "best": best}
    raise RuntimeError("cv")


# ------------------------------------------------------------------ H7 group leakage at realistic table size
def h_group_xl(rng):
    for _ in range(100000):
        patients = ["P{:03d}".format(i) for i in rng.sample(range(100, 999), 40)]
        counts = [rng.choice([1, 2, 2, 3, 3, 4, 5, 6]) for _ in patients]
        scans = []
        for p, c in zip(patients, counts):
            scans += [p] * c
        if not 110 <= len(scans) <= 130:
            continue
        rng.shuffle(scans)
        n_test = len(scans) // 3
        split = ["test"] * n_test + ["train"] * (len(scans) - n_test)
        rng.shuffle(split)
        train_p = {p for p, s in zip(scans, split) if s == "train"}
        rows, clean, leak = [], [], []
        for i, (p, s) in enumerate(zip(scans, split), start=1):
            if s == "train":
                rows.append(("S{:04d}".format(i), p, s, "-"))
            else:
                leaked = p in train_p
                c = 1 if rng.random() < (0.95 if leaked else 0.62) else 0
                (leak if leaked else clean).append(c)
                rows.append(("S{:04d}".format(i), p, s, c))
        if not (8 <= len(clean) <= 13):
            continue
        naive = F(sum(clean) + sum(leak), len(clean) + len(leak)) * 100
        key = F(sum(clean), len(clean)) * 100
        if naive - key < 15:
            continue
        table = csv(["scan_id", "patient_id", "split", "model_correct"], rows)
        scenario = (
            "A hospital trains an image classifier on chest scans from 40 patients; most patients have several "
            "scans. The team randomly assigned each SCAN to train or test. model_correct is 1 if the final model "
            "classified that test scan correctly (train rows show '-'). Two radiologists labelled the scans; "
            "their agreement was checked and is high.\n\n{t}\n\nAnalyst's write-up:\nTest accuracy is {n}% on "
            "{k} held-out scans. The model generalises well to new patients and is ready for a pilot in another "
            "hospital."
        ).format(t=table, n=r2(naive), k=len(clean) + len(leak))
        question = (
            "Accuracy in percent on the test scans from patients who have NO scan in the training set (an estimate "
            "of performance on genuinely new patients). Round to 2 decimals."
        )
        return scenario, question, r2(naive), r2(key), {"rows": rows}
    raise RuntimeError("group_xl")


# ------------------------------------------------------------------ H8 survivorship at realistic table size
def h_survivor_xl(rng):
    syll = ["Al", "Bra", "Cor", "Dun", "El", "Fen", "Gar", "Hol", "Ist", "Jor", "Kel", "Lor", "Mar", "Nor", "Os",
            "Per", "Quin", "Ros", "Sel", "Tor", "Ul", "Ven", "Wes", "Yar"]
    for _ in range(10000):
        names = set()
        while len(names) < 60:
            names.add(rng.choice(syll) + rng.choice(["ton", "ridge", "field", "mere", "wick", "dale", "ford", "stone"]))
        names = sorted(names)
        rng.shuffle(names)
        status = ["closed"] * 19 + ["open"] * 41
        rng.shuffle(status)
        rows = []
        for nm, st in zip(names, status):
            if st == "open":
                rows.append((nm + " Value Fund", "open", "2026-01-01", rng.randint(21, 118)))
            else:
                rows.append((nm + " Value Fund", "closed", "{}-{:02d}-01".format(rng.randint(2017, 2024), rng.randint(1, 12)),
                             rng.randint(-52, 15)))
        open_r = [r[3] for r in rows if r[1] == "open"]
        naive = F(sum(open_r), len(open_r))
        key = F(sum(r[3] for r in rows), len(rows))
        if naive - key < 15:
            continue
        table = csv(["fund", "status", "return_measured_until", "cumulative_return_pct"], rows)
        scenario = (
            "A fund-research team studies all 60 'Value' funds that launched in January 2016 in one market. 19 have "
            "since been closed or merged into other funds; for those, the cumulative return is measured from launch "
            "until the closure date. Fees are already deducted in every number.\n\n{t}\n\nAnalyst's write-up:\n"
            "Using the funds in our current database (the {k} funds still open), the average 10-year cumulative "
            "return of Value funds launched in 2016 is {n}%. Investors should expect roughly this from a newly "
            "launched Value fund."
        ).format(t=table, k=len(open_r), n=r2(naive))
        question = (
            "The average cumulative return in percent across ALL 60 funds that launched, using each closed fund's "
            "return up to its closure. Round to 2 decimals."
        )
        return scenario, question, r2(naive), r2(key), {"rows": rows}
    raise RuntimeError("survivor_xl")


# ------------------------------------------------------------------ H9 sound RCT analysis; stratifier is post-treatment
def h_control_mediator(rng):
    for _ in range(100000):
        nd, npl = rng.randint(600, 700), rng.randint(600, 700)
        # the drug lowers blood pressure, so far more drug patients have BP controlled at week 4
        cd = round(nd * rng.uniform(0.72, 0.82))
        cp = round(npl * rng.uniform(0.18, 0.28))
        rec = {}
        rec["drug_yes"] = round(cd * rng.uniform(0.55, 0.62))
        rec["plac_yes"] = round(cp * rng.uniform(0.66, 0.74))
        rec["drug_no"] = round((nd - cd) * rng.uniform(0.18, 0.25))
        rec["plac_no"] = round((npl - cp) * rng.uniform(0.27, 0.34))
        within = (F(rec["drug_yes"], cd) < F(rec["plac_yes"], cp)) and (F(rec["drug_no"], nd - cd) < F(rec["plac_no"], npl - cp))
        pooled = (F(rec["drug_yes"] + rec["drug_no"], nd) - F(rec["plac_yes"] + rec["plac_no"], npl)) * 100
        if not within or pooled < 4:
            continue
        rows = [("yes", "drug", rec["drug_yes"], cd), ("yes", "placebo", rec["plac_yes"], cp),
                ("no", "drug", rec["drug_no"], nd - cd), ("no", "placebo", rec["plac_no"], npl - cp)]
        table = csv(["bp_controlled_at_week4", "arm", "recovered_at_week12", "patients"], rows)
        key = r2(pooled)
        scenario = (
            "A double-blind randomized trial compares a new drug with placebo for patients with hypertensive kidney "
            "disease. Patients were randomized at week 0. The drug works partly by lowering blood pressure. At week 4 "
            "(after treatment started) each patient's blood pressure was recorded as controlled (yes/no). The primary "
            "outcome is recovery at week 12. Randomization was checked and the arms are balanced at baseline.\n\n{t}"
            "\n\nAnalyst's write-up:\nPooling all randomized patients: drug {a}/{na} = {ra:.1f}% recovered, placebo "
            "{b}/{nb} = {rb:.1f}%. Drug minus placebo = {d:+.2f} percentage points. The drug improves recovery and "
            "should go to the regulator."
        ).format(t=table, a=rec["drug_yes"] + rec["drug_no"], na=nd, ra=float(F(rec["drug_yes"] + rec["drug_no"], nd)) * 100,
                 b=rec["plac_yes"] + rec["plac_no"], nb=npl, rb=float(F(rec["plac_yes"] + rec["plac_no"], npl)) * 100, d=key)
        question = (
            "The effect of the drug on week-12 recovery, in percentage points (drug minus placebo), that should be "
            "reported as the trial's primary result. Round to 2 decimals."
        )
        return scenario, question, key, key, {"rows": rows}
    raise RuntimeError("mediator")


def build(seed):
    rng = random.Random(seed + 1)
    out = []

    def add(tid, flaw, kind, built, tol):
        scenario, question, analyst, key, data = built
        out.append({"id": tid, "tier": "hard", "kind": kind, "difficulty": "hard", "is_control": flaw == "none",
                    "key": {"flaw": flaw, "value": key, "tol": tol}, "analyst_value": analyst,
                    "prompt": prompt(scenario, question, analyst), "data": data})

    add("hard_cohort_censoring", "right_censoring", "censoring", h_censoring(rng), 0.02)
    add("hard_regression_to_mean", "regression_to_the_mean", "rtm", h_rtm(rng), 0.02)
    add("hard_patient_leakage", "group_leakage", "leakage", h_group(rng), 0.02)
    add("hard_survivorship", "survivorship_bias", "survivorship", h_survivor(rng), 0.02)
    add("hard_feature_windows", "target_leakage", "leakage", h_windows(rng), 0.0)
    add("hard_control_cv_tuning", "none", "control", h_control_cv(rng), 0.02)
    # added later in the hackathon on a separate random stream, so the six tasks above are unchanged
    rng2 = random.Random(seed + 2)
    add("hard_patient_leakage_xl", "group_leakage", "leakage", h_group_xl(rng2), 0.02)
    add("hard_survivorship_xl", "survivorship_bias", "survivorship", h_survivor_xl(rng2), 0.02)
    add("hard_control_post_treatment", "none", "control", h_control_mediator(rng2), 0.02)
    return out
