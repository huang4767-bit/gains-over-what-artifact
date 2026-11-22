# CastFSR EPF protocol: published epftoolbox LEAR/DNN and seasonal naive on CastFSR's 60 windows, z-scored with
# training-partition stats. Criteria written in advance: criteria_castfsr_lear.md (same folder).
# PowerShell 5.1. Variable names deliberately distinct (PowerShell is case-insensitive).
#
# Inputs (give either -InDir, or both -DataRoot and -LearForecastDir), for each market M in BE, DE, FR, NP, PJM:
#   -InDir            folder with raw_<M>.csv and fc_<M>.csv, where
#                       raw_<M>.csv = copy of <DataRoot>\<M>\<M>.csv
#                       fc_<M>.csv  = copy of <LearForecastDir>\Forecasts_<M>_DNN_LEAR_ensembles.csv
#   -DataRoot         folder with <M>\<M>.csv (epftoolbox day-ahead data; column 0 = timestamp, column 1 = price)
#   -LearForecastDir  folder with Forecasts_<M>_DNN_LEAR_ensembles.csv (epftoolbox published forecasts; columns
#                     "Real price", "LEAR Ensemble", "DNN Ensemble")
# Outputs:
#   -OutDir (default: the folder of this script)\castfsr_lear_results.csv
param(
    [string]$InDir,
    [string]$DataRoot,
    [string]$LearForecastDir,
    [string]$OutDir = $PSScriptRoot
)
if ($InDir) { $InDir = (Resolve-Path -LiteralPath $InDir).ProviderPath }
elseif ($DataRoot -and $LearForecastDir) { $DataRoot = (Resolve-Path -LiteralPath $DataRoot).ProviderPath; $LearForecastDir = (Resolve-Path -LiteralPath $LearForecastDir).ProviderPath }
else { throw "Give -InDir, or both -DataRoot and -LearForecastDir (see the header of this script)." }
if (-not $OutDir) { throw "-OutDir is empty." }

$expDates = @{
  "BE"  = @("2015-05-08 00:00:00", "2016-07-07 00:00:00", "2016-09-04 00:00:00", "2016-12-31 23:00:00")
  "FR"  = @("2015-05-08 00:00:00", "2016-07-07 00:00:00", "2016-09-04 00:00:00", "2016-12-31 23:00:00")
  "DE"  = @("2016-05-07 00:00:00", "2017-07-07 00:00:00", "2017-09-04 00:00:00", "2017-12-31 23:00:00")
  "NP"  = @("2017-04-30 00:00:00", "2018-06-30 00:00:00", "2018-08-28 00:00:00", "2018-12-24 23:00:00")
  "PJM" = @("2017-04-30 00:00:00", "2018-06-30 00:00:00", "2018-08-28 00:00:00", "2018-12-24 23:00:00") }
# Table 1 (v3): CastFSR-Zero MSE, MAE; CastFSR-R1 MSE, MAE; best non-LLM baseline MSE
$tab1 = @{
  "BE"  = @(0.960, 0.386, 0.927, 0.375, 1.140)
  "DE"  = @(0.393, 0.408, 0.386, 0.405, 0.798)
  "FR"  = @(3.939, 0.501, 4.032, 0.502, 4.786)
  "NP"  = @(0.221, 0.277, 0.172, 0.247, 0.301)
  "PJM" = @(0.140, 0.268, 0.133, 0.260, 0.180) }

$nSlice = 14496; $nTrain = 10224; $nTrVal = 11640; $nWin = 60; $hzn = 24; $strd = 48
$summary = New-Object System.Collections.Generic.List[object]

foreach ($mkt in "BE", "DE", "FR", "NP", "PJM") {
  if ($InDir) { $rawPath = Join-Path $InDir "raw_$mkt.csv"; $fcPath = Join-Path $InDir "fc_$mkt.csv" }
  else { $rawPath = Join-Path $DataRoot "$mkt\$mkt.csv"; $fcPath = Join-Path $LearForecastDir "Forecasts_${mkt}_DNN_LEAR_ensembles.csv" }
  $rawLinesArr = [IO.File]::ReadAllLines($rawPath); $nRawRows = $rawLinesArr.Length - 1; $sliceOff = $nRawRows - $nSlice
  $sliceTs = New-Object string[] $nSlice; $slicePx = New-Object double[] $nSlice
  for ($ii = 0; $ii -lt $nSlice; $ii++) { $parts = $rawLinesArr[$sliceOff + 1 + $ii].Split(','); $sliceTs[$ii] = $parts[0]; $slicePx[$ii] = [double]::Parse($parts[1], [Globalization.CultureInfo]::InvariantCulture) }
  # G1
  $g1 = ($sliceTs[0] -eq $expDates[$mkt][0]) -and ($sliceTs[$nTrain] -eq $expDates[$mkt][1]) -and ($sliceTs[$nTrVal] -eq $expDates[$mkt][2]) -and ($sliceTs[$nSlice - 1] -eq $expDates[$mkt][3])
  # sigma variants
  $sigmaOf = { param($cnt) $acc = 0.0; for ($jj = 0; $jj -lt $cnt; $jj++) { $acc += $slicePx[$jj] }; $mu = $acc / $cnt; $ss = 0.0; for ($jj = 0; $jj -lt $cnt; $jj++) { $dv = $slicePx[$jj] - $mu; $ss += $dv * $dv }; @($mu, [math]::Sqrt($ss / $cnt), [math]::Sqrt($ss / ($cnt - 1))) }
  $stTrain = & $sigmaOf $nTrain; $stTrVal = & $sigmaOf $nTrVal; $stFull = & $sigmaOf $nSlice
  $sdMain = $stTrain[1]
  # forecast file
  $fcLinesArr = [IO.File]::ReadAllLines($fcPath); $fcHdr = $fcLinesArr[0].Split(',')
  $colReal = [array]::IndexOf($fcHdr, "Real price"); $colLear = [array]::IndexOf($fcHdr, "LEAR Ensemble"); $colDnn = [array]::IndexOf($fcHdr, "DNN Ensemble")
  $fcMap = @{}
  for ($ii = 1; $ii -lt $fcLinesArr.Length; $ii++) { $fp = $fcLinesArr[$ii].Split(','); $fcMap[$fp[0]] = @([double]::Parse($fp[$colReal], [Globalization.CultureInfo]::InvariantCulture), [double]::Parse($fp[$colLear], [Globalization.CultureInfo]::InvariantCulture), [double]::Parse($fp[$colDnn], [Globalization.CultureInfo]::InvariantCulture)) }
  # windows: raw-unit squared/abs error sums per window
  $winSqL = New-Object double[] $nWin; $winSqD = New-Object double[] $nWin; $winSqS1 = New-Object double[] $nWin; $winSqS7 = New-Object double[] $nWin
  $absL = 0.0; $absD = 0.0; $absS1 = 0.0; $absS7 = 0.0; $missing = 0; $maxTruthDiff = 0.0; $firstOrigin = ""; $lastScored = ""
  for ($kk = 0; $kk -lt $nWin; $kk++) {
    for ($hh = 0; $hh -lt $hzn; $hh++) {
      $ix = $nTrVal + $strd * $kk + $hh; $tsNow = $sliceTs[$ix]; $yTrue = $slicePx[$ix]
      if ($kk -eq 0 -and $hh -eq 0) { $firstOrigin = $tsNow }; $lastScored = $tsNow
      if (-not $fcMap.ContainsKey($tsNow)) { $missing++; continue }
      $rec = $fcMap[$tsNow]; $maxTruthDiff = [math]::Max($maxTruthDiff, [math]::Abs($rec[0] - $yTrue))
      $eL = $rec[1] - $yTrue; $eD = $rec[2] - $yTrue; $eS1 = $slicePx[$ix - 24] - $yTrue; $eS7 = $slicePx[$ix - 168] - $yTrue
      $winSqL[$kk] += $eL * $eL; $winSqD[$kk] += $eD * $eD; $winSqS1[$kk] += $eS1 * $eS1; $winSqS7[$kk] += $eS7 * $eS7
      $absL += [math]::Abs($eL); $absD += [math]::Abs($eD); $absS1 += [math]::Abs($eS1); $absS7 += [math]::Abs($eS7)
    } }
  $nScored = $nWin * $hzn
  $rawMseL = ($winSqL | Measure-Object -Sum).Sum / $nScored; $rawMseD = ($winSqD | Measure-Object -Sum).Sum / $nScored
  $rawMseS1 = ($winSqS1 | Measure-Object -Sum).Sum / $nScored; $rawMseS7 = ($winSqS7 | Measure-Object -Sum).Sum / $nScored
  $var0 = $sdMain * $sdMain
  $zL = $rawMseL / $var0; $zD = $rawMseD / $var0; $zS1 = $rawMseS1 / $var0; $zS7 = $rawMseS7 / $var0
  $zMaeL = $absL / $nScored / $sdMain; $zMaeD = $absD / $nScored / $sdMain; $zMaeS1 = $absS1 / $nScored / $sdMain; $zMaeS7 = $absS7 / $nScored / $sdMain
  $t1 = $tab1[$mkt]; $cStar = [math]::Min($t1[0], $t1[2]); $cStarMae = [math]::Min($t1[1], $t1[3]); $bestBase = $t1[4]
  $g2 = ($maxTruthDiff -le 1e-6); $g3 = ($missing -eq 0); $sn1Ratio = $zS1 / $bestBase; $g4 = ($sn1Ratio -ge (1.0 / 3) -and $sn1Ratio -le 3)
  $rLear = $zL / $cStar
  $cat = if ($rLear -le 0.90) { "benchmark clearly better" } elseif ($rLear -ge 1.10) { "CastFSR clearly better" } else { "comparable" }
  # sigma sensitivity
  $catFor = { param($sdv) $rr = ($rawMseL / ($sdv * $sdv)) / $cStar; if ($rr -le 0.90) { "B" } elseif ($rr -ge 1.10) { "C" } else { "=" } }
  $catTrain = & $catFor $stTrain[1]; $catTrVal = & $catFor $stTrVal[1]; $catFull = & $catFor $stFull[1]
  # bootstrap over windows (descriptive)
  $rng = New-Object System.Random 0; $bootVals = New-Object double[] 10000
  for ($bb = 0; $bb -lt 10000; $bb++) { $sacc = 0.0; for ($ww = 0; $ww -lt $nWin; $ww++) { $sacc += $winSqL[$rng.Next($nWin)] }; $bootVals[$bb] = $sacc / $nScored / $var0 }
  [array]::Sort($bootVals); $bLo = $bootVals[249]; $bHi = $bootVals[9749]
  $summary.Add([pscustomobject]@{
    Market = $mkt; G1 = $g1; G2 = $g2; G3 = $g3; G4 = $g4; FirstOrigin = $firstOrigin; LastScored = $lastScored; MaxTruthDiff = $maxTruthDiff
    SdTrain0 = [math]::Round($stTrain[1], 4); SdTrain1 = [math]::Round($stTrain[2], 4); SdTrVal = [math]::Round($stTrVal[1], 4); SdFull = [math]::Round($stFull[1], 4)
    zMSE_LEAR = [math]::Round($zL, 4); zMSE_DNN = [math]::Round($zD, 4); zMSE_SN1 = [math]::Round($zS1, 4); zMSE_SN7 = [math]::Round($zS7, 4)
    zMAE_LEAR = [math]::Round($zMaeL, 4); zMAE_DNN = [math]::Round($zMaeD, 4); zMAE_SN1 = [math]::Round($zMaeS1, 4); zMAE_SN7 = [math]::Round($zMaeS7, 4)
    CStarMSE = $cStar; CStarMAE = $cStarMae; BestNonLLM = $bestBase
    r_LEAR = [math]::Round($rLear, 3); r_DNN = [math]::Round($zD / $cStar, 3); r_SN1 = [math]::Round($zS1 / $cStar, 3); r_SN7 = [math]::Round($zS7 / $cStar, 3)
    rMAE_LEAR = [math]::Round($zMaeL / $cStarMae, 3); rMAE_DNN = [math]::Round($zMaeD / $cStarMae, 3)
    LEAR_over_BestNonLLM = [math]::Round($zL / $bestBase, 3); SN1_over_BestNonLLM = [math]::Round($sn1Ratio, 3)
    Category = $cat; CatSigma_Train_TrVal_Full = "$catTrain/$catTrVal/$catFull"; Boot95_LEAR = ("{0:N4}..{1:N4}" -f $bLo, $bHi) })
}
$summary | Format-List
New-Item -ItemType Directory -Force $OutDir | Out-Null
$summary | Export-Csv -NoTypeInformation -Encoding UTF8 -Path (Join-Path $OutDir "castfsr_lear_results.csv")
