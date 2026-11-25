# Independent recomputation of the first-round results (facts only)

This is an independent recomputation from the stored outputs, written separately from the analysis scripts. It was done in Windows PowerShell 5.1 and modified no input file.
Rows entering r are the rows of `<repo>/recheck/round1/out/ur_b_per_dataset.csv` with `included == True` (all rows of the four systems are True). The per-row r is the column `r`.
Script values are taken from `<repo>/recheck/round1/out/ur_b_summary.csv`, columns `r_system` and `r_system_median`.

## 1. Geometric mean of r and median for four systems

| System | Rows entering r (per_dataset, column included) | Recomputed geometric mean r | Script r_system | Difference | Recomputed median | Script r_system_median | Difference |
|---|---|---|---|---|---|---|---|
| LLMTime | 25 | 1.0042911056 | 1.0042911056 | 0 (relative difference 0) | 0.8989791755 | 0.8989791755 | 0 |
| LSTPrompt | 6 | 1.2212835565 | 1.2212835565 | 0 | 0.9943670363 | 0.9943670363 | 0 |
| CastFSR | 10 | 1.3474632156 | 1.3474632156 | 0 | 1.3085291192 | 1.3085291192 | 0 |
| JudgeCast | 5 | 1.7667057827 | 1.7667057827 | 0 | 1.7371290941 | 1.7371290941 | 0 |

In addition, for every row of LLMTime, LSTPrompt, and CastFSR, r was recomputed from the columns `control_value / reported`. The relative difference to the column `r` is below 1e-9 (the control_value of the JudgeCast rows is empty, see Section 2).

## 2. Spot checks of raw errors

| Item | Source of the raw errors (file / column) | Recomputed | r in per_dataset | Agrees |
|---|---|---|---|---|
| LLMTime AirPassengersDataset | `llmtime_darts.csv`: mae_r2 = 28.11841007177639, mae_reported (GPT-3) = 34.37257068965513 | 0.818047923 | 0.8180479233 | yes |
| LLMTime cif_2016 | `monash_dataset_cif_2016.csv`: mae_r2 = 1933744.3804011436, mae_reported = 715086.3357994701 | 2.704211063 | 2.7042110631 | yes (the file column r_r2 is also 2.7042110631) |
| LLMTime sunspot | `monash_dataset_sunspot.csv`: mae_r2 = 3.9501855341488823, mae_reported = 0.0732 | 53.96428325 | 53.9642832534 | yes (the file column r_r2 is also 53.96428325) |
| CastFSR ETTh1 | `castfsr_datasets.csv`: r3_mse = 0.103, cstar = 0.077 | 0.103 / 0.077 = 1.3376623377 | 1.3376623377 (same as file column r_r3) | yes |
| CastFSR DE | same file: r3_mse = 0.798, cstar = 0.386 | 2.0673575130 | 2.0673575130 (same as file column r_r3) | yes |
| JudgeCast NP | `judgecast_datasets.csv`: median_mse_arima = 49.43156776218285, mse_reported = 19.657; file column r_r2 = 2.6013274693 | 49.43156776 / 19.657 = 2.5147 (see below) | 2.6013274693 | agrees with the file column r_r2; differs from the direct quotient median_mse_arima / mse_reported, see below |
| JudgeCast PJM | same file: median_mse_arima = 54.40467077316974, mse_reported = 25.946; file column r_r2 = 1.7371290941 | 54.40467077 / 25.946 = 2.0968 (see below) | 1.7371290941 | same as above |

Note on JudgeCast: the column `median_mse_arima` of `judgecast_datasets.csv` is the median of the ARIMA in the paper's convention over the window family (used for the reproduction check), not the R2 control. The r in per_dataset equals the column `r_r2` of that file (median of R2 over the stride family {24, 48, 72, 96} divided by mse_reported), digit for digit (NP 2.601327469325088, PJM 1.737129094058874). The file has no column with the absolute R2 error, so the absolute R2 error cannot be recovered from mse_reported; only the agreement of the source column of r could be checked. The values 2.5147 and 2.0968 in the table are the direct quotients of `median_mse_arima`; they only show that the two quantities differ (compared with r_r2) and are not a recomputation of r.

## 3. LLMTime sensitivity

| Variant | Number of datasets | Geometric mean r | Median | Source |
|---|---|---|---|---|
| All (script convention) | 25 | 1.0042911056 | 0.8989791755 | per_dataset, block in {darts, monash} |
| Without sunspot | 24 | 0.8506795642 | 0.8942590695 | rows with dataset == sunspot removed |
| Darts only | 8 | 0.9647110090 | 0.9208897155 | block == darts (script note: 0.9647 / 0.9209, agrees) |
| Monash only | 17 | 1.0234749271 | 0.8989791755 | block == monash (script r_anchor_only 1.0234749271; note 1.0235 / 0.8990, agrees) |
| Monash only, without sunspot | 16 | 0.7988226722 | 0.8729300259 | additional |

Fact: the sunspot row has r = 53.964 (mae_r2 = 3.9502, mae_reported = 0.0732). In the same file `monash_dataset_sunspot.csv`, the column `last_value_paper` is 3.9333334 and the column `mae_naive` is 3.9333333.

## 4. Combined counts and the tier reading of the criteria

Input r values of the systems:

| Group | System | r | Source |
|---|---|---|---|
| A | MoiraiAgent | 1.013 | `recheck/round1/read_values.md`, table "r for each system" |
| A | TSOrchestra | 1.076 | same |
| A | FASE | 1.072 | same |
| A | TimeRSI | 1.402 | same |
| B | LLMTime | 1.0043 | ur_b_summary.csv column r_system (v1_pass = True) |
| B | CastFSR | 1.3475 | same (v1_pass = True) |
| B | JudgeCast | 1.7667 | same (v1_pass = True) |
| B | LSTPrompt | 1.2213 | same (v1_pass = True; whether it is counted is decided by the authors) |

MUSE-Bench is pending in the read values and is not counted; MemCast, TimEvolve, and KairosAgent have v1_pass = False and are not counted.

Systems with r at or below each threshold:

| Threshold | Systems that satisfy it | Count |
|---|---|---|
| r <= 1.00 | none (smallest are LLMTime 1.0043, MoiraiAgent 1.013) | 0 |
| r <= 1.05 | MoiraiAgent, LLMTime | 2 |
| r <= 1.10 | MoiraiAgent, TSOrchestra, FASE, LLMTime | 4 |

LSTPrompt (1.2213) satisfies none of the three thresholds, so including it changes N but not the counts.

Mechanical tier reading by the criteria ("at least ceil(N/2) -> matched tier; at most floor(N/4) -> system-ahead tier; otherwise mixed"):

| Variant | N | ceil(N/2) | floor(N/4) | r <= 1.00: count -> tier | r <= 1.05: count -> tier | r <= 1.10: count -> tier |
|---|---|---|---|---|---|---|
| With LSTPrompt | 8 | 4 | 2 | 0 -> at most 2, system-ahead tier | 2 -> at most 2, system-ahead tier | 4 -> at least 4, control-matched tier |
| Without LSTPrompt | 7 | 4 (ceil 3.5) | 1 (floor 1.75) | 0 -> at most 1, system-ahead tier | 2 -> 1 < 2 < 4, mixed tier | 4 -> at least 4, control-matched tier |

In both variants the three thresholds fall into different tiers, which meets the condition of the criteria for the reading "close".

Supplement (mechanical display only, not the script convention): if LLMTime enters with its r without sunspot, 0.8507, the counts are 1 for r <= 1.00, 3 for r <= 1.05, and 5 for r <= 1.10.
- N = 8 (ceil(N/2) = 4, floor(N/4) = 2): 1 -> system-ahead tier; 3 -> mixed tier; 5 -> control-matched tier.
- N = 7 (ceil(N/2) = 4, floor(N/4) = 1): 1 -> system-ahead tier (1 <= 1); 3 -> mixed tier; 5 -> control-matched tier.

## 5. Differences from the script outputs (relative difference > 1e-3)

None. All comparable numbers in Sections 1 to 3 differ from the script outputs by a relative difference of 0 or below 1e-9.

Facts recorded in addition (not numerical differences):
- In `judgecast_datasets.csv`, the per-dataset column `v1_pass` is False for 4 rows (BE, DE, FR, NP) and True for 1 row (PJM); in `ur_b_summary.csv`, v1_pass of JudgeCast is True (1/5 within 5%).
- The warning column of JudgeCast in `ur_b_summary.csv` reads "only 5 of the expected 6 datasets enter r".
- In `castfsr_datasets.csv`, the per-dataset column `v1_pass` is True for 3 rows (Wind, BE, FR), which agrees with "3/10" in the summary.
- The four r values of the read values, divided as numerator and denominator given there: 0.6978/0.6887 = 1.0132, 0.7281/0.6768 = 1.0758, 0.728/0.679 = 1.0721, 0.8293/0.5916 = 1.4018; they agree with the printed numbers to within 1e-3.