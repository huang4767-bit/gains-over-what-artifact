# Independent re-computation of the castfsr_lear.ps1 numbers (separate code path, same inputs): published epftoolbox
# LEAR/DNN and seasonal naive (1 day, 7 days) on CastFSR's 60 EPF test windows, z-scored with training statistics.
#
# Inputs (give either -InDir, or both -DataRoot and -LearForecastDir), for each market M in BE, DE, FR, NP, PJM:
#   -InDir            folder with raw_<M>.csv and fc_<M>.csv, where
#                       raw_<M>.csv = copy of <DataRoot>\<M>\<M>.csv
#                       fc_<M>.csv  = copy of <LearForecastDir>\Forecasts_<M>_DNN_LEAR_ensembles.csv
#   -DataRoot         folder with <M>\<M>.csv (epftoolbox day-ahead data; column 0 = timestamp, column 1 = price)
#   -LearForecastDir  folder with Forecasts_<M>_DNN_LEAR_ensembles.csv (epftoolbox published forecasts)
# Outputs:
#   -OutDir (default: the folder of this script)\indep.csv
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
$inv=[System.Globalization.CultureInfo]::InvariantCulture
$cStar=@{BE=0.927;DE=0.386;FR=3.939;NP=0.172;PJM=0.133}
function PopStd($arr){ $n=$arr.Count; $sm=0.0; foreach($v in $arr){$sm+=$v}; $mu=$sm/$n; $ss=0.0; foreach($v in $arr){$ss+=($v-$mu)*($v-$mu)}; [math]::Sqrt($ss/$n) }
$out=@()
foreach($mk in 'BE','DE','FR','NP','PJM'){
  if($InDir){ $rawPath=Join-Path $InDir ('raw_'+$mk+'.csv'); $fcPath=Join-Path $InDir ('fc_'+$mk+'.csv') }
  else{ $rawPath=Join-Path $DataRoot ($mk+'\'+$mk+'.csv'); $fcPath=Join-Path $LearForecastDir ('Forecasts_'+$mk+'_DNN_LEAR_ensembles.csv') }
  $rawLines=[System.IO.File]::ReadAllLines($rawPath)
  $rawBody=$rawLines[1..($rawLines.Length-1)] | ?{$_.Trim().Length -gt 0}
  $nAll=$rawBody.Count
  $sliceLines=$rawBody[($nAll-14496)..($nAll-1)]
  $tsArr=New-Object string[] 14496; $pxArr=New-Object double[] 14496
  for($i=0;$i -lt 14496;$i++){ $p=$sliceLines[$i].Split(','); $tsArr[$i]=$p[0]; $pxArr[$i]=[double]::Parse($p[1],$inv) }
  $trainPx=$pxArr[0..10223]
  $sigTr=PopStd $trainPx; $sigTV=PopStd $pxArr[0..11639]; $sigAll=PopStd $pxArr
  $iTest=14496-2856
  Write-Host ("{0} rawrows={1} trainStart={2} valStart={3} testStart={4} testEnd={5} testStartIdx={6}" -f $mk,$nAll,$tsArr[0],$tsArr[10224],$tsArr[$iTest],$tsArr[14495],$iTest)
  # forecast file
  $fcLines=[System.IO.File]::ReadAllLines($fcPath)
  $hdr=$fcLines[0].Split(',')
  $cReal=[array]::IndexOf($hdr,'Real price'); $cLear=[array]::IndexOf($hdr,'LEAR Ensemble'); $cDnn=[array]::IndexOf($hdr,'DNN Ensemble')
  $fcReal=@{};$fcLear=@{};$fcDnn=@{}
  for($i=1;$i -lt $fcLines.Length;$i++){ if($fcLines[$i].Trim().Length -eq 0){continue}; $p=$fcLines[$i].Split(','); $k=$p[0].Trim(); $fcReal[$k]=[double]::Parse($p[$cReal],$inv); $fcLear[$k]=[double]::Parse($p[$cLear],$inv); $fcDnn[$k]=[double]::Parse($p[$cDnn],$inv) }
  $sumL=0.0;$sumD=0.0;$sum1=0.0;$sum7=0.0;$aL=0.0;$aD=0.0;$a1=0.0;$a7=0.0;$cnt=0;$missing=0;$maxDiff=0.0
  $sumLtv=0.0;$sumLall=0.0
  for($w=0;$w -lt 60;$w++){
    for($h=0;$h -lt 24;$h++){
      $ix=$iTest+48*$w+$h; $key=$tsArr[$ix]; $truth=$pxArr[$ix]
      if(-not $fcLear.ContainsKey($key)){$missing++;continue}
      $dd=[math]::Abs($truth-$fcReal[$key]); if($dd -gt $maxDiff){$maxDiff=$dd}
      $eL=$fcLear[$key]-$truth; $eD=$fcDnn[$key]-$truth; $e1=$pxArr[$ix-24]-$truth; $e7=$pxArr[$ix-168]-$truth
      $sumL+=$eL*$eL;$sumD+=$eD*$eD;$sum1+=$e1*$e1;$sum7+=$e7*$e7
      $aL+=[math]::Abs($eL);$aD+=[math]::Abs($eD);$a1+=[math]::Abs($e1);$a7+=[math]::Abs($e7)
      $cnt++
    }
  }
  $lastScored=$tsArr[$iTest+48*59+23]
  $s2=$sigTr*$sigTr
  $r=[pscustomobject]@{Market=$mk;N=$cnt;Missing=$missing;SigTrain=$sigTr;SigTrVal=$sigTV;SigAll=$sigAll;
   LEAR_zMSE=$sumL/$cnt/$s2;DNN_zMSE=$sumD/$cnt/$s2;SN1_zMSE=$sum1/$cnt/$s2;SN7_zMSE=$sum7/$cnt/$s2;
   LEAR_zMAE=$aL/$cnt/$sigTr;DNN_zMAE=$aD/$cnt/$sigTr;SN1_zMAE=$a1/$cnt/$sigTr;SN7_zMAE=$a7/$cnt/$sigTr;
   LEAR_zMSE_trval=$sumL/$cnt/($sigTV*$sigTV);LEAR_zMSE_all=$sumL/$cnt/($sigAll*$sigAll);
   CStar=$cStar[$mk];rLEAR=($sumL/$cnt/$s2)/$cStar[$mk];rDNN=($sumD/$cnt/$s2)/$cStar[$mk];MaxAbsDiffReal=$maxDiff;LastScored=$lastScored}
  $out+=$r
}
$out | Format-List
New-Item -ItemType Directory -Force $OutDir | Out-Null
$out | Export-Csv (Join-Path $OutDir 'indep.csv') -NoTypeInformation
