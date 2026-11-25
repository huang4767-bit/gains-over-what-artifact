# Independent recomputation of the second round (CiK / BNP / Nexus / N2F / CompEvo)

This is an independent recomputation from the stored outputs, written separately from the analysis scripts. It is a read-only check; no original file was modified.
Method: everything was recomputed in Windows PowerShell 5.1 from the raw outputs (cik_instances.csv, cik_anchor_seed_rcrps.csv, n2f_forecasts.csv, nexus_r3.csv, and the manifests). Nexus was recomputed once more from the literal values written in the criteria (Section 6.3), independent of the csv files.

## Summary

**All 7 items agree**; no numerical mismatch was found.

- Checksums: the recorded checksums of the criteria file and of `ur_c.py` match the frozen values; all 35 manifest entries match the actual checksums (more than the required "at least 10").
- CiK: R1, R2, and the anchor aggregate recompute to 0.35183, 0.42952, and 0.57187, as reported. The deviation of the reproduction check is -5.476%, outside the 5% tolerance (this check recomputes numbers only and does not judge the check).
- N2F: the RMSE over 4,800 points is 839.62 (R2) and 488.49 (R1); r is 2.994 and 1.742.
- Nexus: r = 1.121; the sensitivity with the best pool model per column is 1.116.
- Section 7 gives K = 1, a = 0, b = 1, and the reading "insufficient test". Section 8 gives the counts 0/2/4 in both variants, N = 9 and N = 8, and both read "close". The conclusion of the summary rule (no separate combined reading is written; the main reading with N = 8, "close", stays) is correct.
- The report and the files in `out/` agree item by item, with one remark (see "Additional observations").

## 1. Checksums: agree

| Object | Actual value | Expected value | Result |
|---|---|---|---|
| criteria file of the second round | matches | the value recorded in the frozen-criteria record | agrees |
| `ur_c.py` | matches | the frozen value (also the value recorded in the report, items 1b and 1g) | agrees |

Manifests: all 35 entries of the 7 manifest files were re-hashed one by one; **35/35 agree, 0 differ**.
By manifest: cik 11 entries, compevo-check 5, n2f 5, nexus 4, selftest 1, smoke 5, summary 4. They include cik_instances.csv, cik_forecasts.csv, cik_anchor_seed_rcrps.csv, cik_anchor_samples_offset0.npz, n2f_forecasts.csv, nexus_r3.csv, ur_c_summary.json, and other core files.

## 2. CiK aggregates: agree

Method: the 355 rows of cik_instances.csv were read; for `rcrps_raw_R1`, `rcrps_raw_R2`, and `rcrps_raw_anchor`, values of 5 or more were capped at 5 and then averaged with the fraction weights. The weights are 1, 1/2, 1/3, 1/4, 1/8, and 1/16, parsed as fractions; the sum of weights is 105.

| Quantity | Capped values (recomputed) | Capped values (reported) | Recomputed aggregate (unrounded) | Reported value | Result |
|---|---|---|---|---|---|
| R1 | 2 | 2 | 0.3518304534922316 | 0.3518304534922316 | agrees (0.35183) |
| R2 | 1 | 1 | 0.4295157792927236 | 0.4295157792927236 | agrees (0.42952) |
| Anchor Exp-Smoothing | 3 | 3 | 0.5718680257615214 | 0.5718680257615214 | agrees (0.57187) |

Further check: the weighted average of the already capped columns `rcrps_R1`, `rcrps_R2`, and `rcrps_anchor` in the file gives the same three values.

Recomputed ratios:
- r(R2) = 0.4295157792927236 / 0.159 = 2.70136 (with the rounded value, 0.42952 / 0.159 = 2.70138); reported 2.70135710246996; agrees.
- r(R1) = 0.3518304534922316 / 0.159 = 2.21277; reported 2.2127701477498842; agrees.
- BNP r(R2) = 0.4295157792927236 / 0.110 = 3.90469 (rounded values: 0.42952 / 0.110 = 3.90473); reported 3.904688902661124; agrees.
- BNP r(R1) = 0.3518304534922316 / 0.110 = 3.19846; reported 3.198458668111196; agrees.

## 3. CiK reproduction check: agrees

- 0.57187 / 0.605 - 1 = **-0.05476** (rounded to -0.0548); unrounded 0.5718680257615214 / 0.605 - 1 = -0.0547636. |-0.0548| > 0.05, so the value is **outside the 5% tolerance**.
- Distribution over seeds: cik_anchor_seed_rcrps.csv has 21 columns (off_0 to off_20000). For each column, values were capped at 5, averaged with the weights, and compared with 0.605:

| Offset | Relative deviation | Offset | Relative deviation | Offset | Relative deviation |
|---|---|---|---|---|---|
| 0 | -5.48% x | 7000 | -1.34% | 14000 | +0.43% |
| 1000 | -4.23% | 8000 | -5.66% x | 15000 | -5.14% x |
| 2000 | -6.65% x | 9000 | -2.50% | 16000 | -2.93% |
| 3000 | -4.03% | 10000 | -3.33% | 17000 | -4.69% |
| 4000 | -5.33% x | 11000 | -3.78% | 18000 | -2.26% |
| 5000 | -4.60% | 12000 | -1.23% | 19000 | -4.26% |
| 6000 | -3.55% | 13000 | -2.71% | 20000 | -7.19% x |

(x marks a deviation beyond 5%.)

  **15 of 21** are within 5%; the 6 outside are off_0, 2000, 4000, 8000, 15000, and 20000. This agrees with "15 of 21 seeds within 5%".
- The median is 0.58059, the minimum 0.56150, the maximum 0.60760; the 5% and 95% quantiles (linear interpolation, taking the 2nd smallest and the 2nd largest) are 0.56475 and 0.59758, which agree with the reported [0.5648, 0.5976]. cik_anchor_seeds.csv has 21 rows, as expected.

## 4. N2F: agrees

n2f_forecasts.csv has 4,800 rows (100 windows x 48 steps). RMSE = sqrt(sum((forecast - y)^2) / 4800):
- R2 (column r2): 839.6211033; reported 839.621103346161; agrees (839.62).
- R1 (column r1): 488.4870152; reported 488.48701524665245; agrees (488.49).
- r(R2) = 839.6211033 / 280.39 = **2.99448** (with 839.62 / 280.39 = 2.99447); reported 2.9944759; agrees.
- r(R1) = 488.4870152 / 280.39 = **1.74217**; reported 1.742169889; agrees.
- Additional check: the column r2 equals the median of the columns ets, theta, and arima on all 4,800 rows (0 rows differ). The RMSE of the three single models is 902.14, 727.33, and 1640.31.

## 5. Nexus: agrees

Independent recomputation with the values taken from Section 6.3 of the criteria, not from the csv.

- System values (smaller of the two versions, Gemini and Claude, per column): 1.970, 5.305, 1.958, 2.488, 2.994, 3.434. In all 6 columns the smaller value is the Gemini version, as in Section 5.4 of the criteria.
- Geometric mean over the 6 columns of the ratio of each model to the system value:

| Model | Ratio |
|---|---|
| Chronos-2 | 1.1206758 |
| TimesFM-2.5 | 1.1843877 |
| TiRex | 1.1334337 |

- The best single model is Chronos-2, **r = 1.1206758, about 1.121**. P1 (> 1.221) is False, P2 (> 1.10) is True.
- **Sensitivity (best pool model per column):** the best models per column are Chronos-2, Chronos-2, Chronos-2, TiRex, TiRex, TiRex. The geometric mean is **1.1155210, about 1.116**, as reported.
- The per-column ratios of Chronos-2 in nexus_r3.csv, 1.34975, 1.16664, 1.04494, 1.05627, 1.04041, 1.09552, are identical to the six hand-computed ratios.

## 6. Section 7 and the combined reading: agree

**Section 7:** the only new S-tier system that passes the reproduction check and is counted is Nexus, so K = 1. a = number of systems with r > 1.221 = 0 (1.1207 < 1.221). b = number of systems with r > 1.10 = 1 (1.1207 > 1.10). By Section 7.2, K <= 2 gives the reading **"insufficient test"**, as reported.

**r of the original 8 systems:** checked against `recheck/round1/read_values.md` and ur_b_summary.csv; all 8 values match (MoiraiAgent 1.013, TSOrchestra 1.076, FASE 1.072, TimeRSI 1.402, LLMTime 1.004, LSTPrompt 1.221, CastFSR 1.347, JudgeCast 1.767).

**Section 8, main variant (with LSTPrompt):** N = 8 + 1 = 9, ceil(9/2) = 5, floor(9/4) = 2. Nexus (1.121) is not counted at any of the three thresholds.

| Threshold | Count | Tier |
|---|---|---|
| r <= 1.00 | 0 | 0 <= 2, ahead tier (counter-evidence) |
| r <= 1.05 | 2 (LLMTime 1.004, MoiraiAgent 1.013) | 2 <= 2, ahead tier (counter-evidence) |
| r <= 1.10 | 4 (plus FASE 1.072, TSOrchestra 1.076) | 4 < 5 and 4 > 2, mixed tier |

The three thresholds fall into different tiers, hence **"close"**.

**Other variant (without LSTPrompt):** N = 7 + 1 = 8, ceil(8/2) = 4, floor(8/4) = 2. The counts are again 0, 2, 4 (LSTPrompt, 1.221, is not within any threshold anyway). The tiers are ahead, ahead, matched (4 >= 4); the reading is again **"close"**.

**Summary rule:** Section 8 states that when the three thresholds of the main variant fall into different tiers ("close"), the abstract writes no separate combined reading and keeps the main reading with N = 8, "close". This conclusion of the report and of ur_c_summary is **correct**.
Counts and tiers: the counts and tiers for N = 9 and N = 8 agree with section8 of ur_c_summary.json. The reproduction of the original N = 8 and N = 7 in the report also agrees with original_counts.

## 7. Report and `out/` files: agree

- The full text of ur_c_summary.txt embedded in Section 8 of the report and the file out/ur_c_summary.txt were compared line by line (50 lines): **0 differences**.
- The lines of cik_primary.txt, n2f_summary.txt, and nexus_r3.txt agree with the corresponding log lines in the report (the logs have an extra timestamp prefix).
- The values r, RMSE, aggregates, the capped counts (anchor 3, R1 2, R2 1), and the R2 tally (fail_ETS = 139, fail_Theta = 10, fail_ARIMA = 0, median3 = 216, median2 = 129, single = 10) in ur_c_summary.json, ur_c_status.csv, cik_primary.json, n2f_summary.json, and cik_descriptive.json agree with the report.
- The file sizes in Section 9a of the report agree with the actual lengths in `out/` (spot checks of cik_instances.csv 102861, n2f_forecasts.csv 443409, cik_anchor_seed_rcrps.csv 163061, and others).
- The statement "one run, no error" agrees with the content of cik_FIRST_RUN.lock (17:05:52 up to the anchor stage; same script checksum).

## Additional observations (they do not change the results above)

1. **The sensitivity that switches to the frequency table is a no-op.** In cik_sens_freq.csv, all 175 recomputed rows (30 rows of 10min with m = 144, 145 rows of MS with m = 12) have a history shorter than m, so R1 degenerates to m = 1. On these 175 rows, the per-instance R1 and R2 values are identical to the main run (maximum absolute difference 0). Hence r_CiK(R2) = 2.701 and r_BNP = 3.905 equal the main values digit for digit, and this sensitivity carries no information. `r1_degenerate: 175` in cik_descriptive.json does not contradict the 0 of the main run for this reason.
2. The anchor cap count is 3. The criteria and Table 6 of the paper list 5 comparison values; the two numbers differ, which is a descriptive item.
3. For "r > 1.405" in Section 7.3, item 3, the report gives two readings: the literal reading (BNP, CiK, and N2F, 3 systems, including those with unverified protocol) and the reading restricted to systems that pass the reproduction check (0 systems). This is a faithful handling of an ambiguous place in the criteria and has no numerical issue.
4. ur_c_summary.json contains the literal `NaN` (r_R1, and r of CompEvo); strict JSON parsers reject it. This is a format matter only.