# MemCast EPF: day-aligned sensitivity of "published LEAR/DNN vs MemCast's reported MSE" (2026-11-15).
# POST HOC sensitivity; the decision rule below was written before running and is the same as the rule of the
# all-placement analysis:
#   among placements in a subset, if LEAR-Ens MSE < MemCast's reported MSE in >= 95% -> robust; <= 5% -> reversed; else placement-dependent.
# Family (unchanged): 30 windows of 24 h, stride s in {24,48,72,96} h, every start hour such that all windows lie inside the test
# segment = rows [int(0.8*14496), 14496) of the last 14,496 rows of the market.
# New in this script:
#   * DAY-ALIGNED subset: placements whose first window starts at 00:00 (all strides are multiples of 24 h, so every window then
#     covers exactly one delivery day). Each window then uses a single day-ahead issuance of the published forecast, i.e. the
#     benchmark does not use a later forecast origin than a day-ahead window of the reconstructed protocol.
#   * counts before and after the scale filter (SN-1d MSE within a factor of 3 of the paper's best non-LLM baseline), per stride,
#     for ALL placements and for the DAY-ALIGNED subset; LEAR/MemCast ratio median and 5th/95th percentiles.
# Availability convention (not verified with issuance timestamps): the epftoolbox benchmark recalibrates daily on data before the
# delivery day and uses day-ahead load/generation forecasts, per Lago et al. (2021). This is the published protocol, stated as such.
#
# Inputs, for each market M in NP, PJM, BE, FR, DE:
#   -RawDir (alias -DataRoot)        folder with <M>\<M>.csv (epftoolbox day-ahead data; column 0 = timestamp)
#   -FcDir  (alias -LearForecastDir) folder with Forecasts_<M>_DNN_LEAR_ensembles.csv (epftoolbox published forecasts)
# Outputs (-OutDir, default: the folder of this script):
#   dayaligned_summary.csv, dayaligned_placements.csv
param(
    [Alias('LearForecastDir')][string]$FcDir,
    [Alias('DataRoot')][string]$RawDir,
    [string]$OutDir = $PSScriptRoot
)
if (-not $FcDir) { throw "-FcDir (alias -LearForecastDir) is required: folder with Forecasts_<M>_DNN_LEAR_ensembles.csv" }
if (-not $RawDir) { throw "-RawDir (alias -DataRoot) is required: folder with <M>\<M>.csv" }
if (-not $OutDir) { throw "-OutDir is empty." }
$FcDir = (Resolve-Path -LiteralPath $FcDir).ProviderPath; $RawDir = (Resolve-Path -LiteralPath $RawDir).ProviderPath
$paperVals = @{ "NP" = @(36.871, 55.857); "PJM" = @(30.238, 63.342); "BE" = @(756.308, 887.125); "FR" = @(756.981, 876.179); "DE" = @(210.445, 290.971) }
$rowsOut = New-Object System.Collections.ArrayList
$placeOut = New-Object System.Collections.ArrayList
$textOut = New-Object System.Collections.ArrayList
foreach ($mkt in "NP", "PJM", "BE", "FR", "DE") {
    $rawLines = [IO.File]::ReadAllLines("$RawDir\$mkt\$mkt.csv"); $nAll = $rawLines.Length - 1; $offRow = $nAll - 14496; $eRow = [int][math]::Floor(0.8 * 14496)
    $segStart = $rawLines[$offRow + $eRow + 1].Split(',')[0]; $segEnd = $rawLines[$nAll].Split(',')[0]
    $fcLines = [IO.File]::ReadAllLines("$FcDir\Forecasts_${mkt}_DNN_LEAR_ensembles.csv"); $hdr = $fcLines[0].Split(',')
    $iReal = [array]::IndexOf($hdr, "Real price"); $iDnn = [array]::IndexOf($hdr, "DNN Ensemble"); $iLear = [array]::IndexOf($hdr, "LEAR Ensemble")
    $nFc = $fcLines.Length - 1
    $tsArr = New-Object string[] $nFc; $errL = New-Object double[] $nFc; $errD = New-Object double[] $nFc; $yArr = New-Object double[] $nFc
    for ($i = 1; $i -lt $fcLines.Length; $i++) { $parts = $fcLines[$i].Split(','); $tsArr[$i - 1] = $parts[0]; $yv = [double]$parts[$iReal]; $yArr[$i - 1] = $yv; $errL[$i - 1] = ([double]$parts[$iLear] - $yv) * ([double]$parts[$iLear] - $yv); $errD[$i - 1] = ([double]$parts[$iDnn] - $yv) * ([double]$parts[$iDnn] - $yv) }
    $aIdx = [array]::IndexOf($tsArr, $segStart); $bIdx = [array]::IndexOf($tsArr, $segEnd)
    if ($aIdx -lt 24 -or $bIdx -lt 0) { [void]$textOut.Add("$mkt : test segment $segStart .. $segEnd not covered by the forecast file"); continue }
    $segLen = $bIdx - $aIdx + 1
    $blockL = New-Object double[] $segLen; $blockD = New-Object double[] $segLen; $blockS = New-Object double[] $segLen
    for ($t = 0; $t + 24 -le $segLen; $t++) { $sumL = 0.0; $sumD = 0.0; $sumS = 0.0; for ($h = 0; $h -lt 24; $h++) { $k = $aIdx + $t + $h; $sumL += $errL[$k]; $sumD += $errD[$k]; $e1 = $yArr[$k] - $yArr[$k - 24]; $sumS += $e1 * $e1 }; $blockL[$t] = $sumL; $blockD[$t] = $sumD; $blockS[$t] = $sumS }
    $pMem = $paperVals[$mkt][0]; $pBest = $paperVals[$mkt][1]
    foreach ($subsetName in @('all', 'day_aligned')) {
        foreach ($strideVal in @(24, 48, 72, 96, 0)) {
            $nPlace = 0; $nMatched = 0; $nLearWinM = 0; $nDnnWinM = 0; $nLearWinAll = 0; $ratioList = New-Object System.Collections.Generic.List[double]
            foreach ($sv in @(24, 48, 72, 96)) {
                if ($strideVal -ne 0 -and $sv -ne $strideVal) { continue }
                for ($st = 0; $st + 29 * $sv + 24 -le $segLen; $st++) {
                    $hourText = $tsArr[$aIdx + $st]
                    $isMidnight = ([datetime]::Parse($hourText, [Globalization.CultureInfo]::InvariantCulture)).Hour -eq 0
                    if ($subsetName -eq 'day_aligned' -and -not $isMidnight) { continue }
                    $accL = 0.0; $accD = 0.0; $accS = 0.0
                    for ($w = 0; $w -lt 30; $w++) { $tt = $st + $w * $sv; $accL += $blockL[$tt]; $accD += $blockD[$tt]; $accS += $blockS[$tt] }
                    $mseL = $accL / 720; $mseD = $accD / 720; $mseS = $accS / 720; $nPlace++
                    if ($mseL -lt $pMem) { $nLearWinAll++ }
                    $scaleR = $mseS / $pBest; $inScale = ($scaleR -ge (1 / 3) -and $scaleR -le 3)
                    if ($inScale) { $nMatched++; if ($mseL -lt $pMem) { $nLearWinM++ }; if ($mseD -lt $pMem) { $nDnnWinM++ }; $ratioList.Add($mseL / $pMem) }
                    if ($subsetName -eq 'day_aligned' -and $strideVal -eq 0) { [void]$placeOut.Add([pscustomobject]@{ market = $mkt; stride = $sv; first_window_start = $hourText; sn1d_mse = $mseS; scale_ok = $inScale; lear_mse = $mseL; dnn_mse = $mseD; memcast_reported = $pMem; lear_over_memcast = $mseL / $pMem }) }
                }
            }
            $ratioList.Sort()
            $medR = if ($ratioList.Count) { $ratioList[[int]($ratioList.Count / 2)] } else { [double]::NaN }
            $p05 = if ($ratioList.Count) { $ratioList[[int](0.05 * ($ratioList.Count - 1))] } else { [double]::NaN }
            $p95 = if ($ratioList.Count) { $ratioList[[int](0.95 * ($ratioList.Count - 1))] } else { [double]::NaN }
            $shareM = if ($nMatched) { $nLearWinM / $nMatched } else { [double]::NaN }
            $verdict = if ($nMatched -eq 0) { 'n/a' } elseif ($shareM -ge 0.95) { 'robust' } elseif ($shareM -le 0.05) { 'reversed' } else { 'placement-dependent' }
            $strideLabel = if ($strideVal -eq 0) { 'all strides' } else { "$strideVal h" }
            [void]$rowsOut.Add([pscustomobject]@{ market = $mkt; subset = $subsetName; stride = $strideLabel; placements = $nPlace; scale_matched = $nMatched; lear_win_share_matched = $shareM; lear_win_share_all = $(if ($nPlace) { $nLearWinAll / $nPlace } else { [double]::NaN }); dnn_win_share_matched = $(if ($nMatched) { $nDnnWinM / $nMatched } else { [double]::NaN }); ratio_p05 = $p05; ratio_median = $medR; ratio_p95 = $p95; verdict = $verdict })
        }
    }
}
New-Item -ItemType Directory -Force $OutDir | Out-Null
$rowsOut | Export-Csv (Join-Path $OutDir "dayaligned_summary.csv") -NoTypeInformation -Encoding UTF8
$placeOut | Export-Csv (Join-Path $OutDir "dayaligned_placements.csv") -NoTypeInformation -Encoding UTF8
$rowsOut | Where-Object { $_.stride -eq 'all strides' } | Format-Table market, subset, placements, scale_matched, @{n='LEAR<MemCast (matched)';e={'{0:P1}' -f $_.lear_win_share_matched}}, @{n='median ratio';e={'{0:N2}' -f $_.ratio_median}}, @{n='p95';e={'{0:N2}' -f $_.ratio_p95}}, verdict -AutoSize
$textOut
