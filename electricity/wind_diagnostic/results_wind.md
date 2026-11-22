# Wind diagnostic results

This file documents the results of the wind power-curve diagnostic (C2) on the CastFSR Wind protocol, executed according to the criteria written in advance.

## Summary

The three checks W1, W2 and W3 all pass. A training-segment power curve that uses only the measured wind speed `ture_w_speed` over the forecast horizon (D2) has a z-MSE m2 = 1.1997, lower than the 1.596 of CastFSR-Zero (and lower than 2.291). By the reading written in advance, this falls in the class m2 <= 1.596 and **supports** the statement "if the reported numbers come from the public code path, the Wind result may be determined mainly by test-period information under the public code path". This is a diagnosis of the code path and an assertion about the behaviour of the authors is outside its scope.

## Numbers (101 windows x 96 steps, z-score with training-segment mean and population standard deviation ddof=0)

| Model | z-MSE (ddof0, main) | z-MSE (ddof1, note) | Window MSE min / median / max |
|---|---|---|---|
| P0 persistence | 3.7008 | 3.7007 | 0.0000 / 2.1502 / 15.0717 |
| D1 forecast-wind-speed power curve (available information) | 1.9365 | 1.9364 | 0.0485 / 1.4179 / 7.7084 |
| D2 measured-wind-speed power curve (not available at forecast time) | 1.1997 | 1.1997 | 0.0000 / 0.7185 / 4.7762 |

Reference (paper Table 1, Wind): CastFSR-Zero 1.596, CastFSR-R1 1.757, without slow thinking 2.310, Chronos-2 / best non-LLM baseline 2.291.
D1 - D2 = 0.7367 (descriptive): measured wind speed brings a z-MSE gap of about 0.74 over forecast wind speed. D1 (1.9365) itself lies between 1.596 and 2.291, so a power curve using only the forecast wind speed is better than all non-LLM baselines of the paper and worse than CastFSR-Zero. By the criteria this is descriptive only and is not used for the reading.

## Checks

- **W1 pass**: N = 48,673 rows; first 2020-01-01 00:00, last 2021-05-22 00:00; no step other than 15 minutes; missing or non-numeric values are 0 in each column.
- **W2 pass**: P0 z-MSE = 3.7008, interval [0.7637, 6.8730].
- **W3 pass**: the correlation of `ture_w_speed` with the target is largest at lag 0 (0.81216), 0.79371 / 0.79485 at lag +-1, and decreases monotonically with |lag|. The largest correlation of `pred_w_speed` is at lag +2 (0.60076), and 0.59762 at lag 0 (an additional observation, not a check).

Full lag table (corr(target[t], speed[t+lag]), training segment):

| lag | ture_w_speed | pred_w_speed |
|---|---|---|
| -8 | 0.64403 | 0.54143 |
| -7 | 0.66348 | 0.55127 |
| -6 | 0.68388 | 0.56058 |
| -5 | 0.70485 | 0.56911 |
| -4 | 0.72624 | 0.57671 |
| -3 | 0.74829 | 0.58347 |
| -2 | 0.77160 | 0.58929 |
| -1 | 0.79485 | 0.59405 |
| 0 | 0.81216 | 0.59762 |
| 1 | 0.79371 | 0.59988 |
| 2 | 0.77060 | 0.60076 |
| 3 | 0.74799 | 0.60015 |
| 4 | 0.72589 | 0.59819 |
| 5 | 0.70373 | 0.59495 |
| 6 | 0.68266 | 0.59049 |
| 7 | 0.66265 | 0.58497 |
| 8 | 0.64363 | 0.57859 |

## Index check

- N = 48,673; training segment = rows 0..34070 (nTrain = 34071, last timestamp 2020-12-20 21:30).
- The first origin index is 38976, timestamp 2021-02-10 00:00 (as expected). The last origin is 48576 (2021-05-21 00:00). The last scored row is 48671, timestamp 2021-05-21 23:45 (as expected). There are more than 96 steps of look-back before the first origin.
- The target has no missing values inside the windows.

## Self-checks

- (a) P0 was computed twice by two independent code paths, a PowerShell loop and C# (Add-Type). The total z-MSE is 3.70084728713386 in both, the difference is 0, and the maximum per-window difference is 0, which meets 1e-9.
- (b) Training target mean 15.124873411405771, std (ddof0) 18.280940371777728, std (ddof1) 18.281208654816048, 34071 valid training targets. D1 has 40 non-empty bins (bin numbers 0..40, i.e. 0-20.5 m/s, 1 empty bin in range). D2 has 46 non-empty bins (bin numbers 0..48, i.e. 0-24.5 m/s, 3 empty bins in range). Each has 8 sparse bins with fewer than 5 training rows. Every bin of every forecast point in the test period is non-empty in the training segment (the counts of "falls into an empty bin" are 0 for D1 and D2), so the "nearest non-empty bin" rule was not used in scoring.
- (c) See the window MSE min/median/max in the table above.
- (d) The 7-day block bootstrap was not run, as specified.
- Number of missing-value backfills: P0 = 0, D1 = 0, D2 = 0.

## Details decided during execution

1. Dates are parsed as `yyyy/M/d H:mm`. Numbers use InvariantCulture. Empty or unparsable fields are treated as missing (none occurred).
2. Correlation: t is inside the training segment, and t+lag is also restricted to the training segment 0..nTrain-1 (no test-period data is borrowed). Pairs with missing values are dropped (none occurred).
3. W3 is read as: among lags -8..+8, the lag with the largest signed correlation of `ture_w_speed` lies in {-1, 0, +1}.
4. Bin = floor(x/0.5); the target mean in the bin on the training segment. An empty bin takes the nearest non-empty bin, and the lower bin if the distances are equal.
5. The "last observation before the origin" of P0 is the target value of row origin-1 (if missing, the nearest valid value looking backwards; none occurred).
6. The z-MSE with ddof=1 is recomputed with the same forecasts and only the standard deviation replaced.
7. The script must be run with `powershell.exe -File`. The CSV is first copied to a local temporary file (`<temp>/c2_wind_copy.csv`) and then read.
8. Per-window MSE is also written out: `c2_per_window.csv` (not required by the protocol, only for checking).

## Limitations (descriptive)

- This diagnostic shows only that the information in the measured wind speed over the forecast horizon is enough for a simple curve to reach or exceed the number of CastFSR-Zero. It does not show that CastFSR used this information. Whether the numbers of the paper come from the public code path cannot be judged from this diagnostic.
- The Chronos-2 value (2.291) and our P0 (3.70) are of the same order of magnitude. W2 shows only agreement in order of magnitude and does not show that the windows are identical to those in the paper.

## Files

- Script: `c2_wind.ps1` in this folder. Other outputs: `c2_results.csv`, `c2_per_window.csv`, `c2_log.txt` (in `<data>/castfsr/analysis_c2/`, not included here).
