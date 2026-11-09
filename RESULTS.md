# AuditBench results

Per task: 50 pts for the correct flaw label + 50 pts for the corrected number. Tier score = mean over complete runs of that tier (± sd across runs). Percent columns pool every graded answer.

| Model | How run | Core tier /100 (10 tasks) | Hard tier /100 (9 tasks) | Answers fully correct | Flaw label right (flawed tasks) | Number right (flawed tasks) | Said 'none' on a flawed task | False alarm on sound analyses | API errors |
|---|---|---|---|---|---|---|---|---|---|
| nvidia/nemotron-3-ultra-550b-a55b:free | api | 100.0 ± 0.0 (1 run) | 100.0 ± 0.0 (1 run) | 100% | 100% | 100% | 0% | 0% | 0 |
| nvidia/nemotron-3.5-super-vl:free | api | 100.0 ± 0.0 (2 runs) | 100.0 ± 0.0 (2 runs) | 100% | 100% | 100% | 0% | 0% | 0 |
| claude-opus-5.5_chat | manual_chat | - | 100.0 ± 0.0 (1 run) | 100% | 100% | 100% | 0% | 0% | 0 |
| nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free | api | 90.0 ± 0.0 (1 run) | 61.1 ± 0.0 (1 run) | 74% | 80% | 73% | 0% | 0% | 0 |
| qwen2.5:7b | local | 43.3 ± 2.4 (3 runs) | 25.9 ± 5.2 (3 runs) | 18% | 49% | 9% | 36% | 42% | 0 |

## Pass rate per task (samples fully correct / samples run)

| Tier | Task | Key | nemotron-3-ultra-550b_openrouter | nemotron-3.5-super_openrouter | claude-opus-5.5_chat | nemotron-3-nano-30b_openrouter | qwen2.5-7b_ollama-local |
|---|---|---|---|---|---|---|---|
| core | simpson_2_strata | simpsons_paradox = 3.05 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| core | simpson_4_strata | simpsons_paradox = 5.65 | 1/1 | 2/2 | - | 0/1 | 0/3 |
| core | base_rate_double_positive | base_rate_fallacy = 66.03 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| core | imbalanced_f1 | imbalanced_accuracy = 44.72 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| core | multiple_comparisons_bh | multiple_comparisons = 3 | 1/1 | 2/2 | - | 1/1 | 3/3 |
| core | test_set_tuning | test_set_tuning = 86.75 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| core | preprocessing_leakage | preprocessing_leakage = 43.17 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| core | target_leakage_timing | target_leakage = 5 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| core | control_balanced_ab | none = 1.06 | 1/1 | 2/2 | - | 1/1 | 3/3 |
| core | control_legit_lagged_features | none = 8 | 1/1 | 2/2 | - | 1/1 | 0/3 |
| hard | hard_cohort_censoring | right_censoring = 35.64 | 2/2 | 2/2 | 1/1 | 0/1 | 0/3 |
| hard | hard_regression_to_mean | regression_to_the_mean = 1.7 | 1/1 | 2/2 | 1/1 | 1/1 | 0/3 |
| hard | hard_patient_leakage | group_leakage = 75.0 | 1/1 | 2/2 | 1/1 | 1/1 | 0/3 |
| hard | hard_survivorship | survivorship_bias = 51.65 | 1/1 | 2/2 | 1/1 | 1/1 | 0/3 |
| hard | hard_feature_windows | target_leakage = 8 | 1/1 | 2/2 | 1/1 | 1/1 | 0/3 |
| hard | hard_control_cv_tuning | none = 86.55 | 1/1 | 2/2 | 1/1 | 1/1 | 1/3 |
| hard | hard_patient_leakage_xl | group_leakage = 55.56 | 2/2 | 2/2 | 1/1 | 0/1 | 0/3 |
| hard | hard_survivorship_xl | survivorship_bias = 44.95 | 2/2 | 2/2 | 1/1 | 0/1 | 0/3 |
| hard | hard_control_post_treatment | none = 10.28 | 2/2 | 2/2 | 1/1 | 0/1 | 3/3 |

## Reasoning effort (mean completion tokens per answer, where the API reported usage)

| Task | nemotron-3-ultra-550b_openrouter | nemotron-3.5-super_openrouter | claude-opus-5.5_chat | nemotron-3-nano-30b_openrouter | qwen2.5-7b_ollama-local |
|---|---|---|---|---|---|
| simpson_2_strata | - | 5,846 | - | 9,471 | - |
| simpson_4_strata | 9,732 | 11,460 | - | 16,000 | - |
| base_rate_double_positive | - | 2,342 | - | 3,419 | - |
| imbalanced_f1 | - | 1,930 | - | 2,831 | - |
| multiple_comparisons_bh | 2,069 | 2,368 | - | 1,439 | - |
| test_set_tuning | 1,221 | 1,298 | - | 617 | - |
| preprocessing_leakage | 1,128 | 1,434 | - | 1,019 | - |
| target_leakage_timing | 830 | 1,495 | - | 389 | - |
| control_balanced_ab | 2,355 | 3,944 | - | 2,246 | - |
| control_legit_lagged_features | 1,284 | 3,571 | - | 852 | - |
| hard_cohort_censoring | 3,540 | 5,240 | - | 8,614 | 51 |
| hard_regression_to_mean | 1,301 | 6,102 | - | 2,149 | 45 |
| hard_patient_leakage | 2,267 | 2,331 | - | 3,271 | 70 |
| hard_survivorship | 1,771 | 1,868 | - | 1,943 | 53 |
| hard_feature_windows | 2,070 | 5,359 | - | 1,158 | 63 |
| hard_control_cv_tuning | 1,805 | 2,146 | - | 1,094 | 71 |
| hard_patient_leakage_xl | 9,318 | 8,612 | - | 16,000 | 56 |
| hard_survivorship_xl | 4,016 | 5,192 | - | 16,000 | 59 |
| hard_control_post_treatment | 3,584 | 6,668 | - | 16,000 | 54 |

## Every wrong answer

**nemotron-3-ultra-550b_openrouter**: 0 wrong of 23

**nemotron-3.5-super_openrouter**: 0 wrong of 38

**claude-opus-5.5_chat**: 0 wrong of 9

**nemotron-3-nano-30b_openrouter**: 5 wrong of 19
- simpson_4_strata (sample 1): said None / None; key simpsons_paradox / 5.65. no parseable JSON [finish_reason=length]
- hard_cohort_censoring (sample 1): said right_censoring / 30.58; key right_censoring / 35.64. right label, wrong number
- hard_patient_leakage_xl (sample 1): said None / None; key group_leakage / 55.56. no parseable JSON [finish_reason=length]
- hard_survivorship_xl (sample 1): said None / None; key survivorship_bias / 44.95. no parseable JSON [finish_reason=length]
- hard_control_post_treatment (sample 1): said None / None; key none / 10.28. no parseable JSON [finish_reason=length]

**qwen2.5-7b_ollama-local**: 47 wrong of 57
- simpson_2_strata (sample 1): said none / -16.88; key simpsons_paradox / 3.05. wrong label and number
- simpson_4_strata (sample 1): said none / -4.31; key simpsons_paradox / 5.65. wrong label and number
- base_rate_double_positive (sample 1): said base_rate_fallacy / 0.4; key base_rate_fallacy / 66.03. right label, wrong number
- imbalanced_f1 (sample 1): said imbalanced_accuracy / 36.86; key imbalanced_accuracy / 44.72. right label, wrong number
- test_set_tuning (sample 1): said test_set_tuning / 81.13; key test_set_tuning / 86.75. right label, wrong number
- preprocessing_leakage (sample 1): said preprocessing_leakage / 43.0; key preprocessing_leakage / 43.17. right label, wrong number
- target_leakage_timing (sample 1): said preprocessing_leakage / 5.0; key target_leakage / 5. wrong label, right number
- control_legit_lagged_features (sample 1): said preprocessing_leakage / 6.0; key none / 8. wrong label and number
- simpson_2_strata (sample 2): said none / -16.88; key simpsons_paradox / 3.05. wrong label and number
- simpson_4_strata (sample 2): said simpsons_paradox / -4.29; key simpsons_paradox / 5.65. right label, wrong number
- base_rate_double_positive (sample 2): said base_rate_fallacy / 2.56; key base_rate_fallacy / 66.03. right label, wrong number
- imbalanced_f1 (sample 2): said imbalanced_accuracy / 36.75; key imbalanced_accuracy / 44.72. right label, wrong number
- test_set_tuning (sample 2): said test_set_tuning / 71.88; key test_set_tuning / 86.75. right label, wrong number
- preprocessing_leakage (sample 2): said preprocessing_leakage / 42.97; key preprocessing_leakage / 43.17. right label, wrong number
- target_leakage_timing (sample 2): said preprocessing_leakage / 6.0; key target_leakage / 5. wrong label and number
- control_legit_lagged_features (sample 2): said preprocessing_leakage / 6.0; key none / 8. wrong label and number
- simpson_2_strata (sample 3): said none / -16.88; key simpsons_paradox / 3.05. wrong label and number
- simpson_4_strata (sample 3): said base_rate_fallacy / -4.31; key simpsons_paradox / 5.65. wrong label and number
- base_rate_double_positive (sample 3): said base_rate_fallacy / 0.4; key base_rate_fallacy / 66.03. right label, wrong number
- imbalanced_f1 (sample 3): said imbalanced_accuracy / 36.29; key imbalanced_accuracy / 44.72. right label, wrong number
- test_set_tuning (sample 3): said test_set_tuning / 71.9; key test_set_tuning / 86.75. right label, wrong number
- preprocessing_leakage (sample 3): said preprocessing_leakage / 41.07; key preprocessing_leakage / 43.17. right label, wrong number
- target_leakage_timing (sample 3): said preprocessing_leakage / 7.0; key target_leakage / 5. wrong label and number
- control_legit_lagged_features (sample 3): said preprocessing_leakage / 6.0; key none / 8. wrong label and number
- hard_cohort_censoring (sample 1): said none / 24.87; key right_censoring / 35.64. wrong label and number
- hard_regression_to_mean (sample 1): said none / 13.3; key regression_to_the_mean / 1.7. wrong label and number
- hard_patient_leakage (sample 1): said none / 90.0; key group_leakage / 75.0. wrong label and number
- hard_survivorship (sample 1): said survivorship_bias / 53.8; key survivorship_bias / 51.65. right label, wrong number
- hard_feature_windows (sample 1): said preprocessing_leakage / 10.0; key target_leakage / 8. wrong label and number
- hard_control_cv_tuning (sample 1): said test_set_tuning / 82.31; key none / 86.55. wrong label and number
- hard_cohort_censoring (sample 2): said none / 24.87; key right_censoring / 35.64. wrong label and number
- hard_regression_to_mean (sample 2): said none / 13.3; key regression_to_the_mean / 1.7. wrong label and number
- hard_patient_leakage (sample 2): said none / 90.0; key group_leakage / 75.0. wrong label and number
- hard_survivorship (sample 2): said survivorship_bias / 42.25; key survivorship_bias / 51.65. right label, wrong number
- hard_feature_windows (sample 2): said preprocessing_leakage / 11.0; key target_leakage / 8. wrong label and number
- hard_cohort_censoring (sample 3): said none / 24.87; key right_censoring / 35.64. wrong label and number
- hard_regression_to_mean (sample 3): said none / 13.3; key regression_to_the_mean / 1.7. wrong label and number
- hard_patient_leakage (sample 3): said none / 90.0; key group_leakage / 75.0. wrong label and number
- hard_survivorship (sample 3): said survivorship_bias / 61.5; key survivorship_bias / 51.65. right label, wrong number
- hard_feature_windows (sample 3): said preprocessing_leakage / 11.0; key target_leakage / 8. wrong label and number
- hard_control_cv_tuning (sample 3): said test_set_tuning / 85.87; key none / 86.55. wrong label and number
- hard_patient_leakage_xl (sample 1): said none / 86.05; key group_leakage / 55.56. wrong label and number
- hard_survivorship_xl (sample 1): said survivorship_bias / 39.5; key survivorship_bias / 44.95. right label, wrong number
- hard_patient_leakage_xl (sample 2): said none / 86.05; key group_leakage / 55.56. wrong label and number
- hard_survivorship_xl (sample 2): said survivorship_bias / 37.81; key survivorship_bias / 44.95. right label, wrong number
- hard_patient_leakage_xl (sample 3): said none / 86.05; key group_leakage / 55.56. wrong label and number
- hard_survivorship_xl (sample 3): said survivorship_bias / 56.4; key survivorship_bias / 44.95. right label, wrong number
