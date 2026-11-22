# Recheck, class A: values read from public result files

This file documents the class-A results of the uniform recheck (2026-11-16): control-to-system ratios recomputed independently from public result files, for four systems, with criteria written in advance.

The values were recomputed with PowerShell from public result files.

## Data sources

- **GIFT-Eval**: `huggingface.co/spaces/Salesforce/GIFT-Eval`, path `results/<model>/all_results.csv`, fetched 2026-11-16. Convention: for each configuration, `MASE[0.5]` and `mean_weighted_sum_quantile_loss` are divided by the value of Seasonal_Naive for the same configuration, then the geometric mean is taken over the 97 configurations.
- **fev-bench**: `github.com/autogluon/fev`, commit `9cf943c388e5cfaf352175ea3c69e408b197d997` (2026-11-11), path `benchmarks/fev_bench/results/{seasonal_naive,stat_ensemble,TimeRSI}.csv`. Convention: the MASE of each task divided by seasonal_naive, then the geometric mean.

## Check V1 (class A: source and convention of the numbers)

| System | Check | Result |
|---|---|---|
| MoiraiAgent | Recomputed the blog values 0.689 / 0.698 / 0.705 / 0.716 / 0.728 from the leaderboard: MoiraiAgent 0.6887, Chronos-2 0.6978, TimesFM-2.5 0.7050, TiRex 0.7158, Moirai2 0.7281 | pass |
| TSOrchestra | The leaderboard entry is the version without leakage (a separate entry, TSOrchestra-test, is self-labelled as leaking and was not used). The convention of the 25.5% in the paper is not defined and cannot be reproduced from the leaderboard. r is computed from the leaderboard values. | pass (source: leaderboard), with a note |
| FASE | Paper Table 1 and Table 3 taken verbatim from the verification record; convention is the geometric mean relative to seasonal naive over 29 configurations | pass |
| TimeRSI | Recomputed the MASE skill of TimeRSI over 100 tasks from the fev result files as 40.58; leaderboard value 40.579 | pass |

## r for each system (main control / system; r <= 1.05 is labelled "control matched")

| System | Main control (as fixed in the criteria written in advance, section 3) | Main metric | r | Category | Sensitivity and notes |
|---|---|---|---|---|---|
| MoiraiAgent | R3: the best single model reported by the system itself, Chronos-2 (the pool median is not reported) | GIFT-Eval MASE | 0.6978 / 0.6887 = **1.013** | **control matched** | CRPS: 0.4854 / 0.4756 = 1.021. No-LLM median ensemble of the same pool (TimeCopilot row): MASE 1.024 |
| TSOrchestra | R3: the best single model reported in the paper, Moirai-2 | GIFT-Eval MASE | 0.7281 / 0.6768 = **1.076** | **system clearly ahead** | With the stronger leaderboard model Chronos-2: 1.031 (matched). **The conclusion depends on which single model is the control.** The criteria use the one reported in the paper. CRPS against Moirai2: 1.103 |
| FASE | R3: the best single model reported in the paper, TiRex-2 (the equal-weight ensemble is also reported; the rule takes the single model) | MASE (first column of Table 1) | 0.728 / 0.679 = **1.072** | **system clearly ahead** | Against the equal-weight ensemble: 0.731 / 0.679 = 1.077. CRPS against TiRex-2: 0.489 / 0.497 = 0.984, the control is better |
| TimeRSI | R2: Stat. Ensemble (official fev-bench result file) | fev-bench MASE (96 common tasks) | 0.8293 / 0.5916 = **1.402** | **system clearly ahead** | No ready statistical-ensemble value exists on the TIME benchmark, so only fev-bench was read. Seasonal-naive floor: 1 / 0.5916 = 1.69 |
| MUSE-Bench | R2: no ready value in the paper or in public places | - | - | **pending** | Execution detail: in phase B, an attempt is made to rebuild R2 on its public datasets. Parts with private datasets cannot be rebuilt. If this fails, the system is recorded as "protocol not verified" and does not enter the main count. |

**Threshold sensitivity** (criteria section 6, counted by system):

| Threshold | Systems with control matched |
|---|---|
| r <= 1.00 | 0/4 |
| r <= 1.05 | 1/4 (MoiraiAgent) |
| r <= 1.10 | 3/4 (MoiraiAgent, TSOrchestra, FASE) |

The three thresholds give different categories, so the wording can only be "close".

## Notes

- These are partial results for four systems. **No domain-level conclusion is drawn.** The criteria require N >= 6 systems passing the check, to be read together after phase B is complete.
- Information tier: the GIFT-Eval arm of MoiraiAgent, FASE and TSOrchestra are M; TimeRSI is S (holiday rules). Under the criteria, the information tier is descriptive only.
