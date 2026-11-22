# c2_wind.ps1 -- wind diagnostic (PowerShell 5.1). Criteria written in advance: section C2, summarised with the
# results in results_wind.md (same folder). The input is read through a temporary copy in $env:TEMP.
#
# Inputs:
#   -WindCsv  CastFSR Wind data file wind.csv (columns: date, pred_humidity, pred_pressure, pred_temp, pred_w_dir,
#             pred_w_speed, target, ture_w_speed; 15-minute rows, date format yyyy/M/d H:mm)
# Outputs (-OutDir, default: the folder of this script):
#   c2_results.csv, c2_per_window.csv, c2_log.txt
param(
    [string]$WindCsv,
    [string]$OutDir = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
if (-not $WindCsv) { throw "-WindCsv is required: path to the CastFSR wind.csv" }
if (-not $OutDir) { throw "-OutDir is empty." }
$inv  = [Globalization.CultureInfo]::InvariantCulture
$srcCsv = (Resolve-Path -LiteralPath $WindCsv).ProviderPath
New-Item -ItemType Directory -Force $OutDir | Out-Null; $OutDir = (Resolve-Path -LiteralPath $OutDir).ProviderPath
$scratch = $env:TEMP + '\c2_wind_copy.csv'
Copy-Item $srcCsv $scratch -Force
$logLines = New-Object System.Collections.Generic.List[string]
function Log([string]$msg) { Write-Host $msg; $script:logLines.Add($msg) }

Add-Type -TypeDefinition @"
public static class P0Alt {
    // independent code path: per-window MSE of persistence
    public static double[] Run(double[] tgt, int first, int nWin, int stride, int h, double m, double s) {
        double[] res = new double[nWin];
        for (int w = 0; w < nWin; w++) {
            int o = first + w * stride;
            int k = o - 1; while (double.IsNaN(tgt[k])) k--;
            double zp = (tgt[k] - m) / s;
            double acc = 0;
            for (int j = 0; j < h; j++) { double zt = (tgt[o + j] - m) / s; double d = zp - zt; acc += d * d; }
            res[w] = acc / h;
        }
        return res;
    }
}
"@

# ---- read ----
$allLines = [IO.File]::ReadAllLines($scratch)
Log ('header: ' + $allLines[0])
$nRows = $allLines.Length - 1
$colNames = @('pred_humidity','pred_pressure','pred_temp','pred_w_dir','pred_w_speed','target','ture_w_speed')
$colData = @{}; $colBad = @{}
foreach ($cn in $colNames) { $colData[$cn] = New-Object 'double[]' $nRows; $colBad[$cn] = 0 }
$stamps = New-Object 'DateTime[]' $nRows
$badFieldCount = 0; $badDate = 0
for ($i = 0; $i -lt $nRows; $i++) {
    $f = $allLines[$i + 1].Split(',')
    if ($f.Length -ne 8) { $badFieldCount++ }
    $dt = [DateTime]::MinValue
    if (-not [DateTime]::TryParseExact($f[0], 'yyyy/M/d H:mm', $inv, [Globalization.DateTimeStyles]::None, [ref]$dt)) { $badDate++ }
    $stamps[$i] = $dt
    for ($c = 0; $c -lt 7; $c++) {
        $cn = $colNames[$c]; $v = 0.0
        $tok = ''
        if ($c + 1 -lt $f.Length) { $tok = $f[$c + 1].Trim() }
        if ($tok -ne '' -and [double]::TryParse($tok, [Globalization.NumberStyles]::Float, $inv, [ref]$v) -and -not [double]::IsNaN($v) -and -not [double]::IsInfinity($v)) { $colData[$cn][$i] = $v }
        else { $colData[$cn][$i] = [double]::NaN; $colBad[$cn]++ }
    }
}
$tgt = $colData['target']; $spP = $colData['pred_w_speed']; $spT = $colData['ture_w_speed']
Log ("rows N = $nRows ; rows with !=8 fields = $badFieldCount ; unparsable dates = $badDate")
foreach ($cn in $colNames) { Log ("missing/non-numeric in $cn : " + $colBad[$cn]) }
$gapCount = 0; for ($i = 1; $i -lt $nRows; $i++) { if (($stamps[$i] - $stamps[$i-1]).TotalMinutes -ne 15) { $gapCount++ } }
Log ("non-15-minute steps: $gapCount")
$fmtT = 'yyyy-MM-dd HH:mm'
Log ('first timestamp: ' + $stamps[0].ToString($fmtT, $inv) + ' ; last timestamp: ' + $stamps[$nRows-1].ToString($fmtT, $inv))

# ---- W1 ----
$w1 = ($nRows -eq 48673) -and ($stamps[0] -eq [DateTime]'2020-01-01 00:00') -and ($stamps[$nRows-1] -eq [DateTime]'2021-05-22 00:00')
$w1txt = 'FAIL'; if ($w1) { $w1txt = 'PASS' }
Log ("W1 (N=48673, first 2020-01-01 00:00, last 2021-05-22 00:00): $w1txt")

# ---- split & scaling ----
$nTrain = [int][Math]::Floor(0.7 * $nRows)
Log ("nTrain = $nTrain (rows 0..$($nTrain-1)); last train timestamp " + $stamps[$nTrain-1].ToString($fmtT, $inv))
$sumT = 0.0; $cntT = 0
for ($i = 0; $i -lt $nTrain; $i++) { if (-not [double]::IsNaN($tgt[$i])) { $sumT += $tgt[$i]; $cntT++ } }
$trainMean = $sumT / $cntT
$ssq = 0.0
for ($i = 0; $i -lt $nTrain; $i++) { if (-not [double]::IsNaN($tgt[$i])) { $dv = $tgt[$i] - $trainMean; $ssq += $dv * $dv } }
$std0 = [Math]::Sqrt($ssq / $cntT); $std1 = [Math]::Sqrt($ssq / ($cntT - 1))
Log ("train target mean = $($trainMean.ToString('R',$inv)) ; std ddof0 = $($std0.ToString('R',$inv)) ; std ddof1 = $($std1.ToString('R',$inv)) ; valid train targets = $cntT")

# ---- origins ----
$firstOrigin = -1
$origTs = [DateTime]'2021-02-10 00:00'
for ($i = 0; $i -lt $nRows; $i++) { if ($stamps[$i] -eq $origTs) { $firstOrigin = $i; break } }
$nWin = 101; $stride = 96; $horizon = 96; $lookback = 96
$lastOrigin = $firstOrigin + ($nWin - 1) * $stride
$lastScored = $lastOrigin + $horizon - 1
Log ("first origin idx = $firstOrigin (expected 38976) ts " + $stamps[$firstOrigin].ToString($fmtT, $inv))
Log ("last origin idx = $lastOrigin ts " + $stamps[$lastOrigin].ToString($fmtT, $inv) + " ; last scored idx = $lastScored ts " + $stamps[$lastScored].ToString($fmtT, $inv) + " (expected 2021-05-21 23:45)")
Log ("first origin >= nTrain? " + ($firstOrigin -ge $nTrain) + " ; lookback available (origin-lookback >= 0)? " + ($firstOrigin - $lookback -ge 0))
$ctxOk = ($firstOrigin -eq 38976) -and ($stamps[$lastScored] -eq [DateTime]'2021-05-21 23:45')
$ctxTxt = 'MISMATCH'; if ($ctxOk) { $ctxTxt = 'OK' }
Log ("origin/last-scored check vs criteria: $ctxTxt")

# ---- helpers ----
function Get-Scores($predMat, [double]$mu, [double]$sd) {
    $per = New-Object 'double[]' $nWin; $tot = 0.0
    for ($w = 0; $w -lt $nWin; $w++) {
        $o = $firstOrigin + $w * $stride; $acc = 0.0
        for ($j = 0; $j -lt $horizon; $j++) {
            $zp = ($predMat[$w][$j] - $mu) / $sd; $zt = ($tgt[$o + $j] - $mu) / $sd; $dz = $zp - $zt; $acc += $dz * $dz
        }
        $per[$w] = $acc / $horizon; $tot += $acc
    }
    return @{ mse = $tot / ($nWin * $horizon); per = $per }
}
function Summ($per) {
    $srt = [double[]]($per | Sort-Object); $n = $srt.Length
    if ($n % 2 -eq 1) { $med = $srt[($n-1)/2] } else { $med = ($srt[$n/2-1] + $srt[$n/2]) / 2 }
    return @{ min = $srt[0]; med = $med; max = $srt[$n-1] }
}

# ---- P0 ----
$missFill = @{ P0 = 0; D1 = 0; D2 = 0 }
$predP0 = New-Object 'object[]' $nWin
for ($w = 0; $w -lt $nWin; $w++) {
    $o = $firstOrigin + $w * $stride; $k = $o - 1
    while ([double]::IsNaN($tgt[$k])) { $k--; $missFill.P0++ }
    $arr = New-Object 'double[]' $horizon; for ($j = 0; $j -lt $horizon; $j++) { $arr[$j] = $tgt[$k] }
    $predP0[$w] = $arr
}
$trueNaN = 0; for ($w = 0; $w -lt $nWin; $w++) { $o = $firstOrigin + $w * $stride; for ($j = 0; $j -lt $horizon; $j++) { if ([double]::IsNaN($tgt[$o+$j])) { $trueNaN++ } } }
Log ("NaN targets inside scored windows: $trueNaN")
$sP0 = Get-Scores $predP0 $trainMean $std0
$sP0b = Get-Scores $predP0 $trainMean $std1

# self-check (a): independent C# path
$altPer = [P0Alt]::Run($tgt, $firstOrigin, $nWin, $stride, $horizon, $trainMean, $std0)
$altMse = 0.0; foreach ($pv in $altPer) { $altMse += $pv }; $altMse /= $nWin
$maxDiffPer = 0.0; for ($w = 0; $w -lt $nWin; $w++) { $dd = [Math]::Abs($altPer[$w] - $sP0.per[$w]); if ($dd -gt $maxDiffPer) { $maxDiffPer = $dd } }
$diffMse = [Math]::Abs($altMse - $sP0.mse)
$agree = ($diffMse -lt 1e-9) -and ($maxDiffPer -lt 1e-9)
Log ("self-check (a) P0 z-MSE PowerShell = $($sP0.mse.ToString('R',$inv)) ; C# = $($altMse.ToString('R',$inv)) ; |diff| = $diffMse ; max per-window |diff| = $maxDiffPer ; agree<1e-9: $agree")

# ---- W2 ----
$refBest = 2.291
$w2 = ($sP0.mse -ge $refBest / 3) -and ($sP0.mse -le $refBest * 3)
$w2txt = 'FAIL'; if ($w2) { $w2txt = 'PASS' }
Log ("P0 z-MSE (ddof0) = $($sP0.mse.ToString('F4',$inv)) ; W2 range [$(($refBest/3).ToString('F4',$inv)), $(($refBest*3).ToString('F4',$inv))] : $w2txt")

# ---- W3 alignment ----
function Pearson($a, $b, [int]$lag) {
    $n = 0; $sa = 0.0; $sb = 0.0
    for ($t = 0; $t -lt $nTrain; $t++) {
        $u = $t + $lag; if ($u -lt 0 -or $u -ge $nTrain) { continue }
        $x = $a[$t]; $y = $b[$u]; if ([double]::IsNaN($x) -or [double]::IsNaN($y)) { continue }
        $n++; $sa += $x; $sb += $y
    }
    $ma = $sa / $n; $mb = $sb / $n; $sab = 0.0; $saa = 0.0; $sbb = 0.0
    for ($t = 0; $t -lt $nTrain; $t++) {
        $u = $t + $lag; if ($u -lt 0 -or $u -ge $nTrain) { continue }
        $x = $a[$t]; $y = $b[$u]; if ([double]::IsNaN($x) -or [double]::IsNaN($y)) { continue }
        $sab += ($x-$ma)*($y-$mb); $saa += ($x-$ma)*($x-$ma); $sbb += ($y-$mb)*($y-$mb)
    }
    return $sab / [Math]::Sqrt($saa * $sbb)
}
$corrTrue = @{}; $corrPred = @{}
for ($lg = -8; $lg -le 8; $lg++) { $corrTrue[$lg] = Pearson $tgt $spT $lg; $corrPred[$lg] = Pearson $tgt $spP $lg }
Log 'Alignment table: corr(target[t], speed[t+lag]) on training part'
Log 'lag, ture_w_speed, pred_w_speed'
$bestTrue = -99.0; $bestTrueLag = 0; $bestPred = -99.0; $bestPredLag = 0
for ($lg = -8; $lg -le 8; $lg++) {
    Log (("{0,3}, {1}, {2}" -f $lg, $corrTrue[$lg].ToString('F5',$inv), $corrPred[$lg].ToString('F5',$inv)))
    if ($corrTrue[$lg] -gt $bestTrue) { $bestTrue = $corrTrue[$lg]; $bestTrueLag = $lg }
    if ($corrPred[$lg] -gt $bestPred) { $bestPred = $corrPred[$lg]; $bestPredLag = $lg }
}
$w3 = ([Math]::Abs($bestTrueLag) -le 1)
$w3txt = 'FAIL'; if ($w3) { $w3txt = 'PASS' }
Log ("argmax lag ture_w_speed = $bestTrueLag (corr $($bestTrue.ToString('F5',$inv))) ; argmax lag pred_w_speed = $bestPredLag (corr $($bestPred.ToString('F5',$inv)))")
Log ("W3 (ture_w_speed argmax lag in {-1,0,1}): $w3txt")

# ---- power curves ----
function Build-Curve($spd) {
    $bsum = @{}; $bcnt = @{}
    for ($i = 0; $i -lt $nTrain; $i++) {
        $x = $spd[$i]; $y = $tgt[$i]; if ([double]::IsNaN($x) -or [double]::IsNaN($y)) { continue }
        $b = [int][Math]::Floor($x / 0.5)
        if ($bsum.ContainsKey($b)) { $bsum[$b] += $y; $bcnt[$b]++ } else { $bsum[$b] = $y; $bcnt[$b] = 1 }
    }
    $bmean = @{}; foreach ($b in $bsum.Keys) { $bmean[$b] = $bsum[$b] / $bcnt[$b] }
    return @{ mean = $bmean; cnt = $bcnt }
}
function Curve-Value($curve, [int]$b) {
    if ($curve.mean.ContainsKey($b)) { return $curve.mean[$b] }
    for ($dd2 = 1; $dd2 -lt 100000; $dd2++) {   # nearest non-empty bin, ties -> lower bin (check b-d first)
        if ($curve.mean.ContainsKey($b - $dd2)) { return $curve.mean[$b - $dd2] }
        if ($curve.mean.ContainsKey($b + $dd2)) { return $curve.mean[$b + $dd2] }
    }
    throw 'empty curve'
}
function Predict-Curve($curve, $spd, [string]$tag) {
    $pm = New-Object 'object[]' $nWin; $emptyHit = 0
    for ($w = 0; $w -lt $nWin; $w++) {
        $o = $firstOrigin + $w * $stride; $arr = New-Object 'double[]' $horizon
        for ($j = 0; $j -lt $horizon; $j++) {
            $k = $o + $j; $x = $spd[$k]
            if ([double]::IsNaN($x)) {
                $script:missFill[$tag]++
                while ([double]::IsNaN($x)) { $k--; $x = $spd[$k] }
            }
            $b = [int][Math]::Floor($x / 0.5)
            if (-not $curve.mean.ContainsKey($b)) { $emptyHit++ }
            $arr[$j] = Curve-Value $curve $b
        }
        $pm[$w] = $arr
    }
    return @{ pred = $pm; emptyHit = $emptyHit }
}
$curveD1 = Build-Curve $spP; $curveD2 = Build-Curve $spT
function Curve-Info($curve, $name) {
    $ks = [int[]]($curve.mean.Keys | Sort-Object)
    $lo = $ks[0]; $hi = $ks[$ks.Length - 1]
    $sparse = @($curve.cnt.Keys | Where-Object { $curve.cnt[$_] -lt 5 }).Count
    Log ("$name : non-empty bins = $($ks.Length) ; bin range [$lo .. $hi] = speed [$($lo*0.5) .. $(($hi+1)*0.5)) ; empty bins inside range = $(($hi - $lo + 1) - $ks.Length) ; bins with <5 train rows = $sparse")
}
Curve-Info $curveD1 'D1 (pred_w_speed)'; Curve-Info $curveD2 'D2 (ture_w_speed)'
$pd1 = Predict-Curve $curveD1 $spP 'D1'; $pd2 = Predict-Curve $curveD2 $spT 'D2'
Log ("horizon points whose bin was empty in training (filled by nearest bin): D1 = $($pd1.emptyHit), D2 = $($pd2.emptyHit)")
Log ("missing-value fills used: P0 = $($missFill.P0), D1 = $($missFill.D1), D2 = $($missFill.D2)")
$sD1 = Get-Scores $pd1.pred $trainMean $std0; $sD2 = Get-Scores $pd2.pred $trainMean $std0
$sD1b = Get-Scores $pd1.pred $trainMean $std1; $sD2b = Get-Scores $pd2.pred $trainMean $std1

# ---- results ----
$rows = @()
foreach ($e in @(@('P0',$sP0,$sP0b), @('D1',$sD1,$sD1b), @('D2',$sD2,$sD2b))) {
    $sm = Summ $e[1].per
    $rows += [pscustomobject]@{ model = $e[0]; zmse_ddof0 = $e[1].mse.ToString('R',$inv); zmse_ddof1 = $e[2].mse.ToString('R',$inv); win_min = $sm.min.ToString('R',$inv); win_median = $sm.med.ToString('R',$inv); win_max = $sm.max.ToString('R',$inv) }
    Log (("RESULT {0}: z-MSE(ddof0) = {1} ; z-MSE(ddof1) = {2} ; per-window MSE min/median/max = {3} / {4} / {5}" -f $e[0], $e[1].mse.ToString('F4',$inv), $e[2].mse.ToString('F4',$inv), $sm.min.ToString('F4',$inv), $sm.med.ToString('F4',$inv), $sm.max.ToString('F4',$inv)))
}
$rows | Export-Csv -Path (Join-Path $OutDir 'c2_results.csv') -NoTypeInformation -Encoding UTF8
$pw = for ($w = 0; $w -lt $nWin; $w++) { [pscustomobject]@{ window = $w; origin_idx = $firstOrigin + $w*$stride; origin_ts = $stamps[$firstOrigin + $w*$stride].ToString($fmtT, $inv); P0 = $sP0.per[$w].ToString('R',$inv); D1 = $sD1.per[$w].ToString('R',$inv); D2 = $sD2.per[$w].ToString('R',$inv) } }
$pw | Export-Csv -Path (Join-Path $OutDir 'c2_per_window.csv') -NoTypeInformation -Encoding UTF8

# ---- verdict ----
$m2 = $sD2.mse
Log ("D1 vs D2 (descriptive): D1 = $($sD1.mse.ToString('F4',$inv)), D2 = $($m2.ToString('F4',$inv)), D1 - D2 = $(($sD1.mse - $m2).ToString('F4',$inv))")
Log ("Gates: W1=$w1 W2=$w2 W3=$w3")
if (-not $w1) { $verdict = 'W1 failed: judgment downgraded to description' }
elseif (-not $w3) { $verdict = 'W3 failed: D2 not judged' }
elseif (-not $w2) { $verdict = 'W2 failed: magnitude does not match' }
elseif ($m2 -le 1.596) { $verdict = 'm2 <= 1.596 : SUPPORTED' }
elseif ($m2 -lt 2.291) { $verdict = '1.596 < m2 < 2.291 : PARTIALLY SUPPORTED' }
else { $verdict = 'm2 >= 2.291 : NOT SUPPORTED' }
Log ("VERDICT: m2 = $($m2.ToString('F4',$inv)) -> $verdict")
[IO.File]::WriteAllLines((Join-Path $OutDir 'c2_log.txt'), $logLines.ToArray())
