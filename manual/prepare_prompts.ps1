Set-Location C:\Users\Badrw\Projects\auditbench
Remove-Item manual\prompts\*.txt
$order = "hard_cohort_censoring","hard_regression_to_mean","hard_patient_leakage","hard_survivorship","hard_feature_windows","hard_control_cv_tuning","hard_patient_leakage_xl","hard_survivorship_xl","hard_control_post_treatment"
python run_eval.py --export-manual --tasks ($order -join ",") | Select-Object -First 1
$i = 1
foreach ($t in $order) {
    Rename-Item "manual\prompts\$t.txt" ("{0}_{1}.txt" -f $i, $t)
    $f = "manual\claude-opus-5.5_chat\{0}__1.txt" -f $t
    if (-not (Test-Path $f)) { New-Item -ItemType File $f | Out-Null }
    $i++
}
Get-ChildItem manual\prompts | Select-Object -ExpandProperty Name
