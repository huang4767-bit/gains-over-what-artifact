# Re-check criteria, first round

These are the criteria written before the computations of this round.

They were written on 2026-11-16, before any computation of this round. Section numbers are kept as written. "No LLM is called" in Section 7 means that no step of the re-check computation queries an LLM.

## Criteria: uniform re-check (the same cheap no-LLM controls x each system's own evaluation protocol)

- Version: v1, 2026-11-16. No computation was run before this document was written.
- Any necessary change goes into a separate "post hoc" section with its date and reason.
- Basis: the feasibility assessment of the uniform re-check and its table of system protocols (`recheck/system_protocols.csv`).

### 1. The question

The main conclusion of the paper is that "the reported LLM advantage depends on how strong the control is, and strong controls are rarely reported". At present the support for "adding strong controls changes the conclusion" consists of 4-6 cases, each with a different control, and most of them come from one research group. This re-check applies the **same** set of cheap no-LLM controls under the evaluation protocols of systems from **several research groups**, and answers one question:

> Under the system's own protocol, can a cheap no-LLM control come within 5% of the value the system reports, or do better?

**This is a real test, and its result can go against the paper's claim.** An unfavourable result is also written into the paper as it is; see Section 6.

### 2. Systems in scope (core version, fixed)

| Group | Systems |
|---|---|
| A (read: control values under the same protocol are public) | TSOrchestra, MoiraiAgent (GIFT-Eval leaderboard), FASE (paper Table 1), TimeRSI (paper tables and fev-bench), MUSE-Bench (paper Tables 3/11) |
| B (rebuild: public data, CPU) | LLMTime, MemCast, LSTPrompt (only the 6 rows that overlap with Darts/Monash), CastFSR, JudgeCast, TimEvolve, KairosAgent |

- 12 LLM systems in total. The leaderboard entry of TimeCopilot has no LLM in its evaluation path; it **serves only as the same-pool control of MoiraiAgent** and is not counted as a system.
- The 5 systems of class C (TSci, Bridging, Informed Forecasting, Time-R1, FLAIRR-TS) are not done; the paper lists the reasons.
- No extension beyond the core version. N2F, CompEvo, CiK, Beyond Naive Prompting, and Nexus are only listed as "not covered".

### 3. Controls (fixed, not chosen by result)

| Code | Control | Applies to |
|---|---|---|
| R1 | Seasonal naive. The period is fixed in advance by data frequency: hourly 24, daily 7, weekly 52, monthly 12, quarterly 4, yearly 1; benchmarks with an official period keep it | all |
| R2 | Statistical ensemble: the **median** of the pointwise forecasts of AutoETS, AutoTheta, and AutoARIMA (statsforecast 2.1.1); at each forecast origin only data before that origin are used for fitting | all of class B; class A is read where values exist |
| R3 | Same-pool no-LLM control: the median ensemble of the system's own candidate pool, and the best single candidate | systems with a candidate pool: MoiraiAgent (TimeCopilot row, Chronos-2), TSOrchestra (best single model in the pool), FASE (Uniform Ensemble), CastFSR (experts of the model-selection stage) |

**Fallback rule for R2**: when the seasonal period exceeds 24 (e.g. the weekly period 168 of electricity prices), the daily period 24 is used throughout. When a model fails to fit at an origin, that origin uses the median of the other two models; if all three fail, R1 is used. All fallbacks are counted and reported.

**Main control of each system**:

- Systems with a candidate pool use **R3**, taking whichever of the pool median and the best single model the **system itself has reported** in the paper or on the leaderboard; when both have been reported, the best single model is used.
- All other systems use **R2**.
- R1 is reported for all systems as a lower reference.

### 4. Validity checks for each system (checks first, then results)

- **Baseline-consistency check**: under the reconstructed protocol, reproduce at least one no-LLM baseline number of the paper's own table (preferably seasonal naive or naive, otherwise ARIMA or ETS) with a relative error of at most 5%.
  - Class A is not recomputed; the check becomes a **source check**: confirm that the source and definition of the numbers on the leaderboard or in the paper agree.
  - Not passed: the system is recorded as "protocol unverified", reported separately, and **does not enter the main count**.
- **Metric-definition check**: error metric, aggregation, and normalisation agree with the paper and are stated item by item.
- **Window enumeration**: where the paper does not determine the test windows uniquely (the strides of MemCast and JudgeCast), a window family fixed in advance is used, and the median and the 5%-95% range are given.
  - MemCast keeps the already registered four-stride family and takes its "day-aligned" subset.
  - The stride family of JudgeCast is {24, 48, 72, 96} hours.

### 5. Quantity per system

- r = E(main control) / E(value reported by the system), in the paper's main metric and the paper's aggregation. r <= 1 means the control is no worse than the system.
- Bands: **"control matches"**: r <= 1.05, i.e. the control is within 5% of the reported value or better; **"system clearly ahead"**: r > 1.05.
- When a system reports on several datasets or settings, the geometric mean of the per-dataset r in the main metric is first taken **within the system** as its r; the r of each dataset is also reported.

### 6. Field-level reading (fixed in advance)

Let N be the number of systems that pass the baseline-consistency check (the source check for class A) (expected 8-12). A field-level conclusion is drawn only when N >= 6; otherwise the results are only described.

| Systems with "control matches" | Wording in the paper |
|---|---|
| >= ceil(N/2) | **"On most re-checked systems, under the system's own protocol, a cheap no-LLM control comes within 5% of the reported value or does better"**; supports the main conclusion |
| <= floor(N/4) | **"On most re-checked systems, the LLM systems are clearly ahead of cheap controls under their own protocols"**. This is evidence against the account "control strength determines the advantage": it is written as it is, the abstract and conclusion are rewritten accordingly, and the main conclusion is narrowed to a finding about reporting practice |
| otherwise | "Mixed result": only the per-system ratios and directions are reported, with no field-level direction |

- The results are also reported stratified by input category (category S (substantive) against categories M (metadata) and H (history only), with labels taken from the adjudicated results of the re-annotation), as description only, with no separate reading.
- Threshold sensitivity: counts at r <= 1.00 and r <= 1.10 are also given. If the three thresholds fall into different categories, the wording is "close", with no direction.
- Research groups: report how many independent research groups the systems that pass the baseline-consistency check come from. The systems of one research group are listed in a separate row of the results.

### 7. What is not done and not said

- No audited system is run, no LLM is called, and no author is contacted.
- Different metrics are not pooled across systems into one number.
- A cheap control that matches only shows that "the reported margin can be covered by a cheap control"; it does **not** mean that the LLM component contributes nothing, because the two sides receive different information.
- When a system is clearly ahead, the advantage is not attributed to the LLM component either.
- Leaderboard entries that flag themselves as affected by test-data leakage are not used. The date of reading the leaderboard is fixed to the day of execution and recorded.
