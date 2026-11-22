# Post hoc sensitivity: R2 with the native seasonal period

This file documents a post hoc run of phase B of the uniform recheck (`ur_b.py` with `--r2-native-period`), in which the statistical reference R2 uses the native seasonal period instead of the cap of 24 written in advance.

Run date: 2026-11-17 (CPU). Four commands were run (the `timemmd` command was left out). The script `ur_b.py` was not modified, and no package was installed in the Python environment. No code from the third-party folder was run. No LLM, key or GPU was used. No output redirection (`*>`, `>`, `2>&1`) was used.

Execution note: the first run was paused at the last dataset of CMD2 (13:31:47). It was resumed at 13:48:39 and only the unfinished `nn5_weekly` was rerun. All other finished datasets were not recomputed.

---

## 1. Command exit codes and run times

| Command | exit code | Run time | Time span |
|---|---|---|---|
| CMD1 `llmtime-darts --r2-native-period` | **0** | 155 s | 12:43:02-12:45:37 |
| CMD2 `monash --r2-native-period --datasets solar_weekly,traffic_weekly,nn5_weekly,australian_electricity_demand` | **0** (two runs, see below) | 2829 s in total (see below) | 12:45:37-13:31:47; 13:48:39-13:50:53 |
| CMD3 `castfsr --r2-native-period` | **0** | 266 s | 13:50:53-13:55:19 |
| CMD4 `summary --r2-native-period` | **0** | 2 s | 13:55:19-13:55:20 |

The two runs of CMD2:
- First run (from 12:45:37): `solar_weekly` 69.0 s, `australian_electricity_demand` 2436.3 s and `traffic_weekly` 246.6 s finished. `nn5_weekly` had started when the run was paused and terminated (no exit code, the process was killed).
- Rerun (from 13:48:39): `nn5_weekly` exit 0, 131.2 s (timing in the log; wall clock 134 s).

Total wall clock: 12:43:02-13:55:20, 1 h 12 min. This includes a 17 min pause, so the actual computation took about 55 min.

---

## 2. Full text of `ur_b_summary.txt` (post hoc output folder)

```text
Uniform re-check, phase B -- mechanical summary (judgement rules: criteria written in advance)
*** POST HOC (--r2-native-period): R2 uses the native seasonal period, NOT the cap of 24 written in advance. Not part of the primary analysis. ***

LSTPrompt V1-P AirPassengersDataset: ARIMA(authors) MAE recomputed in an earlier analysis from LLMTime's published ARIMA forecasts = 24.0337 vs LSTPrompt Table 1 24.03 (rel +0.00015)
LSTPrompt V1-P MonthlyMilkDataset: ARIMA(authors) MAE recomputed in an earlier analysis from LLMTime's published ARIMA forecasts = 37.1941 vs LSTPrompt Table 1 37.19 (rel +0.00011)
LSTPrompt V1-P AusBeerDataset: ARIMA(authors) MAE recomputed in an earlier analysis from LLMTime's published ARIMA forecasts = 17.1338 vs LSTPrompt Table 1 17.13 (rel +0.00022)
LSTPrompt V1-P SunspotsDataset: ARIMA(authors) MAE recomputed in an earlier analysis from LLMTime's published ARIMA forecasts = 43.5632 vs LSTPrompt Table 1 43.56 (rel +0.00007)

system       V1      n        r   median     r_R1   r_anch  category / thresholds
LLMTime      True   12   0.9133   0.9103   1.0555   0.8533  control matched  r<=1.00:Y r<=1.05:Y r<=1.10:Y
             V1: type M: Monash naive vs monash.csv 'Last Value', 4/4 datasets within 5% (anchor subset = those passing in Monash; Darts has no anchor)
             fallbacks (datasets in r): R2 fits=1123, failures ETS/Theta/ARIMA=0/0/0, median-of-2=0, single=0, all-three-failed->R1=0; R1 period->naive=137; r_anch over 4 anchor-passing datasets
             subsets: darts: n=8 geomean r=0.9448 median r=0.8747; monash: n=4 geomean r=0.8533 median r=0.9460
             WARNING: only 12 of the expected 25 datasets enter r (see per-dataset rows)
LSTPrompt    True    4   1.3478   1.3996   1.5777   1.3478  system clearly ahead  r<=1.00:N r<=1.05:N r<=1.10:N
             V1: type P: the ARIMA column is recomputed from the public ARIMA forecasts of LLMTime, 4/4 within 5% (whether it counts is decided separately; the counts below give both versions)
             fallbacks (datasets in r): R2 fits=4, failures ETS/Theta/ARIMA=0/0/0, median-of-2=0, single=0, all-three-failed->R1=0; R1 period->naive=0; r_anch over 4 anchor-passing datasets
             Darts 4 + Monash 2
             WARNING: only 4 of the expected 6 datasets enter r (see per-dataset rows)
CastFSR      True    5   1.2033   1.1339   1.5476   1.4355  system clearly ahead  r<=1.00:N r<=1.05:N r<=1.10:N
             V1: type M: ARIMA(2,1,2) anchor within 5% on 1/5 datasets
             fallbacks (datasets in r): R2 fits=463, failures ETS/Theta/ARIMA=0/0/0, median-of-2=0, single=0, all-three-failed->R1=0; R1 period->naive=0; r_anch over 1 anchor-passing datasets
             main control R3; inclusion check = structure check + magnitude check (not included: none); R2 system r = 2.0876 (median 1.8416); R3 per-dataset best (sensitivity) = 1.1593
             WARNING: only 5 of the expected 10 datasets enter r (see per-dataset rows)
MUSE-Bench   False   0      nan      nan      nan      nan  (protocol not verified, not counted)
             V1: protocol not verified: the processed benchmark data and windows are not public

B systems passing V1, including LSTPrompt (P-type anchor): N_B = 3 (LLMTime, LSTPrompt, CastFSR)
    r <= 1.00: 1/3
    r <= 1.05: 1/3
    r <= 1.10: 1/3
B systems passing V1, excluding LSTPrompt: N_B = 2 (LLMTime, CastFSR)
    r <= 1.00: 1/2
    r <= 1.05: 1/2
    r <= 1.10: 1/2

columns: r = geometric mean over datasets in r; median = median of the same r; r_R1 = R1 lower reference; r_anch = only datasets whose own anchor is within 5 % (sensitivity)
per-dataset rows (with block, fallback counters, R1 notes): ur_b_per_dataset.csv
```

---

## 3. Dataset result lines and key lines of the logs

Local paths in the logged command lines are replaced by `<data>/...` placeholders.

### 3.1 `llmtime_darts.log` (14 lines in full)

```text
[2026-11-17 12:43:06] === llmtime_darts start | python 3.14.2 | numpy 2.5.4 | pandas 2.3.3 | argv ['llmtime-darts', '--r2-native-period', '--out', '<data>/out', '--darts-csv-dir', '<data>/darts_csv', '--llmtime-root', '<data>/llmtime', '--r12-stat-csv', '<data>/llmtime/out/stat_forecasts.csv']
[2026-11-17 12:43:07] statsforecast 2.1.1 | statsmodels 0.15.0
[2026-11-17 12:43:20] AirPassengersDataset   H=29   m=12/12 MAE R1=64.7586 R2=28.1184 GPT-3(rep)=34.3726 r_R2=0.8180 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:43:22] AusBeerDataset         H=43   m=4/4 MAE R1=14.2558 R2=12.6450 GPT-3(rep)=16.1270 r_R2=0.7841 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:43:22] GasRateCO2Dataset      H=60   m=1/1 MAE R1=2.2900 R2=2.2895 GPT-3(rep)=3.4958 r_R2=0.6550 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:43:27] MonthlyMilkDataset     H=34   m=12/12 MAE R1=9.5588 R2=14.2461 GPT-3(rep)=9.6772 r_R2=1.4721 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:45:26] SunspotsDataset        H=141  m=33/33 MAE R1=43.8745 R2=40.7046 GPT-3(rep)=47.3390 r_R2=0.8599 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:45:33] WineDataset            H=36   m=12/12 MAE R1=2246.3333 R2=2212.8739 GPT-3(rep)=1569.3237 r_R2=1.4101 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:45:34] WoolyDataset           H=24   m=4/4 MAE R1=824.9167 R2=719.3976 GPT-3(rep)=808.7309 r_R2=0.8895 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:45:36] HeartRateDataset       H=180  m=1/1 MAE R1=5.9192 R2=5.9145 GPT-3(rep)=6.2111 r_R2=0.9522 mode=median3 stat={'ETS': 'ok', 'Theta': 'ok', 'ARIMA': 'ok'}
[2026-11-17 12:45:36] SMOKE CHECK darts: datasets with any R2 component not ok: none (must be none, except possibly SunspotsDataset)
[2026-11-17 12:45:36] R2 tally [llmtime-darts]: calls=8 all-three-failed(->R1)=0 fail_ETS=0 fail_Theta=0 fail_ARIMA=0
[2026-11-17 12:45:36] wrote llmtime_darts.csv, llmtime_darts_points.csv
[2026-11-17 12:45:36] *** POST HOC run (--r2-native-period); outputs written to POSTHOC_r2_native_period ***
```

### 3.2 `monash.log` (14 lines in full; appended by two calls)

```text
[2026-11-17 12:45:38] === monash start | python 3.14.2 | numpy 2.5.4 | pandas 2.3.3 | argv ['monash', '--r2-native-period', '--out', '<data>/out', '--monash-dir', '<data>/monash_tsf', '--llmtime-root', '<data>/llmtime', '--r12-monash-csv', '<data>/llmtime/out/main_fixed/monash_per_dataset.csv', '--datasets', 'solar_weekly,traffic_weekly,nn5_weekly,australian_electricity_demand']
[2026-11-17 12:45:38] statsforecast 2.1.1 | statsmodels 0.15.0
[2026-11-17 12:46:47] solar_weekly                   n=137/137 H=5 m=52 naive=1729.41 LastValue=1729.41 (V1 rel -0.0000) R1=1729.41 R2=1203.37 GPT-3=2049.1 r_R2=0.5873 fallbacks median2=0 single=0 R1=0 | origins=137 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=137 (69.0 s)
[2026-11-17 12:46:47] solar_weekly: NOTE R1 = naive on 137/137 series (history shorter than m=52)
[2026-11-17 13:27:24] australian_electricity_demand  n=5/5 H=336 m=48 naive=659.601 LastValue=659.601 (V1 rel +0.0000) R1=455.961 R2=464.166 GPT-3=459.966 r_R2=1.0091 fallbacks median2=0 single=0 R1=0 | origins=5 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0 (2436.3 s)
[2026-11-17 13:28:34] traffic_weekly: 250/862 series, 70 s
[2026-11-17 13:29:47] traffic_weekly: 500/862 series, 143 s
[2026-11-17 13:30:58] traffic_weekly: 750/862 series, 214 s
[2026-11-17 13:31:31] traffic_weekly                 n=862/862 H=8 m=52 naive=1.18558 LastValue=1.18558 (V1 rel +0.0000) R1=1.41581 R2=1.12781 GPT-3=1.17369 r_R2=0.9609 fallbacks median2=0 single=0 R1=0 | origins=862 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0 (246.6 s)
[2026-11-17 13:48:40] === monash start | python 3.14.2 | numpy 2.5.4 | pandas 2.3.3 | argv ['monash', '--r2-native-period', '--out', '<data>/out', '--monash-dir', '<data>/monash_tsf', '--llmtime-root', '<data>/llmtime', '--r12-monash-csv', '<data>/llmtime/out/main_fixed/monash_per_dataset.csv', '--datasets', 'nn5_weekly']
[2026-11-17 13:48:41] statsforecast 2.1.1 | statsmodels 0.15.0
[2026-11-17 13:50:52] nn5_weekly                     n=111/111 H=8 m=52 naive=16.7086 LastValue=16.7086 (V1 rel +0.0000) R1=21.7025 R2=14.8212 GPT-3=15.9195 r_R2=0.9310 fallbacks median2=0 single=0 R1=0 | origins=111 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0 (131.2 s)
[2026-11-17 13:50:52] R2 tally [monash]: calls=111 all-three-failed(->R1)=0 fail_ETS=0 fail_Theta=0 fail_ARIMA=0
[2026-11-17 13:50:52] *** POST HOC run (--r2-native-period); outputs written to POSTHOC_r2_native_period ***
```

### 3.3 `castfsr.log` (12 lines in full)

```text
[2026-11-17 13:50:54] === castfsr start | python 3.14.2 | numpy 2.5.4 | pandas 2.3.3 | argv ['castfsr', '--r2-native-period', '--out', '<data>/out', '--ett-dir', '<data>/ur_b/ett_1d16c8f', '--wind-csv', '<data>/castfsr/data/wind.csv']
[2026-11-17 13:50:54] statsforecast 2.1.1 | statsmodels 0.15.0
[2026-11-17 13:55:18] epf_cache.csv not found: run epf-cache first; EPF part of CastFSR skipped
[2026-11-17 13:55:18] R3 readout: geometric-mean ratio to C* per pool expert {'ARIMA': 2.51965947194001, 'DLinear': 1.6397751219089785, 'PatchTST': 1.4752323892908799, 'iTransformer': 1.6562974698402986, 'Chronos2': 1.3474632156279804}; best single expert = Chronos2
[2026-11-17 13:55:18] CastFSR ETTh1  gate=True anchor ARIMA(2,1,2) zMSE 0.1052 vs paper 0.156 (q=0.674, V1 fail, scale gate True) | zMSE R1 0.1221 R2 0.1227 | C* 0.077 | r_R3 1.338 r_R2 1.593 | origins=36 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0
[2026-11-17 13:55:18] CastFSR ETTh2  gate=True anchor ARIMA(2,1,2) zMSE 0.3317 vs paper 0.356 (q=0.932, V1 fail, scale gate True) | zMSE R1 0.2964 R2 0.4457 | C* 0.242 | r_R3 1.062 r_R2 1.842 | origins=36 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0
[2026-11-17 13:55:18] CastFSR ETTm1  gate=True anchor ARIMA(2,1,2) zMSE 0.0519 vs paper 0.142 (q=0.366, V1 fail, scale gate True) | zMSE R1 0.0699 R2 0.0644 | C* 0.055 | r_R3 1.091 r_R2 1.170 | origins=145 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0
[2026-11-17 13:55:18] CastFSR ETTm2  gate=True anchor ARIMA(2,1,2) zMSE 0.2939 vs paper 0.173 (q=1.699, V1 fail, scale gate True) | zMSE R1 0.1596 R2 0.5593 | C* 0.127 | r_R3 1.134 r_R2 4.404 | origins=145 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0
[2026-11-17 13:55:18] CastFSR Wind   gate=True anchor ARIMA(2,1,2) zMSE 3.6080 vs paper 3.682 (q=0.980, V1 PASS, scale gate True) | zMSE R1 4.5658 R2 4.1846 | C* 1.596 | r_R3 1.435 r_R2 2.622 | origins=101 fail E/T/A=0/0/0 median2=0 single=0 allfail->R1=0 R1-period->naive=0
[2026-11-17 13:55:18] R2 tally [castfsr]: calls=463 all-three-failed(->R1)=0 fail_ETS=0 fail_Theta=0 fail_ARIMA=0
[2026-11-17 13:55:18] wrote castfsr_datasets.csv, castfsr_windows.csv
[2026-11-17 13:55:18] *** POST HOC run (--r2-native-period); outputs written to POSTHOC_r2_native_period ***
```

### 3.4 `summary.log`: lines with `===` and `WARNING`

```text
[2026-11-17 13:55:20] === summary start | python 3.14.2 | numpy 2.5.4 | pandas 2.3.3 | argv ['summary', '--r2-native-period', '--out', '<data>/out', '--r12-darts-metrics', '<data>/llmtime/out/main_fixed/darts_metrics.csv']
[2026-11-17 13:55:20]              WARNING: only 12 of the expected 25 datasets enter r (see per-dataset rows)
[2026-11-17 13:55:20]              WARNING: only 4 of the expected 6 datasets enter r (see per-dataset rows)
[2026-11-17 13:55:20]              WARNING: only 5 of the expected 10 datasets enter r (see per-dataset rows)
```

### 3.5 Sentinel checks (all passed)

- `R2 SENTINEL`: did not appear in any log.
- `failed at EVERY R2 call`: did not appear.
- `R2 component failure`: did not appear.
- `STOP`: did not appear.
- `R2 tally` in three places: llmtime-darts `calls=8 ... 0`; monash `calls=111 ... 0`; castfsr `calls=463 ... 0`.
- The 3 WARNING lines are expected: `timemmd` was not run, so LLMTime has only 8 Darts + 4 Monash = 12 datasets. The same holds for LSTPrompt and CastFSR.

---

## 4. Unchanged primary outputs and post hoc file list

The formal (primary) result files keep their modification time of 2026/11/17 03:09 and were not touched by this run. A file-by-file comparison of the 67 files in the primary output folder (name, size, modification time) against the state before the run showed no difference.

Files in the post hoc output folder (name, size in bytes):

```text
castfsr.log                                        2472
castfsr_datasets.csv                               2507
castfsr_windows.csv                               47010
llmtime_darts.csv                                  2911
llmtime_darts.log                                  2402
llmtime_darts_points.csv                          57779
monash.log                                         2848
monash_dataset_australian_electricity_demand.csv    714
monash_dataset_nn5_weekly.csv                       668
monash_dataset_solar_weekly.csv                     748
monash_dataset_traffic_weekly.csv                   673
monash_series_australian_electricity_demand.csv     977
monash_series_nn5_weekly.csv                      17129
monash_series_solar_weekly.csv                    20634
monash_series_traffic_weekly.csv                 137607
README_POST_HOC.txt                                 357
summary.log                                        5080
ur_b_per_dataset.csv                               3405
ur_b_summary.csv                                   1758
ur_b_summary.txt                                   3697
```

---

## 5. Errors and run times

### 5.1 Errors

There was no abnormal exit and no traceback. The only stderr output is a `ResourceWarning` at interpreter exit, which does not affect the results:

```text
<sys>:0: ResourceWarning: unclosed file <_io.TextIOWrapper name='<data>/out/POSTHOC_r2_native_period/castfsr.log' mode='a' encoding='utf-8'>
```

Two situations were expected, and the run continued:
- `castfsr.log`: `epf_cache.csv not found: run epf-cache first; EPF part of CastFSR skipped` (the electricity price part is skipped; CastFSR has only 5 long-series datasets).
- The summary has no Time-MMD (not run) and no electricity price system.

### 5.2 Run time breakdown

| Stage | Log timing | Wall clock |
|---|---|---|
| llmtime-darts (8 datasets) | - | 155 s |
| monash: solar_weekly | 69.0 s | 69.0 s |
| monash: australian_electricity_demand | 2436.3 s | 2436.3 s |
| monash: traffic_weekly (862 series) | 246.6 s | 246.6 s |
| monash: nn5_weekly (rerun) | 131.2 s | 134 s |
| castfsr (5 long-series datasets) | - | 266 s |
| summary | - | 2 s |

Note: `australian_electricity_demand` took 40.6 minutes in this run (318.8 s in the primary run on the same dataset). It was the slowest item here, because with the native period 48 and H=336 each window needs much more expensive statistical fits. `traffic_weekly` took only 246.6 s (1002.5 s in the primary run, which ran in parallel with other windows).

### 5.3 Other

- Pause and resume: paused at 13:31:47 (`nn5_weekly` interrupted), resumed at 13:48:39, and only `nn5_weekly` was rerun. `monash.log` was appended to, so the result lines of the first 3 datasets are preserved (both `=== monash start` lines are present).
- No script was changed, no package was installed, no code from the third-party folder was run, and no LLM, GPU or network was used.
