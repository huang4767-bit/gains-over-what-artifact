# Results for the weak references on MemCast (main protocol and sensitivity)

Source: the mechanical count under the criteria in `criteria_weak_references.md`. The summary outputs of the main protocol are in `out_spread96/`. The values below are MSE on the raw price scale over 30 windows x 24 hours.

## Validity check

Main protocol (`spread96`), `SN-1d` against the paper's best non-LLM baseline:

| Market | SN-1d MSE | Paper's best non-LLM | Ratio | Check (< 3x) |
|---|---|---|---|---|
| NP | 43.047 | ConvTimeNet 55.857 | 0.771 | passed |
| PJM | 40.345 | Prophet 63.342 | 0.637 | passed |
| BE | 557.953 | TimeXer 887.125 | 0.629 | passed |
| FR | 782.970 | TimeXer 876.179 | 0.894 | passed |
| DE | 447.487 | PatchTST 290.971 | 1.538 | passed |

All five markets pass; none is removed. On the 30 consecutive days of the public code layout, the naive baselines are an order of magnitude below the paper's errors on BE and FR; with windows spread over the test segment, the error scale matches the paper.

## Main protocol (`spread96`)

SameInfo is the same-information linear model; it was chosen by validation on training windows only, and the choice was Ridge-s in all five markets.

| Market | SameInfo MSE | Paper's best non-LLM | SameInfo / baseline | MemCast MSE | SameInfo / MemCast | R-3 MSE | R-3 / MemCast |
|---|---|---|---|---|---|---|---|
| NP | 52.295 | 55.857 | 0.936 | 36.871 | 1.418 | 120.769 | 3.275 |
| PJM | 84.791 | 63.342 | 1.339 | 30.238 | 2.804 | 157.649 | 5.214 |
| BE | 423.309 | 887.125 | 0.477 | 756.308 | 0.560 | 577.656 | 0.764 |
| FR | 335.776 | 876.179 | 0.383 | 756.981 | 0.444 | 652.708 | 0.862 |
| DE | 427.365 | 290.971 | 1.469 | 210.445 | 2.031 | 717.341 | 3.409 |

- **R1** (SameInfo against the paper's best non-LLM baseline; threshold: at least 4 markets better): SameInfo is lower in NP, BE, and FR, 3 of 5; not reached.
- **R2** (SameInfo against MemCast): SameInfo <= MemCast only in BE and FR, 2 of 5 (threshold 3; not reached). MemCast is better by 10% or more in NP, PJM, and DE, 3 of 5 (threshold 4; not reached). Neither branch reaches its threshold.
- **R3** (R-3 against MemCast; threshold: at least 3 markets with R-3 <= MemCast): only BE and FR, 2 of 5; not reached.
- **D1** (descriptive, not fixed in advance): `SN-1d` has MSE 43.047 in NP (0.771 times the baseline), 40.345 in PJM (0.637), 557.953 in BE (0.629), 782.970 in FR (0.894), and 447.487 in DE (1.538); relative to MemCast the ratios are 1.168, 1.334, 0.738, 1.034, and 2.126.

## Sensitivity (`spread48`)

SameInfo is again Ridge-s in all five markets.

| Market | SameInfo MSE | SameInfo / baseline | SameInfo / MemCast | R-3 / MemCast | SN-1d MSE |
|---|---|---|---|---|---|
| NP | 51.787 | 0.927 | 1.405 | 3.221 | 52.069 |
| PJM | 82.707 | 1.306 | 2.735 | 5.004 | 41.734 |
| BE | 868.913 | 0.979 | 1.149 | 1.479 | 1023.537 |
| FR | 939.304 | 1.072 | 1.241 | 1.792 | 1287.011 |
| DE | 436.827 | 1.501 | 2.076 | 3.269 | 426.924 |

- R1: 2 of 5 (NP and BE lower). R2, first branch (SameInfo <= MemCast): 0 of 5. R2, second branch (MemCast better by 10% or more): 5 of 5. R3: 0 of 5.
- The two window layouts differ on R2. Under `spread96`, neither branch of R2 reaches its threshold (3 of 5 and 2 of 5). Under `spread48`, the second branch is reached (5 of 5): MemCast has an increment over the same-information control. Whether the advantage of MemCast can be matched by a same-information linear model therefore depends on the window layout, and both layouts are reported.

## Further facts

SameInfo chose Ridge-s in all five markets and under all three layouts; the validation MSE on training windows (for example NP 11.534 against 10.896, DE 21.303 against 20.308) is identical across layouts because the training windows are fixed. In the first version of the script, the static LEAR-style model had MSE 1733 on DE; with the choice by validation, the Ridge model (MSE 283.832 under the 30-consecutive-days layout) is used instead. Under the layout of the public code (`code24`), all 45 MSE values (5 markets x 9 controls) of version 2 equal those of the first version (maximum absolute difference 0.0).