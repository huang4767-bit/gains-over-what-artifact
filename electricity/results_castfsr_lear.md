# Results of the CastFSR electricity-price comparison with LEAR

This file documents the results (2026-11-13) of comparing CastFSR with the domain-standard benchmark LEAR on the CastFSR electricity-price protocol.

Criteria: `criteria_castfsr_lear.md` in this folder (written before computing). Script: `castfsr_lear.ps1`. Inputs are local copies of the CastMind raw data and the epftoolbox reference forecasts (`<data>/CastMind/data/raw`, `<data>/epftoolbox_reference/forecasts`). The per-item output file of the script is not part of this repository.

## 1. Validity checks: all 5 markets pass

- G1: the training, validation and test start points and the last row of the last 14,496 rows equal the dates in A.2 of the paper, one by one.
- G2: over the 1,440 scored hours, the maximum difference between the local price and the epftoolbox "Real price" is 0 (PJM 1.4e-14).
- G3: all scored hours are in the public forecast files.
- G4: the z-MSE of SN-1d is 1.5-2.2 times the best non-LLM baseline of the paper, within 1/3-3 times.
- In addition, the first origin and the last scored hour equal A.3 and Table 6 of the paper. The window positions are fixed uniquely by the paper, so no enumeration of placements is needed, as it was for MemCast.

## 2. Main reading (criteria written in advance)

C* = the smaller MSE of CastFSR-Zero and CastFSR-R1 (the most favourable to CastFSR). r = LEAR z-MSE / C*.

| Market | LEAR z-MSE | C* (source) | r | Category | Category under three sigma (train / train+validation / all) |
|---|---|---|---|---|---|
| BE | 1.063 | 0.927 (R1) | 1.147 | CastFSR clearly better | C / C / B (not robust) |
| DE | 0.280 | 0.386 (R1) | 0.724 | benchmark clearly better | B / B / B (robust) |
| FR | 4.015 | 3.939 (Zero) | 1.019 | comparable | = / = / B |
| NP | 0.183 | 0.172 (R1) | 1.066 | comparable | = / B / B |
| PJM | 0.122 | 0.133 (R1) | 0.919 | comparable | = / = / = |

**Overall reading: mixed.** The benchmark is clearly better in 1 market (DE), and CastFSR is clearly better in 1 market (BE). Neither H1 nor H1 reversed is triggered.

Additional points:
- With CastFSR-R1 only (the main variant of the paper), the categories of the 5 markets are identical to the table above, so the choice of C* does not affect the result.
- **The result depends on the training-segment sigma stated in the paper.** If sigma is taken over all 14,496 rows (which include test data and is not a legitimate convention), BE, DE, FR and NP all become "benchmark clearly better", and H1 is triggered. With the training+validation segment, NP becomes "benchmark clearly better". The reason is that price volatility in the test segment is larger than in the training segment (FR: sigma 20.6 over all rows, 12.3 on the training segment). The 1/3-3 range of G4 is a loose check and does not pin down sigma.

## 3. Secondary analyses (written in advance, descriptive)

| Market | DNN / C* | LEAR / C* (MAE) | DNN / C* (MAE) | **LEAR / best non-LLM baseline of the paper** | **C* / best non-LLM baseline of the paper** | SN-1d / C* | 95% interval of LEAR z-MSE by window resampling |
|---|---|---|---|---|---|---|---|
| BE | 1.091 | 1.028 | 0.956 | 0.93 | 0.81 | 2.50 | 0.22-2.60 |
| DE | 0.586 | 0.831 | 0.739 | 0.35 | 0.48 | 4.51 | 0.15-0.47 |
| FR | 1.061 | 1.050 | 1.046 | 0.84 | 0.82 | 2.16 | 0.38-11.02 |
| NP | 1.056 | 1.092 | 1.115 | 0.61 | 0.57 | 3.42 | 0.11-0.27 |
| PJM | 0.883 | 0.975 | 0.922 | 0.68 | 0.74 | 2.07 | 0.09-0.16 |

Reading:
- The error of the domain-standard benchmark (LEAR, 2021) is 0.35-0.93 times that of the best non-LLM baseline in the control group of the paper. With a +-10% band, the benchmark is clearly better in 4 of 5 markets, and BE (0.93) is inside the band. The control group of the paper does not contain this benchmark. The ratio also depends on sigma (the larger sigma, the better LEAR looks).
- The improvement reported by CastFSR over the best baseline of the paper is 19%-52%. With LEAR instead, the gap ranges from -13% (BE, CastFSR better) to +38% (DE, LEAR better), and 3 markets lie inside the +-10% band written in advance. The +-10% band is a descriptive band and not an equivalence test, so the result must not be written as "tied" or "equivalent".
- The resampling intervals for BE and FR are very wide (price spikes in autumn and winter 2016). In these two markets, a few windows decide which side is better.
- CastFSR has no per-window output, so none of the above is a paired test.

## 4. Post hoc analyses (not written in advance)

- CastFSR-Zero only (the untrained version, driven by DeepSeek-V4-Flash alone): the MSE ratio LEAR / Zero is BE 1.107, DE 0.711, FR 1.019, NP 0.830, PJM 0.873. With the same thresholds, the benchmark is clearly better in 2 markets (DE, NP) and CastFSR is clearly better in 1 (BE, just past 1.10).
- The geometric mean of r over the 5 markets is about 0.96, and about 0.90 for Zero only (descriptive).
- Comparison with MemCast (across papers and protocols, as a hint only): on the same data and the same benchmark, MemCast loses to LEAR on NP, PJM and DE however the windows are placed (0.4-0.7 times). CastFSR shows no such systematic lag. The MemCast result does not extend to CastFSR.

## 5. Information sources (premise of the reading)

- According to the public code (`Xiaoyu-Tao/CastFSR` commit `def273e0be9df1cea3e9302189c4ed9eecee5af4`), the LLM prompt of CastFSR contains the day-ahead covariate forecasts for the 24 forecast hours (see `castfsr_code_note.md`). LEAR also uses the day-ahead covariate forecasts of the target day. The two therefore have the **same information sources**, and LEAR has the longer history (recalibrated every day with up to 1,456 days).
- Whether the individual baselines in Table 1 of the paper (such as Chronos-2) received the forecast-horizon covariates is not stated in the paper or the repository. If they did not, part of the CastFSR advantage over them comes from an information difference. This is a **hypothesis to be checked** and not a conclusion.
- Two further asymmetries:
  - **In favour of LEAR**: LEAR is refitted each day with data up to the previous day, so it uses realised prices from the validation and test segments. The neural experts of CastFSR are trained on the training segment only and then kept fixed, and see the test segment only through the 168-hour context. Both use only past data, so this is no leakage. It is the difference between "online re-estimation" and "fixed model plus context".
  - **In favour of CastFSR**: the prompt contains the real date range and the market name (`forecast_context_v3.py` L1110-1113). The pre-training corpus of DeepSeek-V4-Flash may contain public information on European electricity prices of 2016-2018 (for example the autumn 2016 spikes caused by French nuclear outages, which fall in the FR and BE test segments). Memorisation cannot be ruled out. LEAR has no such channel.

## 6. Verification

- Independent recomputation (`independent_recompute.ps1`): a separately written script recomputed sigma, the z-MSE/z-MAE of the four methods, the ratios and the checks from the raw data. All agree within 4 significant digits, and no bug was found in the original script.
