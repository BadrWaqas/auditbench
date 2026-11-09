# AuditBench: can frontier models catch a broken data analysis?

**Author:** Badr Ahmed (BSc Data Science, National College of Ireland) · micro1 Eval Hackathon, Nov 2026

## Short description

AuditBench tests whether an AI model can review a data analysis the way a senior data scientist would. Each of
19 tasks gives a colleague's analysis (a small table plus a confident write-up). The model must **name the
methodological flaw, or say the analysis is sound, and compute the corrected number**, with no tools. Flaws range from
textbook (Simpson's paradox, data leakage, base rates, multiple testing) to the forms they take in real work
(right-censored cohorts, regression to the mean, patient-level leakage, survivorship bias), plus three sound analyses
built to tempt a reviewer into a false alarm. Every answer key is computed in code, and grading is fully
deterministic, with no LLM judge.

**Key finding:** the gap is between model scales, not between textbook and real-world framing. A 7B model (Qwen2.5,
run locally) scored 43/100 on the core tier and 26/100 on the hard tier. It usually named the right textbook flaw but
could not compute the corrected number. On the realistic tasks it mostly declared flawed analyses sound, while also
raising false alarms on sound ones. A mid-size reasoning model (Nemotron Nano 30B) scored 90 (core) and 61 (hard), and shows where it breaks: it
solved the 32-row patient-leakage audit and the 20-fund survivorship audit, but failed the *identical* 130-row and 60-fund
versions by exhausting its 16,000-token reasoning budget. Same flaw, same question, only the table size changed. Frontier-scale models (Claude Opus 5.5,
Nemotron 3 Ultra 550B and Nemotron 3.5 Super) solved every task they were given, including a randomized-trial trap where
the textbook "Simpson's paradox" reflex is wrong. Their cost grew steeply with table size, though: 3-4x more reasoning
tokens for the 130-row and 60-fund versions of the same audits. I did not find a task that the strongest models fail,
and I report that rather than hide it.

## Video walkthrough

**https://youtu.be/jHa_L2XG-zw** (4:50, narrated by me; unlisted, anyone with the link can view)

## Domain and expertise

Applied statistics and machine-learning evaluation, from my BSc Data Science studies at the National
College of Ireland. The eval draws on the checks an experienced analyst runs before trusting a result:
whether to stratify or pool, whether information from the future or the test set leaked in, base rates,
multiple testing and class imbalance.

## What it tests and why it matters

AuditBench gives a model a realistic analysis written by a colleague (a small data table plus a confident
write-up) and asks it to act as the reviewer: **name the methodological flaw (or say the analysis is sound)
and compute the corrected number.**

Data teams increasingly ask LLMs to review notebooks, A/B test readouts and model reports. The errors that
matter in practice are not syntax errors. They are reasoning errors that produce a confident, wrong business
decision: Simpson's paradox in a non-randomized comparison, a preprocessing step that leaks test data,
a model that only looks good because the classes are imbalanced, twenty A/B metrics with no multiple-testing
correction. A reviewer that recognises the flaw but cannot produce the right corrected number, or that cries
"flaw!" at a sound analysis, is not a safe reviewer. AuditBench measures both halves.

**Who it is for:** teams evaluating LLMs as analytics/ML reviewers, and model developers who want a
compact, contamination-resistant probe of statistical judgement plus exact quantitative follow-through.

## The tasks (19 = 10 core + 9 hard)

**Core tier: the textbook versions (10 tasks).**

| # | Task id | Flaw planted | What the corrected number is | Difficulty |
|---|---|---|---|---|
| 1 | `simpson_2_strata` | Simpson's paradox (physio programs, non-random assignment) | standardized rate difference over 2 strata | medium |
| 2 | `simpson_4_strata` | Simpson's paradox (email promo, 4 customer tiers) | standardized rate difference over 4 strata | hard |
| 3 | `base_rate_double_positive` | Base-rate fallacy (two independent positive tests) | true P(condition given ++) | medium |
| 4 | `imbalanced_f1` | Accuracy on imbalanced data (sepsis model) | F1 of the positive class | easy |
| 5 | `multiple_comparisons_bh` | 20 metrics, no correction | # significant after Benjamini-Hochberg (5% FDR) | hard |
| 6 | `test_set_tuning` | Picking the best of 12 configs on the test set | test accuracy of the validation-selected config | medium |
| 7 | `preprocessing_leakage` | Imputation fitted on train+test | train-only imputation mean | medium |
| 8 | `target_leakage_timing` | Post-outcome features used at day-14 scoring | # features actually available at scoring time | medium |
| 9 | `control_balanced_ab` | **None** (randomized, balanced A/B with strata) | the analyst's figure (unchanged) | control |
| 10 | `control_legit_lagged_features` | **None** (suspicious-sounding but legitimately pre-signup features) | the analyst's figure (unchanged) | control |

**Hard tier: what the same flaws look like in real work (9 tasks).** Built after the first runs showed that strong
models clear the textbook versions. Each hard task adds what a real review involves: flaws outside the textbook list,
date arithmetic, longer tables, and a harmless red herring (a holiday dip, a firmware update, a renamed fund)
that a careful reviewer has to recognise as irrelevant. The label list grows to 13.

| # | Task id | Real flaw | What the corrected number is |
|---|---|---|---|
| 11 | `hard_cohort_censoring` | Right censoring: recent cohorts haven't reached day 30, so the dashboard counts them as churned ("retention is collapsing") | pooled day-30 retention over fully matured cohorts only (needs `cohort_end + 30 <= export date` for 12 cohorts) |
| 12 | `hard_regression_to_mean` | Regression to the mean: the worst Q1 reps were coached and "improved", but the randomized waitlisted reps improved almost as much | coached change minus waitlist change |
| 13 | `hard_patient_leakage` | Group leakage: scans split at random, so most "held-out" patients were also in training | accuracy on test scans of patients with no training scan |
| 14 | `hard_survivorship` | Survivorship bias: averaging only funds still open | mean return over all 20 launched funds |
| 15 | `hard_feature_windows` | Target leakage via feature windows that end after the 2026-02-01 scoring time (including one that ends exactly on 2026-02-01) | # features actually available at scoring time |
| 16 | `hard_control_cv_tuning` | **None**: 12 configs compared by CV inside the training set, test set used once (looks like test-set tuning, but isn't) | the analyst's figure (unchanged) |
| 17 | `hard_patient_leakage_xl` | Group leakage again, at realistic size: 130 scans from 40 patients | accuracy on test scans of patients with no training scan |
| 18 | `hard_survivorship_xl` | Survivorship bias again, at realistic size: 60 funds, 19 closed | mean return over all 60 launched funds |
| 19 | `hard_control_post_treatment` | **None**: a randomized trial where splitting by week-4 blood pressure (caused by the drug) reverses the effect in both strata. The textbook reflex says "Simpson's paradox", but stratifying on a mediator is the error, and the pooled randomized comparison is correct | the analyst's figure (unchanged) |

Tasks 17-18 are the same audits as 13-14 at about 4x and 3x the table size, so any drop in accuracy or rise in effort
is caused by scale alone.

The **controls** (tasks 9, 10, 16 and 19) look like tasks 1, 8, 6 and 1 on the surface. They measure *over-flagging*: a model that
pattern-matches "strata" to Simpson's paradox or "refund" to leakage gets them wrong.

Each prompt fixes the label set (core: `simpsons_paradox, preprocessing_leakage, target_leakage,
imbalanced_accuracy, base_rate_fallacy, test_set_tuning, multiple_comparisons, none`; hard adds `group_leakage,
optional_stopping, regression_to_the_mean, survivorship_bias, right_censoring`), defines the corrected
number precisely (formula and rounding), and requires a final JSON object:

```json
{"flaw": "<label>", "corrected_value": <number>, "reasoning": "<1-2 sentences>"}
```

## Design choices that make the failures real (not gotchas)

- **One defensible answer per task.** The corrected quantity is defined in the prompt, so the only open
  questions are "what is wrong?" and "can you compute it?".
- **Keys cannot be wrong.** `generate_tasks.py` builds each table and computes its key from the same numbers
  with exact `fractions.Fraction` arithmetic. `selftest.py` recomputes every key with a second,
  independent implementation.
- **Built-in traps against shortcuts:** in task 5 the Benjamini-Hochberg count differs from both the naive
  count and the Bonferroni count; in task 6 the best-on-test config differs from the best-on-validation one;
  in tasks 1-2 the treatment wins in *every* stratum but loses pooled; for every flawed task the analyst's
  number is far from the key, so copying it scores 0 on the number.
- **The hard tier uses its own random streams** (`SEED + 1` for tasks 11-16 and `SEED + 2` for 17-19, in
  `hard_tier.py`), so each addition left earlier tasks byte-identical. Results collected before an addition stay valid.
- **Synthetic, seeded, contamination-resistant.** Change `SEED` in `generate_tasks.py` to regenerate fresh
  instances with new numbers and keys.

## Grading (deterministic, `grader.py`)

| Check | Points | Rule |
|---|---|---|
| Flaw label | 50 | exact match after normalising case/spaces |
| Corrected number | 50 | within ±0.02 of the key (exact for counts) |
| **Task passed** | | both checks right |

Also reported: false-alarm rate on the controls and "said none on a flawed task" rate. The parser takes the
**last** JSON object containing `"flaw"` and tolerates code fences, `%` signs and prose. If the JSON is invalid, it
falls back to reading the `"flaw": "..."` and `"corrected_value": ...` fields directly (see failure analysis, point 5).
Anything else scores 0. API errors (rate limits, timeouts) are logged and counted separately, and never graded as wrong.

**Grader validation (`python selftest.py`, 63 checks, all pass):** every one of the 19 keys is recomputed by a
second, independent implementation; perfect answers score 100/100; the "always say none and copy the analyst"
baseline fails every flawed task; "right label, analyst's number"
scores exactly 50; a false alarm on a control is caught; out-of-tolerance numbers and invented labels are
rejected; formatting variants are accepted; invalid JSON with unambiguous fields is graded, but bare prose is not.

## Setup and run instructions

Python 3.9+ and the standard library only (`requirements.txt` is empty on purpose, so there's nothing to install).
Tested on Windows 11 with Python 3.14 and on Linux with Python 3.13.

**1. Verify the eval and re-grade the included raw outputs (no API key, a few seconds):**

```bash
python selftest.py && python report.py
```

**2. Run a model.** Supply the key either as an environment variable or in a `.env` file (copy `.env.example`
to `.env` and fill it in; `.env` is never shipped). A free OpenRouter key needs no card, and free models cost nothing.

```bash
export OPENROUTER_API_KEY=sk-or-...        # Windows PowerShell: $env:OPENROUTER_API_KEY="sk-or-..."
python run_eval.py --model nvidia/nemotron-3-ultra-550b-a55b:free --samples 2
python report.py                           # rewrites RESULTS.md and results_summary.json
```

Any OpenAI-compatible endpoint works too, for example a local Ollama model (no key needed):

```bash
python run_eval.py --model qwen2.5:7b --base-url http://localhost:11434/v1 --samples 3
```

`python generate_tasks.py` rebuilds `tasks.json` byte-for-byte from the seed. Change `SEED` to generate fresh,
unseen instances with new numbers and keys. Runs resume automatically if interrupted.

Or run any chat app by hand:

```bash
python run_eval.py --export-manual           # writes manual/prompts/<task>.txt
# paste each into a NEW chat, save the full reply as manual/<label>/<task>__<n>.txt
python run_eval.py --import-manual manual/<label> --label <label>
python report.py
```

**Runtime and cost:** about 20 to 60 minutes per model for one run of all 19 tasks (about one minute per answer on free
endpoints or a laptop GPU). Each prompt is about 1,000 to 1,500 tokens, so a paid frontier model costs well under
US$1 per full run, and free models cost $0. OpenRouter's free tier allows about 50 requests a day per account (about 2.5 full runs). Raw replies are stored verbatim in `results/*.jsonl` with model ID, settings and timestamp, and grading
happens only in `report.py`, so judges can re-grade without re-running anything.

## Models tested and results

Runs on 8-9 Nov 2026 (UTC). Settings for every API/local run: temperature 0.7, no tools, no system prompt,
`max_tokens` 16,000 (the first 3 Nemotron Ultra answers ran at 6,000 and finished well within it). Exact model IDs below
are as sent to the API; raw replies with model ID, settings, timestamps and token usage are in `results/*.jsonl`.

| Model (exact ID as sent) | How run | Runs | Core /100 (10 tasks) | Hard /100 (9 tasks) | Answers fully correct | False alarms on sound analyses |
|---|---|---|---|---|---|---|
| `nvidia/nemotron-3-ultra-550b-a55b:free` | OpenRouter API | 1 full run (+4 extra hard answers) | **100** | **100** | 23/23 | 0 |
| `nvidia/nemotron-3.5-super-vl:free` | OpenRouter API | 2 full runs | **100 ± 0** | **100 ± 0** | 38/38 | 0 |
| Claude Opus 5.5 (`claude-opus-5-5`, claude.ai chat) | manual chat, new chat per prompt | 1 run, hard tier only | - | **100** | 9/9 | 0 |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter API | 1 full run | **90** | **61.1** | 14/19 | 0 |
| `qwen2.5:7b` (Q4, Ollama) | local, laptop GPU | 3 full runs | **43.3 ± 2.4** | **25.9 ± 5.2** | 10/57 | 42% |

The Opus 5.5 answers came from the claude.ai chat app (I pasted each exported prompt into a fresh chat with Opus 5.5
selected, using the helper `manual/opus_helper.ps1`). The verbatim replies are in `manual/claude-opus-5.5_chat/` and
`results/claude-opus-5.5_chat.jsonl`. These can't be re-run by API key the way the other rows can, so they're labelled
`manual_chat`. Opus was run on the hard tier only, because that's where the question is.

Scores are means over complete runs of a tier (± sd across runs). "Flaw right" and "Number right" pool every answer to a
flawed task. Full per-task tables, a reasoning-token table and every wrong answer are in `RESULTS.md`.

**Why so few runs for the big models:** they ran on OpenRouter's free tier (50 requests a day per account), and I spent
today's allowance on breadth (a third model and a second run of Super) rather than repeating Ultra. The 7B model ran
locally, so it got 3 full runs.

## Failure analysis

**1. Where the 7B model breaks: "no flaw" on realistic framings.** On the core (textbook) tier Qwen2.5-7B usually
names the right flaw (49% of flawed-task answers) but almost never produces the right number (9%). It computes F1 as
~36.5 instead of 44.72, and Bayes' posterior as 0.40% instead of 66.03%. On the hard tier its labelling also collapses:
for right-censored cohorts, regression to the mean, and patient-level leakage (both the 32-row and the 130-row
versions) it answered **"none" in every run**, accepting "retention is collapsing", "coaching works" and "the model
generalises to new patients" at face value. These are the realistic versions of flaws it labelled correctly in textbook
form (leakage, selection effects).

**2. False alarms on sound analyses.** The same model flagged "preprocessing_leakage" in all 3 runs of the sound
lagged-features analysis (it treated features recorded *before* signup as leakage), and "test_set_tuning" in 2 of 3 runs of
the sound CV-tuning analysis. Interestingly, it passed the post-treatment trap 3/3, but only by echoing the analyst
("correctly pools the data"), not by recognising the mediator. Its reasoning text gives that away.

**3. Frontier-scale models: no failures, but cost scales with table size.** Nemotron 3 Ultra (550B), Nemotron 3.5
Super and Claude Opus 5.5 got every task they were given right, including the post-treatment control. Both Nemotrons
explicitly called week-4 blood pressure a mediator and said conditioning on it would bias the estimate. What grows is effort: Ultra used ~2,270 completion
tokens on the 32-row patient-leakage audit and ~9,300 on the 130-row version (4x the rows, 4x the tokens); Super used
~1,400 vs ~5,100 for the 20-fund vs 60-fund survivorship audit. Real audits involve thousands of rows, so a model
reading the table "by eye" will hit its reasoning budget long before it hits a conceptual wall. This is where I'd push
the eval next.

**4. The mid-size model shows the breaking point is scale.** Nemotron Nano 30B (a reasoning model) passed 9 of 10
core tasks and 5 of 9 hard tasks. Four of its five failures are the same thing: `finish_reason = length`, meaning it used
its whole 16,000-token budget reasoning and never produced an answer. That happened on `simpson_4_strata`, both
large-table audits (`hard_patient_leakage_xl`, `hard_survivorship_xl`) and the post-treatment trap. Yet it **passed the
small versions of both large audits** (`hard_patient_leakage`, 32 rows; `hard_survivorship`, 20 funds). The fifth miss
was an arithmetic slip: on censored cohorts it named `right_censoring` correctly but reported 30.58 instead of 35.64.
So the mid-size model knows the statistics. What it can't do is carry an exact audit across a realistic amount of
data within its budget. The frontier models did the same audits with the same budget but needed 3-4x more tokens than
on the small versions. The difference between them is headroom, not knowledge.

**5. A grader false-fail I caught and fixed.** Nemotron Super's first answer on `hard_patient_leakage` had the right
label and number (75.00) but invalid JSON (a missing quote before the reasoning text). The strict v1 parser scored it 0.
`grader.py` now falls back to reading the two graded fields with a strict `"key": value` pattern when no valid JSON
exists. `selftest.py` checks both that this case passes and that prose like "it is simpsons_paradox" is *not* graded.

**What this means.** I set out to show frontier models failing at data-analysis review, and in these runs the
strongest models I could access did not fail on the tasks I wrote. I'm reporting that as it is. The eval still does
its job: it separates models cleanly (hard tier: 26 for 7B, 61 for 30B, 100 for frontier) and pinpoints *how* weaker
models fail. The 7B model accepts a confident conclusion instead of checking the design. The 30B model knows the
statistics but runs out of budget as tables grow. The paired small/large tasks show this is a scale effect, and
scale is where I'd push to find a frontier ceiling: real-size tables (thousands of rows) and audits with several
interacting issues.

## Files

| File | Purpose |
|---|---|
| `generate_tasks.py` | builds all 19 tasks and exact answer keys into `tasks.json` |
| `hard_tier.py` | the 9 hard-tier task generators (imported by `generate_tasks.py`) |
| `tasks.json` | the eval (prompts, keys, underlying data) |
| `grader.py` | deterministic scoring |
| `selftest.py` | proves keys and grader are correct |
| `run_eval.py` | runner for OpenRouter / any OpenAI-compatible endpoint, plus manual export/import |
| `report.py` | grades everything into `RESULTS.md` and `results_summary.json` |
| `RESULTS.md` | full results: per model, per task, every wrong answer |
| `results/` | raw model replies (JSONL, verbatim, with model ID, settings, timestamp) |
| `manual/` | hard-tier prompts exported for chat apps, a helper script, and any manual chat replies |
| `requirements.txt`, `.env.example` | dependencies (none) and the one key name needed |

## Limitations

- 19 tasks and one or two runs per large model (free-tier limits): results show clear failure modes, not tight
  confidence intervals.
- Models answer without tools. With a Python tool the arithmetic half gets easier; recognising the flaw does not.
  That split (flaw label vs. number) is reported separately for exactly this reason.
- The flaw label set is given in the prompt, which makes the task easier than open-ended review. Failures
  under this generous setup are therefore a lower bound on real-world failure.

## Prior work and sources

Nothing existed before the hackathon. Everything was built from scratch during it (Oct 30 to Nov 9, 2026). No existing
benchmark or dataset is used, and all scenarios and numbers are synthetic, generated by `generate_tasks.py`.
The flaw types are standard textbook statistics concepts (Simpson's paradox, Benjamini-Hochberg FDR, Bayes'
theorem, data leakage). Code was written with help from an AI coding assistant. I reviewed the task design, flaw
taxonomy and checks.
