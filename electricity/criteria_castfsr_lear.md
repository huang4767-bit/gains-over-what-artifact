# Criteria for the CastFSR electricity-price comparison with LEAR

This file documents the criteria for comparing CastFSR with the domain-standard benchmark LEAR on the CastFSR electricity-price protocol, written on 2026-11-13 before any error was computed.

**Written**: 2026-11-13, before any LEAR / DNN / seasonal-naive error was computed on the CastFSR windows. The criteria were not changed afterwards. Any change goes into a separate "post hoc" section and is marked as such.

## 0. Verified protocol (extracted verbatim from the arXiv 2608.03031v3 HTML source)

- Data: five markets of Lago et al. 2021 (epftoolbox), last 14,496 hours of each market (A.2).
- Split (A.2, verbatim): train / validation / test = 10,224 / 1,416 / 2,856 hours.
  - BE, FR: train 2015-05-08 to 2016-07-06; validation 2016-07-07 to 2016-09-03; test 2016-09-04 to 2016-12-31.
  - DE: train 2016-05-07 to 2017-07-06; validation 2017-07-07 to 2017-09-03; test 2017-09-04 to 2017-12-31.
  - NP, PJM: train 2017-04-30 to 2018-06-29; validation 2018-06-30 to 2018-08-27; test 2018-08-28 to 2018-12-24.
- Windows (4.1.1, A.3, verbatim): look-back 168 hours, horizon 24 hours, stride 48 hours, 60 origins per market. The first origin is the first test hour (00:00). There are 1,440 scored hours in total, and the days in between are not scored. Sampling is deterministic, with no randomness.
- Scale (4.1.3, verbatim): "final forecasts and ground-truth targets are transformed using the training-partition mean and standard deviation". The reported MSE/MAE are on the standardised target scale.
- Reported values (Table 1; the electricity columns are the same in v1/v2/v3):

| Market | CastFSR-Zero MSE/MAE | CastFSR-R1 MSE/MAE | Best non-LLM baseline MSE of the paper (method) |
|---|---|---|---|
| BE | 0.960 / 0.386 | 0.927 / 0.375 | 1.140 (TimesFM) |
| DE | 0.393 / 0.408 | 0.386 / 0.405 | 0.798 (Chronos-2) |
| FR | 3.939 / 0.501 | 4.032 / 0.502 | 4.786 (Chronos-2) |
| NP | 0.221 / 0.277 | 0.172 / 0.247 | 0.301 (Chronos-2) |
| PJM | 0.140 / 0.268 | 0.133 / 0.260 | 0.180 (PatchTST) |

"Non-LLM baselines" are the 10 methods in Table 1: ARIMA, Prophet, PatchTST, iTransformer, ConvTimeNet, TimeXer, DLinear, TimesFM, Sundial, Chronos-2.

## 1. Information comparison (to be stated with any reading)

- LLM of CastFSR: 168 hours of target history and historical covariates. **According to the public code (`Xiaoyu-Tao/CastFSR` commit `def273e`, `forecast_context_v3.py` L1024-1131), the prompt also contains the complete covariate matrix of the 24 forecast hours** (for electricity prices, the day-ahead load and generation forecasts, available at forecast time). The v3 text says that forecast-horizon covariates are not used, which disagrees with the code and with the v1/v2 text. This is recorded separately in `castfsr_code_note.md`.
- LEAR / DNN (public epftoolbox forecasts): the forecast for target day d uses the prices of day d-1 and earlier, the day-ahead covariate forecasts for day d, and the covariates of days d-1 and d-7. The models are recalibrated every day, with a history longer than 604 days (the LEAR ensemble uses calibration windows of 56/84/1092/1456 days).
- Wording of the conclusion: the two have the **same information sources** (historical prices plus day-ahead covariate forecasts), and LEAR has the **longer history**. It must not be written as "exactly the same information".
- Seasonal naive (SN-1d: the same hour on the previous day; SN-7d: the same hour in the previous week) uses only the target history, which is **less** information than CastFSR has.

## 2. Computation

1. For each market, read the last 14,496 rows of `<data>/CastMind/data/raw/<market>/<market>.csv`. Cut out the training segment by the dates in A.2 and compute the target mean mu and standard deviation sigma (population standard deviation, ddof=0; ddof=1 is also reported).
2. Origins o_k = first test hour + 48k hours, k = 0..59. The scored hours are o_k ... o_k+23.
3. From `<data>/epftoolbox_reference/forecasts/Forecasts_<market>_DNN_LEAR_ensembles.csv`, take "LEAR Ensemble", "DNN Ensemble" and "Real price".
4. Error on the z scale: e = (forecast - truth)/sigma. MSE is the mean of e^2 over the 1,440 scored hours (all windows have equal length, so this equals the mean of per-window MSE). MAE likewise.
5. SN-1d and SN-7d are computed on the raw data (using only values before the origin).

## 3. Validity checks (if any fails, the market is not read and is reported as is)

- G1 split: the timestamps of rows 1, 10,225 and 11,641 of the last 14,496 rows equal the start days (00:00) of the training, validation and test segments of A.2, and the last row equals the test end day at 23:00.
- G2 truth agreement: over the 1,440 scored hours, the maximum absolute difference between the raw-data price and the "Real price" in the epftoolbox file is at most 1e-6.
- G3 coverage: all scored hours of the 60 windows are in the epftoolbox forecast file.
- G4 magnitude: the z-MSE of SN-1d lies between 1/3 and 3 times the best non-LLM baseline MSE of the paper. If not, the scale or protocol is taken as not matched.

## 4. Reading rule (main analysis, written in advance)

The reference for each market is the smaller MSE of CastFSR-Zero and CastFSR-R1 (the most favourable to CastFSR), written C*.

For each market, compute r = LEAR z-MSE / C*:
- r <= 0.90: the benchmark is clearly better
- r >= 1.10: CastFSR is clearly better
- otherwise: comparable

Overall reading (over markets that pass the checks):
- **H1 supported**: the benchmark is clearly better in at least 3 markets. Meaning: the advantage reported by CastFSR does not hold against the domain-standard benchmark, which is absent from the control group of the paper.
- **H1 reversed**: CastFSR is clearly better in at least 3 markets. Meaning: under the same information sources, CastFSR beats the domain-standard benchmark. **This is reported as a counterexample** and enters the counterexample part of the paper.
- Otherwise: mixed, reported market by market.

## 5. Secondary analyses (written in advance, descriptive, not changing the main reading)

- The same comparison with the DNN ensemble, and with MAE.
- LEAR z-MSE / best non-LLM baseline MSE of the paper: this measures how much weaker the control group of the paper is than the domain-standard benchmark.
- Ratio of SN-1d and SN-7d to C*.
- Sensitivity to sigma: sigma taken from the training segment (main), the training+validation segment, and all 14,496 rows. A market's category is called "scale-robust" only if it is the same under all three sigma.
- Variation due to window composition: bootstrap with replacement over the 60 windows (10,000 draws, seed 0), reporting the 2.5%-97.5% quantiles of the LEAR z-MSE. CastFSR has no per-window output, so this is not a paired test. It shows how much the number of the benchmark itself varies with the window composition.

## 6. Known limitations (to be reported)

1. CastFSR has only aggregate numbers and no per-window output, so a paired test is not possible.
2. G1, G2 and G4 give indirect support that the local 14,496-row slice is the slice of the authors. The identity is not established.
3. The mean mu has no effect on MSE (a shift cancels), while the definition of sigma affects all results. Hence the sensitivity analysis in section 5.
