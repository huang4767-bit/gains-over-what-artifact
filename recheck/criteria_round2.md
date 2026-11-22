# Re-check criteria, second round

These are the criteria written before the computations of this round.

They were written on 2026-11-18, before any control error or ratio of these systems was computed. Section numbers, tables, and wording are kept as written. "No LLM is called" in Section 11 means that no step of the re-check computation queries an LLM.

Terms used below:

- Status words: "protocol unverified", "windows or data cannot be determined", "insufficient test" (the paper writes "the prediction is untested"), "close", and for the categories of the original reading rule "ahead (evidence against)", "match", and "mixed".
- Input categories (from the re-annotation of the first round): S (substantive), M (metadata), H (history only).
- Controls (defined in the first round, `recheck/round1/`): R1 is seasonal naive, R2 is the median of the pointwise forecasts of AutoETS, AutoTheta, and AutoARIMA, and R3 is the same-pool no-LLM control (the system's own candidate pool, as median ensemble or best single candidate). r = E(main control) / E(value reported by the system).
- Checks: the baseline-consistency check (reproduce a no-LLM baseline number of the paper's own table within 5%; for systems read from their papers, the source check), the metric-definition check, and window enumeration.

## Supplementary criteria: extending the uniform re-check to the five systems that the first-round criteria listed as "not covered"

- Version: **v2**, 2026-11-18. Revised according to an independent review of v1 (the review of v1, items M1-M9 and S1-S15) and the decisions of the authors.
- Revision record: v0 to v1 in the change log of v0/v1; v1 to v2 in the change log of v1/v2.
- Original criteria: the uniform re-check criteria of the first round (`recheck/criteria_round1.md`), written 2026-11-16 16:48. **The original is not changed.**
- Companion documents: the data pre-check of stage C; the report of the data pre-check (below "the report"); the review of v1 (below "the review").
- Basis: the feasibility assessment and `recheck/system_protocols.csv`; the literature verification notes, groups 2-4; the re-annotated system labels (`coding/`); the pre-check notes (section 0.1 and section 2.3) and the run instructions (R2 sentinel) of the first round (`recheck/round1/`); the final review, section 3; downloaded third-party files (read as text only, not executed).

### 0. Procedure (binding)

1. ~~Data pre-check~~: done (2026-11-18).
2. ~~Reading of the paper tables~~: done. Text only; no ratio computed.
3. ~~Fill in the items to be confirmed and record them in Section 13~~: done (v1).
4. ~~Independent review~~: done, conclusion "usable after changes". v2 implements all 9 required changes and decides the 15 suggestions one by one (Section 13).
5. The substantive changes of v2 are confirmed (Section 14).
6. Computation starts only once this document is complete (Section 12).
7. Only afterwards are the round-2 script and the run instructions written (including the unit tests of the scorer in 5.11), followed by code review, smoke test, and the formal run, using the template of the previous round.

### 1. Relation to the first-round criteria

1. **The original reading is unchanged and is not replaced.** The reading of the first-round criteria at N=8 is "close", and it is the **main reading** of the paper. No result of this second round rewrites, withdraws, or demotes it. "No extension beyond the core version" in the original section 2 refers to the scope of that document; this second round is a separate, dated set of criteria and does not write back into the original reading.
2. **Supplementary results are reported separately**: the r of each system, and the test of the category prediction in Section 7.
3. **The combined reading is a secondary reading** (Section 8).
4. **All rules of the original are kept; no control is added, and thresholds and the reading rule are not changed:**
   - definitions of R1, R2, R3, the period cap of 24, the fallback rule, and the assignment of main controls (original section 3);
   - the baseline-consistency check, the metric-definition check, and window enumeration (original section 4);
   - the definition of r and the geometric mean (original section 5);
   - thresholds and the reading table (original section 6);
   - what is not done and not said (original section 7);
   - execution details follow items 1-9 of section 0.1 of the first-round pre-check notes (`recheck/round1/`);
   - scope of the **magnitude check** (section 0.1, item 7 of those notes: the anchor ratio must lie between 1/3 and 3): it applies only to datasets with a reproducible anchor. It does not apply to systems without an anchor (BNP, N2F), whose descriptive r is computed anyway. If the anchor ratio of CiK falls outside 1/3-3, r is still computed but marked "magnitude check not passed" and treated as "protocol unverified".
5. The places that must be adjusted or fixed are listed one by one in Section 5. Each reason rests only on the protocol and the form of the data, never on a result.

### 2. Information known before writing (disclosed)

**2.1 Paper numbers already read.** These 5 systems were named "not covered" in the first-round criteria and are all the remaining systems of class B of the feasibility assessment; they were not chosen by result. But the numbers below were read before this document was written: some come from the literature verification, and on 2026-11-18 the full tables were read verbatim.

| System | Numbers already read (verbatim, see Section 6) | Meaning for r |
|---|---|---|
| CiK | Direct Prompt with context, minimum 0.159; ARIMA 0.475, ETS 0.530, Exp-Smoothing 0.605, Chronos-Large 0.326 | r far above 1.221, almost foreseeable |
| BNP | minimum cell of the paper's method 0.110; base forecasters 0.382, 0.492, 0.636 | same (not counted, 5.8) |
| Nexus | whole of Table 1 | the main control is an R3 reading, and **r can already be computed from the numbers in Section 6.3 before this document was written**. This document does not compute it; it is read out afterwards according to 5.4 |
| N2F | Table 3 has deep-model baselines only | cannot be inferred in advance (not counted, 5.5) |
| CompEvo | same baseline cells as N2F | by default no r is computed (5.7) |

**2.2 Expected outcome of the test of Section 7 after the pre-check (stated in advance).**

- The source check of Nexus (class A) **is judged as passed in these criteria** (5.4).
- Whether CiK is counted depends on whether the Exp-Smoothing anchor falls within 5% (5.9).
- BNP and N2F are "protocol unverified"; CompEvo is by default "windows or data cannot be determined".

Hence **K is 1 or 2**. By Section 7.2 the reading is "**insufficient test**". No check is relaxed to make K >= 3: no anchor that needs training is accepted, no anchor is borrowed from another paper, and no anchor implementation is swapped. The value of this second round lies mainly in **coverage**: the 5 most relevant systems were all examined, and each gets a status and a reason. It is **not** an informative out-of-sample test.

**2.3 How fragile the 5% tolerance of the CiK anchor is.**

- The aggregate is a weighted mean over 355 instances with weights summing to 105. If an instance of weight 1 changes its RCRPS by Delta, the aggregate changes by Delta/105.
- For example, if a single instance flips between "capped at 5" and "about 1" (Delta about 4), the aggregate moves by about 0.038, about 6% of 0.605.
- The paper's Table 6 records 5 significant failure instances for Exp-Smoothing.
- So a failed anchor does **not necessarily** mean that the protocol reconstruction is wrong. The paper is to say so.

**2.4 Direction of the system-value rule.** Every "system value" takes the cell most favourable to the system: the minimum for CiK and BNP, and per column the lower of the two versions for Nexus. This agrees with the C* precedent for CastFSR in the first-round re-check.

- For the question of the first-round criteria (can a cheap control match), this is **conservative**;
- for the prediction of Section 7 (r above the thresholds), it **favours the prediction**.

See 7.4.

### 3. Scope: the 5 systems, the arms used, and their input category

The input category is that of "the arm used", as for MoiraiAgent in the first-round re-check.

| ID | System | Research group | Arm used | Category | Control class | Status |
|---|---|---|---|---|---|---|
| S07 | CiK, arXiv 2410.18959v4 | ServiceNow | Direct Prompt (ours), with context | S | R2 (statistical ensemble) | depending on the anchor: counted or protocol unverified |
| S10 | Nexus, arXiv 2605.14389v2 | Google Cloud AI Research | Leaf main table (Table 1) | S | R3 (best single model of its own TSFM pool) | **source check judged passed, counted**; R1, R2 not available |
| S11 | N2F, arXiv 2409.17515v3 | Sydney / CUHK-SZ | Filtered News | S | R2 | protocol unverified, Electricity described only |
| S16 | CompEvo, arXiv 2609.09195v1 | Sun Yat-sen University | CompEvo main arm | S | (R2) | windows or data cannot be determined; conditional rule (5.7) |
| S21 | BNP, arXiv 2508.09904v3 | ServiceNow | the paper's CorDP method | S | R2 | protocol unverified, described only |

- The GIFT-CTX arm (Table 2) and the GIFT-Eval arm (Table 3) of Nexus are described only.
- CiK and BNP come from the same group and the same benchmark; their R1 and R2 are one computation, and the two are not independent.

### 4. Assignment of main controls (as in the original section 3; nothing new)

| System | Main control | Secondary (described only) |
|---|---|---|
| CiK | R2 | R1 |
| BNP | R2 (the base forecasters are the object being corrected, not a pool from which the LLM selects) | R1 |
| Nexus | R3: the best single model of the pool (Chronos-2, TimesFM-2.5, TiRex) | R1, R2 not available |
| N2F | R2 | R1 |
| CompEvo | R2 (computed only if the conditional rule is met) | R1 |

### 5. Places that must be adjusted or fixed (listed one by one, each with its reason)

**5.1 RCRPS scoring (CiK, BNP).** Code text relied on: `compute_rcrps_with_hf_dataset.py` of the CiK repository (below "the HF script"). **It is rewritten from the text; the original code is not run.**

1. **CRPS of a point forecast**: R1 and R2 are point forecasts, and their CRPS is |y - x|. The PWM estimator of the HF script has a zero denominator when the number of samples is n=1 (`:67`). Substituting n identical points into the PWM formula gives exactly |y - x| (checked in the review, section III.2).
2. **`metric_scaling` is always taken directly from the field of the HF dataset and not recomputed.** `scaling_cache.py` is used only to understand its meaning: its scaling is computed over 25 seeds and cannot be reproduced from the 5 instances in HF.
3. **Constraint term** (`:310-334`, `:405-412`):
   - the forecast is multiplied by `metric_scaling`; `constraint_min` and `constraint_max` are likewise multiplied by `metric_scaling` and used as they are;
   - min term = mean over **all forecast steps** of max(threshold - forecast, 0);
   - max term = mean over **all forecast steps** of max(forecast - threshold, 0);
   - variable-max term (when `constraint_variable_max_index` has length > 0) = mean, over **the indexed steps only**, of max(forecast - corresponding threshold x `metric_scaling`, 0);
   - the three terms are **added**, not averaged again; multiplied by 10, the CRPS against target 0 is taken. For a point forecast, the constraint term equals 10 x the sum of the three terms.
4. **RoI** (`:376-394`): when `region_of_interest` has length > 0, CRPS = 0.5 x mean(RoI steps) + 0.5 x mean(non-RoI steps); when it has length 0, CRPS = mean(all steps).
5. **RCRPS of each instance** = `metric_scaling` x CRPS + constraint term (`:420`). An RCRPS >= 5 is recorded as 5 (`:492-494`).
6. **Aggregation**: sum of Fraction(weight_i) x RCRPS_i / sum of Fraction(weight_i), computed row by row over the 355 instances (`:490-501`). `weight` is a fraction string, parsed with Fraction; the weights sum to 105. This is the same as "each cluster weighted equally, each task within a cluster weighted equally" in the paper's A.6.
7. **The control forecasts are not truncated or clipped** (for example, not forced to be non-negative), because clipping would use the constraint information in the context.
8. **Direction of the bias, both sides written**: the CRPS of a single-point distribution is usually higher than that of a forecast distribution with the same centre, which **raises** r.
   - For the question of the first-round criteria (can a cheap control match), this is the **conservative** direction, the same as the "period cap of 24";
   - for the category prediction of Section 7, it is the direction that **favours the prediction**.

   So CiK meeting P1 or P2 cannot be taken as evidence for the category pattern (K <= 2, hence insufficient test, also guarantees this). The paper states both sides in the main text.

**5.2 Seasonal period of CiK (fixed).**

- Values of `seasonal_period` in the dataset: -1 in 190 rows, 24 in 120 rows, 7 in 45 rows (report section 3.2, 3b).
- **Meaning of -1**: line 88 of the HF README literally says "-1 if there is seasonal periodicity", evidently missing a "no"; it is a typo. Following the semantics of the code it is read as "no seasonality": `statsmodels.py.txt:68` says "If seasonal_periods is <= 0, then the seasonal component is skipped", `:80` has `seasonal ... if seasonal_periods >= 1 else None`, and `r_forecast.py.txt:88` has `max(1, seasonal_periods)`. Precedent: section 0.1, item 1 of the first-round pre-check notes sets "m=1 for series without calendar seasonality".
- **R1**: for the values 24 or 7, m is that value, i.e. the "official period" of the original section 3; for -1, m=1. Formula: y_hat(T+h) = y(T+h-m*ceil(h/m)), as in the first-round script. When the history is shorter than m, R1 of that instance degenerates to naive (m=1), and this is counted.
- **R2**: season_length = min(m, 24); 1 for -1. When the history is shorter than m, there is **no degeneration**: min(m, 24) is passed throughout and statsforecast handles it; failures follow the fallback rule of the original section 3 and are counted. The fitting input is a numpy one-dimensional array of the target column of `past_time` (integer positions), independent of the timestamp frequency; second-level, 10-minute, and monthly data need no special treatment. The sentinel follows the first-round run instructions: stop if all three models fail in the first 20 fits; also stop if one model fails every time. Execution follows the row order of the parquet file.
- **Sensitivity (described only)**: the instances with -1 take their period from a frequency table instead; the full table is h 24, D 7, MS 12, 10min 144, s 1. The frequency is inferred from the timestamps of `past_time`, in the same way as in the pre-check. R2 still takes min(m, 24).

**5.3 Reported system values.**

- **CiK**: the minimum with context of the paper's own method **Direct Prompt (ours) = 0.159 +/- 0.008** (Llama-3.1-405B-Inst; Table 1 and appendix Table 3 agree). The rule of v1 was "the minimum over all LLM methods with context", which included other methods such as llmp and UniTime and was asymmetric with the rule for BNP. v2 takes the paper's own method only. **This rule was changed after reading the table**; the value is unchanged (both rules give 0.159), and this is disclosed.
- **BNP**: the minimum over the cells of the paper's methods (Median-CorDP, SampleWise-CorDP) in the main Table 1 = **0.110**. The SampleWise-CorDP (Chronos Large) cells of Claude-Sonnet-4.5 and Gemini-2.5-Pro tie. Table 1 has no IC-DP or RouteDP columns; the DP columns are described only. This rule was confirmed on 2026-11-18.
- Both papers have a single aggregate number, so the system r is that one ratio.

**5.4 Nexus: R3 reading; source check judged in these criteria.**

- **Pool**: Chronos-2, TimesFM-2.5, TiRex (section 3.1; report section 3.4).
- **Main metric**: as stated in the Nexus text: "we report MAPE and RMSE, substituting MAE (degrees C) for MAPE on Weather whenever temperatures cross zero" (Nexus paper, section 4.1, Metrics). That is, MAE on Weather and MAPE (%) on the other 5 columns. RMSE is described only.
- **System value**: per column, the lower of Nexus (Gemini-3.1-Pro) and Nexus (Claude-Sonnet-4.5). The rule agrees with C* for CastFSR, and its direction favours the system (2.4). By the values in Section 6.3, the lower of the two is the Gemini version in all 6 columns.
- **Best single model**: the one model used for all 6 columns, the one with the smallest "geometric-mean ratio to the system value". Ties are broken in the order Chronos-2, TimesFM-2.5, TiRex. It is computed and recorded after these criteria are written.
- **Sensitivity (described only)**: take the best single pool model separately for each column, then compute r.
- **Source check (class A): judged passed**. The four criteria, checked one by one, are all met:
  1. The three pool models and the two Nexus versions are all in the same table (Table 1) (Nexus paper, Table 1 of section 4).
  2. Shared windows: the caption of Table 1 says "Forecasting error on Leaf across shared evaluation windows"; the caption of Table 6 says "Windows is the number of forecast windows scored in Table 1 for Nexus and all baselines"; the text says "We use the benchmark's own forecast windows".
  3. The metric is defined in one place: see the Metrics passage above.
  4. The numbers of the three pool models in Table 1 are **not** marked as taken from elsewhere: the Baselines paragraph of section 4.1 lists them as "(iii) Zero-shot foundation models: TimesFM-3.0 and TimesFM-2.5, Chronos-2, Chronos-Bolt, TiRex, and Moirai-2.0" with no source mark; a full-text search for "taken from", "reported by", "copied", "from the original" gives 0 hits. Table 2 carries a dagger mark, but it concerns GIFT-CTX only, not Table 1.

  This judgement **rests only on the text above**; no ratio was read or computed. **It is not judged again later**; only the R3 ratio is recorded.
- **R1, R2**: Leaf is a living benchmark without a fixed version (report section 2.5), recorded as "not available". This does not affect the class-A check.

**5.5 Baseline-consistency check of N2F and CompEvo.** The baselines of both papers need training; the N2F repository has no baseline forecast files; Darts and torch are not available locally (report section 2.1, section 3.1, section 1.1). It was confirmed on 2026-11-18 that a DLinear anchor is not accepted, so both are recorded as "**protocol unverified**", as were TimEvolve and KairosAgent in the previous round.

**5.6 N2F: Electricity only.**

- **Windows**: the 100 windows of `AULF_test_data_2021.json`, covering several states, dated 2021-01-18 to 2021-12-30 (report section 2.1, section 3.1, 1c).
- **Parsing rule**: numbers are taken in order from the fields `instruction` and `output` separately with the regular expression `-?\d+(?:\.\d+)?`, the same split as in the pre-check; it is asserted that `instruction` and `output` of every window have exactly 48 numbers each, and the run stops otherwise (structure check); the 48 numbers of `instruction` are the history and the 48 of `output` the truth.
- **Exchange, Traffic, Bitcoin**: windows cannot be determined (`README.md`:37-39; no split code in the repository; report section 3.1, 1d).
- **Main metric**: RMSE on the original scale, the squared errors of 100 x 48 = 4,800 points pooled before the square root (`accuracy-ts.py`:282-286).
- **Fitting history of R2**: the 48 points given by the window. Period m=48; R2 uses 24.
- **System value**: Electricity RMSE 280.39.
- **The "full-history sensitivity" of v1 is deleted**: suggested defining "matches the CSV"; **not adopted**, the whole item is deleted instead. Reason: N2F is described only and enters no count; this sensitivity analysis would fit AutoARIMA on about 35,000 points, which is costly, and would need extra criteria for "matches" and for truncation; the added degrees of freedom contribute nothing to any reading.

**5.7 CompEvo: windows or data cannot be determined; with a conditional rule fixed in advance.**

- **Default**: the public AEMO file (released with N2F) does not match the description in appendix D.1 of CompEvo (report section 2.2), and the paper does not give the look-back length L. Recorded as "**windows or data cannot be determined**"; no r is computed.
- **Conditional rule**: in the execution phase, the repository `github.com/Aliiina-z/CompEvo` is read as text and no code is run; **the commit is the head of the default branch on the day of execution** and is recorded. Only if **all 7** of the following hold does the "matching" branch apply:
  1. the electricity data provided by the repository have **exactly** 52,560 points and **exactly** 19 variables, and the region agrees with D.3 (VIC);
  2. the look-back length L is uniquely determined by the repository: the main experiment script or configuration has only one value; if there are several, the one named by the README or the paper is taken; if none is named, the condition is not met;
  3. the test segment or test windows are uniquely determined, **including the window stride**;
  4. the target column is uniquely determined;
  5. the forecast length is 48;
  6. the error is computed on the original scale (a repository that computes errors on the standardised scale does not meet this);
  7. all of the above come from the same recorded commit.
- **If "matching"**: R1 and R2 are computed on the repository's data and windows; the fitting history of R2 equals L; main metric RMSE; the system value is the Electricity RMSE of CompEvo in Table 1, 354.18 (mean of 5 runs). The baseline-consistency check still follows 5.5: it passes only if the repository contains the authors' baseline forecast files and a baseline cell of Table 1 is reproduced within 5% (P-type). **If it passes only through a P-type anchor**, K and N_comb are both reported "with" and "without CompEvo", following the precedent of LSTPrompt in the first-round re-check.
- If any condition is not met: it stays "cannot be determined".
- The verification record must be written to the execution report before any R1 or R2 of CompEvo is computed.

**5.8 BNP: protocol unverified; the anchor of CiK is not borrowed.**

- **Facts**: all 71 tasks are used; the numerical series of the two splits are identical row by row, so R1 and R2 do not depend on the split; the only no-LLM anchor that is not a foundation model, arima 0.636, uses R `forecast::auto.arima`. There is no R environment locally, so it cannot be reproduced (report section 2.4, section 3.3).
- **Handling**: recorded as "**protocol unverified**". R1 and R2 are computed together with CiK and only described; they enter neither K nor N_comb.
- **The anchor of CiK is not borrowed**, for two reasons: (1) the baseline-consistency check tests whether our reconstructed protocol reproduces a number in **that paper's own table**; (2) on the same 71 tasks, the three base forecasters reported by BNP all differ from the same-named models reported by CiK: Lag-Llama 0.382 against 0.327, Chronos-Large 0.492 against 0.326, arima 0.636 against ARIMA 0.475. So the evaluation pipelines of the two papers differ in at least one place, and that difference also acts on BNP's system value.

**5.9 Anchor of CiK: Exp-Smoothing only, one implementation, fixed.**

- **Anchor**: Exp-Smoothing **0.605 +/- 0.013** (Table 1, Table 3).
- **ARIMA 0.475 and ETS 0.530**: both are implementations of the R `forecast` package through rpy2 (appendix D.10; `r_forecast.py.txt`:88-94, 169-207), not reproducible locally; recorded as "**this anchor type cannot be reproduced**", and not approximated with statsforecast or statsmodels.
- **Implementation** (following `statsmodels.py.txt`:57-90 and appendix D.9; places marked "our convention" are not in the code):
  1. `statsmodels.tsa.holtwinters.ExponentialSmoothing`. `endog` is the target column of `past_time` as a **numpy float64 one-dimensional array** (our convention, to avoid frequency inference on second-level and monthly indexes; the values are the same as in the code).
  2. `trend="add"`; `trend=None` when `len(past) < 5` (`:72`).
  3. `seasonal_periods` is taken from the instance field; it is set to -1 when `len(past) < 2 * seasonal_periods` (`:74-75`); `seasonal="add" if seasonal_periods >= 1 else None` (`:80`); `seasonal_periods` is passed as in the code (`:81`). **The only interface repair stated in advance**: if statsmodels 0.15.0 raises an error on `seasonal_periods=-1` in the smoke test, `seasonal_periods=None` is passed when `seasonal=None`. This does not change the model and is noted in the acceptance check. No other change is allowed.
  4. `result = model.fit()`, all defaults.
  5. `result.simulate(nsimulations=len(future_time), repetitions=25, random_state=np.random.default_rng(int(seed)))`. `n_samples = 25` is the default of `run_baselines.py` (`:379-384`). **`random_state` is our convention**: the CiK code does not pass this argument at `:86-87`. A new Generator is created before each instance, not shared across instances; no `RandomState`, no global seed.
  6. Scored as in 5.1 (PWM formula, n=25) and aggregated as in 5.1.
  7. **Failed instances**: if fitting or sampling raises an error or the output is not finite, the RCRPS of that instance is recorded as 5 (the same as "significant failure") and counted; it is not refitted with other settings. Warnings such as `ConvergenceWarning` are ignored and only counted. The CiK code drops failed instances at `run_baselines.py.txt`:352-362; we do not, because the HF aggregation needs all 355 instances.
- **Fixed environment**: Python 3.14.2, statsmodels 0.15.0, numpy 2.5.4, pandas 2.3.3, statsforecast 2.1.1 (report section 1.1). No version change; no change to the `trend`, `seasonal`, `n_samples`, or `fit` arguments; no switch to `ETSModel`.
- **Judgement**: with the **unrounded** computed value, |anchor/0.605 - 1| <= 0.05 passes (5.12). Not passed: CiK is recorded as "protocol unverified", enters neither K nor N_comb; r is computed and only described.
- **Closing the route of "swapping the implementation until it fits"** (applies equally to the scoring of R1 and R2):
  1. **The baseline-consistency check is judged only on the anchor value of the first formal run.**
  2. **The smoke test runs at most 10 instances and prints no aggregate value of the anchor, nor any aggregate value of R1 or R2 or any r**; it only checks that the code runs and counts.
  3. The scorer must pass the unit tests of 5.11 before the formal run.
  4. If, after the anchor value has been seen, an error is found in the scorer or the anchor code: the corrected value is reported together with the original value and marked "post hoc correction". The baseline-consistency check, K, and N_comb all follow the first formal run. A correction of the scorer also changes the RCRPS of R1 and R2, and both sets of r are reported.
- **Description (does not change the baseline-consistency check)**: the anchor is rerun with 20 further seed offsets (seed + 1000*j, j=1..20), and the median and 5%-95% range of the 21 runs are reported.
- **Use of `results/results_complete.csv`**: **not downloaded or read during execution.** If it is to be used later, only after the baseline-consistency judgement and all R1, R2, and r have been written to disk; at the fixed commit 73f46016f8c5643bf6799ca31875eab3e8d0d075, read as text only. Only one thing is done with it: for the per-task values already in the file (ARIMA, ETS, Exp-Smoothing), the weighted mean is computed with our aggregation function and compared with the paper's 0.475, 0.530, 0.605. The result is marked "**post hoc**" and does not change the baseline-consistency check, K, or N_comb. Any change to the implementation after the file has been seen is reported with old and new values, as in item 4 above.
- **Known risks**: the CiK code commit (2026-02-11) is later than paper v4; the paper's 0.605 is itself one random realisation with 25 samples; the optimiser defaults of statsmodels may differ from those of the authors' version; the tolerance itself is fragile (2.3).

**5.10 Sensitivity analyses specified in advance (described only; they change no reading).**

- R2 with the original period, i.e. the approach of the post hoc analysis with the original seasonal periods (`recheck/round1/out_posthoc_native_period/`). In this second round only N2F is affected (m=48).
- The -1 periods of CiK taken from the frequency table (5.2).
- The seed distribution of the CiK anchor (5.9).
- The per-column best pool model for Nexus (5.4).
- sqrt(r): no system in this second round has a squared-error metric (CiK uses RCRPS, Nexus MAE/MAPE, N2F RMSE), so this item applies only to the original 8 systems; for them it is a **post hoc description**, not fixed in advance.

**5.11 Unit tests of the scorer (written into the run instructions, synthetic data only, must pass before the formal run).**

1. On random synthetic samples, the PWM formula agrees with the slow definitional formula in the CiK repository's CRPS test (`tests/test_crps.py`) (relative difference < 1e-9).
2. n identical points substituted into the PWM formula give |y - x|.
3. Three hand-computed examples: one with RoI, one with min/max constraints, one with a variable-max constraint.
4. Capping: an RCRPS >= 5 is recorded as 5.
5. Fraction-weight aggregation: one hand-computed example with 3 instances.

The tests do not read the HF data and output no value of any real instance.

**5.12 No rounding in threshold comparisons.** The **unrounded** computed values are always compared with the literal values of the constants in these criteria: anchor |anchor/0.605 - 1| <= 0.05; prediction r > 1.221, r > 1.10, r > 1.405; original reading r <= 1.00, r <= 1.05, r <= 1.10; magnitude check 1/3 <= ratio <= 3. Reports keep three decimals, but the judgement is not affected by rounding.

### 6. Protocol per system (paper numbers copied verbatim)

**6.1 CiK (S07).**

Data: HF `ServiceNow/context-is-key` at commit 32da467ade142a16d099675e78b1129745c5ef7d, apache-2.0; `data/ICML2025-00000-of-00001.parquet`, 213,493 B.

Split: ICML2025; its numerical values are identical row by row to the test split, differing only in the `scenario` of 3 tasks.

Structure check (all must hold, otherwise stop, see Section 9): 355 rows, 71 tasks, 5 seeds per task, (name, seed) unique; weights sum to 105; `past_time` and `future_time` strictly increasing in timestamp after parsing; unique target column; the RoI indices all in [0, H), without duplicates, and not covering all H steps; print the number of finite values in `constraint_min/max` (counts only, no values).

Lengths: past 3/48/287, future 6/24/99 (minimum/median/maximum).

System value: **0.159 +/- 0.008**, Direct Prompt (ours) Llama-3.1-405B-Inst (Table 1; Table 3). Other with-context values of Direct Prompt (ours): Llama-3-70B-Inst 0.286, Llama-3-8B-Inst 0.461, Mixtral-8x7B-Inst 0.523, Qwen-2.5-7B-Inst 0.290, Qwen-2.5-1.5B-Inst 0.575, Qwen-2.5-0.5B-Inst 0.463, GPT-4o 0.274, GPT-4o-mini 0.354. Values of other methods such as llmp and UniTime are in v1 of these criteria or in appendix Table 3 of the CiK paper (v4) and do not enter the rule.

R2, R1: as in 5.1 and 5.2. Baseline-consistency check: Exp-Smoothing 0.605 +/- 0.013, as in 5.9; ARIMA and ETS cannot be reproduced.

CPU: about 2,130 fits, plus the anchor reruns with 20 seed offsets (about 21 x 355 fits), in total less than 1 core-hour.

**6.2 BNP (S21).**

Data: as for CiK, all 71 tasks.

System value: **0.110**. All cells of the paper's methods in Table 1 follow (Median-CorDP and SampleWise-CorDP, each with the base forecasters Lag-Llama, Chronos Large, and arima):

| LLM | Median-CorDP, Lag-Llama | Median-CorDP, Chronos Large | Median-CorDP, arima | SampleWise-CorDP, Lag-Llama | SampleWise-CorDP, Chronos Large | SampleWise-CorDP, arima |
|---|---|---|---|---|---|---|
| Llama3.2-1B-Inst | 0.394 | 0.515 | 0.612 | 0.541 | 0.634 | 0.672 |
| Llama3.2-3B-Inst | 0.344 | 0.455 | 0.573 | 0.509 | 0.423 | 0.663 |
| Llama3-8B-Inst | 0.315 | 0.453 | 0.571 | 0.426 | 0.410 | 0.636 |
| Llama3.3-70B-Inst | 0.281 | 0.251 | 0.352 | 0.223 | 0.215 | 0.311 |
| Llama3.1-405B-Inst | 0.278 | 0.226 | 0.257 | 0.199 | 0.194 | 0.229 |
| Qwen2.5-0.5B-Inst | 0.633 | 0.801 | 0.761 | 0.494 | 0.644 | 0.655 |
| Qwen2.5-1.5B-Inst | 0.426 | 0.537 | 0.682 | 0.522 | 0.474 | 0.719 |
| Qwen2.5-3B-Inst | 0.490 | 0.491 | 0.597 | 0.398 | 0.451 | 0.512 |
| Qwen2.5-7B-Inst | 0.419 | 0.641 | 0.633 | 0.382 | 0.402 | 0.540 |
| Qwen2.5-14B-Inst | 0.315 | 0.334 | 0.423 | 0.364 | 0.410 | 0.471 |
| Qwen2.5-32B-Inst | 0.248 | 0.272 | 0.329 | 0.310 | 0.338 | 0.414 |
| Qwen-2.5-72B-Inst | 0.319 | 0.358 | 0.428 | 0.255 | 0.322 | 0.386 |
| GPT-4o | 0.253 | 0.240 | 0.354 | 0.184 | 0.196 | 0.251 |
| GPT-4o-mini | 0.364 | 0.340 | 0.516 | 0.302 | 0.296 | 0.415 |
| GPT-5.2 | 0.246 | 0.167 | 0.285 | 0.201 | 0.235 | 0.276 |
| Claude-Sonnet-4.5 | 0.299 | 0.213 | 0.242 | 0.162 | **0.110** | 0.217 |
| Gemini-2.5-Pro | 0.157 | 0.123 | 0.166 | 0.130 | **0.110** | 0.145 |

Described only: the DP columns (for example Claude 0.114, Gemini 0.108); base forecasters Lag-Llama 0.382 +/- 0.011, Chronos Large 0.492 +/- 0.004, arima 0.636 +/- 0.014. Baseline-consistency check: protocol unverified (5.8).

**6.3 Nexus (S10).**

Data: Leaf not available (living benchmark, no fixed version).

Windows: Weather 620, Electricity 453, Eq-3d 1,319, Com-3d 1,320, Eq-7d 440, Com-7d 440 (Table 6).

Source check: **passed** (class A, by the four criteria of 5.4). Main control: R3, read out as in 5.4.

Table 1 main metric (verbatim; Weather is MAE, the other five columns are MAPE: Elec, Eq-3d, Com-3d, Eq-7d, Com-7d):

| Model | Weather MAE | Elec | Eq-3d | Com-3d | Eq-7d | Com-7d |
|---|---|---|---|---|---|---|
| TimesFM-2.5 | 2.770 | 6.939 | 2.245 | 2.755 | 3.235 | 3.757 |
| Chronos-2 | 2.659 | 6.189 | 2.046 | 2.628 | 3.115 | 3.762 |
| TiRex | 2.675 | 6.697 | 2.068 | 2.606 | 3.111 | 3.695 |
| Nexus (Claude-Sonnet-4.5) | 2.052 | 5.821 | 2.070 | 2.543 | 3.069 | 3.668 |
| Nexus (Gemini-3.1-Pro) | 1.970 | 5.305 | 1.958 | 2.488 | 2.994 | 3.434 |

Table 1 RMSE (described only):

| Model | Weather | Elec | Eq-3d | Com-3d | Eq-7d | Com-7d |
|---|---|---|---|---|---|---|
| TimesFM-2.5 | 3.888 | 1689.9 | 11.432 | 37.407 | 16.332 | 56.004 |
| Chronos-2 | 3.753 | 1524.6 | 10.638 | 34.428 | 16.045 | 54.467 |
| TiRex | 3.800 | 1632.8 | 10.746 | 32.574 | 15.901 | 51.199 |
| Nexus (Claude-Sonnet-4.5) | 2.802 | 1390.6 | 10.678 | 34.097 | 16.132 | 50.731 |
| Nexus (Gemini-3.1-Pro) | 2.717 | 1309.9 | 10.272 | 31.461 | 15.341 | 48.610 |

**6.4 N2F (S11).**

Data: `github.com/daydreamer-amelia/From_News_to_Forecast` at commit c285bc0744b5a21a3119cfb7042f5783e4a437d0, MIT; `AULF_test_data_2021.json`, 153,249 B.

Structure check: 100 windows, and `instruction` and `output` of each window have exactly 48 numbers each (5.6).

System value: Electricity RMSE **280.39** (Table 1 Filtered News; Table 3 Ours). Baseline-consistency check: protocol unverified.

**6.5 CompEvo (S16).**

The default status is "windows or data cannot be determined". During execution, the 7 criteria of 5.7 are checked; if they are met, the system value is the Electricity RMSE 354.18.

### 7. Predictions written in advance (the core of this second round)

**7.1 Prediction.** In the first-round re-check at N=8 it was seen post hoc that the largest r of categories H and M is 1.221 (LSTPrompt, main version), and that category S lies at 1.347-1.767. **If this pattern holds**, the new category-S arms of this second round that pass the baseline-consistency check (the source check for Nexus) should satisfy **P1**: r > 1.221; **P2**: r > 1.10. Both constants are fixed now; the judgement follows 5.12, without rounding.

**7.2 Test rule.** Let K be the number of new systems that pass the baseline-consistency check (the source check for Nexus) and whose arm used is category S, a the number of them that meet P1, and b the number that meet P2.

| Condition | Reading |
|---|---|
| K <= 2 | **insufficient test**: only the r of each system and whether it meets P1 and P2 are reported |
| K >= 3, a >= K-1, and b = K | **supported** |
| K >= 3, a <= floor(K/2), or K-b >= 2 | **not supported** |
| K >= 3, otherwise | **partly supported** |

For each K: K=3: supported requires a >= 2 and b = 3; not supported is a <= 1 or b <= 1. K=4: supported requires a >= 3 and b = 4; not supported is a <= 2 or b <= 2. K=5: supported requires a >= 4 and b = 5; not supported is a <= 2 or b <= 3.

If CompEvo passes only through a P-type anchor, the reading is made once for each version (5.7).

After the pre-check, K is 1 or 2 (2.2), and the reading will be "insufficient test".

**7.3 Descriptions reported at the same time (they do not change the reading of 7.2).**

1. ServiceNow combined: CiK and BNP as one unit, taking the smaller r.
2. The descriptive r of N2F (Electricity) and BNP and whether they meet P1 and P2, marked "protocol unverified, not counted"; for CompEvo, the status and the reason.
3. Among the new category-S systems, how many have r > 1.405 (the r of LSTPrompt on the anchor subset in the previous round).
4. The sensitivity analyses of Section 5.10.

**7.4 Confounds and biases (must be written into the paper).**

- **Domain and benchmark design**: the benchmark of CiK and BNP was built from tasks that "must use textual context" (caption of CiK Figure 2), so controls that use the history alone are bound to lose under this design. The original category-S systems are electricity prices and fev-bench; the new ones are textual context and event records. Input category, domain, and benchmark construction are mixed together.
- **Different control classes**: CiK uses R2 (statistical ensemble), Nexus uses R3 (best single model of its own TSFM pool); the two r are not the same quantity.
- **Two settings that favour the prediction**: single-point RCRPS raises the r of CiK (5.1, item 8); every system value takes the cell most favourable to the system (2.4). Both are conservative for the question of the first-round criteria, but both are in the direction that **favours** the prediction of Section 7.
- **Known information**: see Section 2.
- **Metrics**: the main metrics differ across systems; they are not combined across metrics into one number.
- Following the original section 7, whatever the result, nothing is attributed to the LLM or to the input.

**7.5 Wording in the paper (English templates).**

**General conventions**: the angle brackets are filled in at the time. **No system may be presupposed to meet P1 or P2.** When met, only "meets the threshold" may be written; under an insufficient test, "but is not a test" must be added. The definition of r is written out each time.

**Common opening** (used in every case):

> "A second set of criteria, written on <date> before any computation, extended the re-check to the five systems the first one listed as not covered (all category S). It predicted that, if the category pattern seen in the first re-check holds, each new system that passes the validity check (anchor reproduction, or a source check for systems read off their papers) would show r = cheap control's error / system's reported error above 1.221, the largest H/M ratio, or at least above 1.10, with a verdict only if three or more pass. Two settings favor the prediction: CiK's controls are point forecasts scored with RCRPS, which favors the system and therefore the prediction, and each system's reported error is its best cell. We had read the papers' numbers before writing the criteria."

**Status sentences** (one per system, filled in as the case may be):

- CiK passed: "CiK passed (Exp-Smoothing anchor <x> vs 0.605); against its statistical ensemble (R2), r = <r>."
- CiK not passed: "CiK's anchor (Exp-Smoothing, 0.605) was reproduced at <x>, outside 5%, so CiK is reported as unverified (r = <r>, descriptive)."
- Nexus: "Nexus passed the source check; against the best single model of its own TSFM pool (R3), as for the other pool-based systems, r = <r>."
- BNP: "BNP's only no-LLM anchor that is not a trained or foundation model (arima) uses R's forecast package, which we did not run, and its base-forecaster numbers differ from CiK's on the same tasks; it is reported as unverified (r = <r>, descriptive)."
- N2F: "N2F reports only trained deep baselines; it is reported as unverified, on Electricity only (r = <r>, descriptive)."
- CompEvo (one of two): "The public AEMO file released with N2F does not match CompEvo's description, and its repository <does not provide / provides> <the data, look-back and test windows>; <no ratio is computed / r = <r>, unverified>."

**Threshold sentence** (one for each system that passes): "<System> <exceeds / does not exceed> 1.221 and <exceeds / does not exceed> 1.10."

**Conclusion sentence by K**:

- K=0: "No new system passed the check; the prediction is untested."
- K=1: "Only one system passed the check (<System>), fewer than the three fixed in advance for a verdict; the prediction is untested. <System>'s ratio <meets / does not meet> the thresholds; this is not a test."
- K=2: "Only two systems passed the check, fewer than the three fixed in advance for a verdict; the prediction is untested. Whatever their ratios, they are not evidence for the category pattern: their magnitudes were close to determined by numbers we had read, and CiK's benchmark selects tasks that need the context."
- K >= 3, supported: "<a> of <K> exceed 1.221 and all exceed 1.10; by the rule fixed in advance the prediction is supported. Input category remains confounded with domain and benchmark design, and the two settings above favor the prediction."
- K >= 3, partly supported: "The prediction is partly supported: <systems, r, threshold missed>." Sentences in the main text about the category ordering are changed to "holds on <a>/<K> new systems".
- K >= 3, not supported: "The prediction fixed in advance did not hold: <systems> show ratios of <r>, at or below <threshold>." Sentences in the abstract and introduction that say the category ordering "holds" or "is consistent" are deleted or rewritten, and the categories are kept only as a post hoc description of the original 8 systems. The claim about reporting practice does not depend on this prediction.

**Prohibitions**: whether or not CiK or Nexus meets P1 or P2, under an insufficient test it may not be written as "verified on the new systems" or "evidence consistent with the prediction". The prediction, rule, and result of Section 7 all go into the main text (they may be compressed into 2-4 sentences); the paper attaches this document.

### 8. Combined reading (secondary reading)

- N_comb = the number counted in the first-round criteria + the number of systems of this second round that pass the baseline-consistency check (the source check for Nexus) (whatever their category). **Main version**: with LSTPrompt, 8+K; **other version**: without LSTPrompt, 7+K; if CompEvo passes only through a P-type anchor, the versions are further split "with / without CompEvo". Expected after the pre-check: main version 9 or 10, other version 8 or 9.
- Counted mechanically as in the original section 6: a reading only if N_comb >= 6; compute ceil(N/2) and floor(N/4); count all three thresholds; if the three thresholds fall into different categories, write "close".
- **Abstract rule** (confirmed on 2026-11-18; v2 states the version explicitly): judged on the **main version**. If the three thresholds fall into the **same category**, whether match, evidence against, or mixed, the abstract states that category in one sentence; if the other version falls into a different category, it is stated in the same sentence. If the three thresholds fall into different categories (i.e. "close"), the abstract does not state the combined reading separately, and the main reading "close" at N=8 stands.
- In the results section the combined reading is marked "secondary, fixed in advance". If it falls into the "evidence against" category, it is written in the wording of the original section 6, not weakened.

### 9. Exclusion and stopping rules

| Situation | Handling | In K or N_comb | Reported |
|---|---|---|---|
| Data not obtainable (download fails, registration required, licence forbids, can only be generated by running third-party code, no fixed version) | recorded as "data not available". Class-A readings (R3 of Nexus) are not affected | no (except Nexus) | yes |
| Windows cannot be determined | no r; CompEvo as in 5.7 | no | yes |
| Anchor not passed, no anchor, or magnitude check not passed | recorded as "protocol unverified"; r computed, described only | no | yes |
| Structure check not passed (6.1, 6.4) | that dataset stops; no instance or window is chosen by hand | no | yes |
| R2 sentinel triggered | stop and post the log; only interface-level errors are fixed, and this is stated in the acceptance check | not before the fix | yes |
| Anchor implementation raises an error | only the one interface repair of 5.9 item 3 is allowed; other failures are recorded as 5 per 5.9 item 7 | -- | yes |
| Deadline 2027-01-31 | systems that have not completed the check are reported as "protocol unverified" or "not completed" | no | yes |
| Third-party code | not run by default; a step that can only be completed by running third-party code stops and is decided by the authors | -- | yes |

The stopping rules do not change with the result. No system is excluded or included because of the size of r.

### 10. Reporting rules

- **All 5 systems are reported**, each with: status, control class (R2 or R3), main metric, system value and its source, control value, r (where it can be computed), the result of the baseline-consistency check (the source check for Nexus), comparison with P1 and P2, and which numbers had been read before this document was written.
- **Diagnostics**: the CiK anchor value, whether or not it passes, and the seed distribution of 5.9; the number of instances capped at 5 (for the anchor, R1, and R2 separately), compared with the 5 of Exp-Smoothing in the paper's Table 6; R1 degeneration counts, R2 fallback and failure counts; the number of failed anchor instances; whether the interface repair of 5.9 item 3 was used.
- The re-check table and the re-check figure of the paper each get 5 rows.
- The known information of Section 2, the adjustments of Section 5, and the confounds and biases of Section 7.4 are written into the main text or the appendix. **The bias of single-point RCRPS is written into the main text with both sides**: conservative for "can the control match", favourable for the prediction of Section 7.
- The readings and text of the first-round re-check are not withdrawn. The sentence "rerunning would take another 3-4 days" is rewritten to point to this second round.

### 11. What is not done and not said (as in the original section 7, with additions)

- No audited system is run; no LLM is called; no author is contacted; no third-party code is run.
- Different metrics are not combined across systems into one number.
- A cheap control that matches does not mean the LLM contributes nothing; a system that is clearly ahead is not attributed to the LLM either.
- A high r in category S is not taken to say "the lead comes from the information".
- During execution, `results_complete.csv` of the CiK repository is not read (5.9).

### 12. Order of work

1. The criteria come first, then the computation. The R3 ratio of Nexus is computed only after this document is complete; its source check has been judged in 5.4.
2. If a change is truly needed after the computation starts, a separate "post hoc" section is opened; the text of these criteria is not changed.

### 13. Record of additions

**13.1 v0 to v1 (2026-11-18, after the pre-check).** C1-C24 are in the change log of v0/v1. Their implementation in v2: the content of C1-C21 is kept and further fixed or changed by the items of 13.2; "Leaf not available" in C8 is kept; the unit note of C14 is kept with 5.6; the expectation "insufficient test" of C22 is rewritten into 2.2 and 7.5.

**13.2 v1 to v2 (2026-11-18, after the independent review).** "The review" means the review of v1.

| # | Section | Change | Basis |
|---|---|---|---|
| D1 | 5.1-8, 7.4, 10, 14 | direction of the bias written on both sides: conservative for "match", favourable to the prediction of Section 7 | review comment on v1 |
| D2 | 5.4, 6.3, 2.2, 3 | the source check of Nexus now judged passed, with the four criteria and the source text; not judged again later | review comment on v1 |
| D3 | 5.1-2, 5.1-3, 5.1-4, structure check of 6.1 | `metric_scaling` taken directly from the HF field; denominator of the constraint terms and "three terms added"; RoI judged by "length > 0"; structure check adds RoI range and not covering all steps, strictly increasing timestamps, (name, seed) unique, count of finite constraint values | review comment on v1 |
| D4 | 5.9 | anchor implementation fixed: endog as a numpy array; how `random_state` is passed (marked as our convention); the one allowed interface repair; failed instances recorded as 5; versions fixed; the baseline-consistency check on the first formal run; smoke test prints no aggregate; how post hoc corrections are reported; seed distribution as description | review comment on v1 |
| D5 | 5.9, 11, 14 | `results_complete.csv` not read during execution; later use only after all results are written to disk, marked "post hoc", changing no baseline-consistency check, K, N_comb | review comment on v1 |
| D6 | 7.5 | templates rewritten: no presupposed P1; cases K=0,1,2 and the three cases of K>=3; "passed the validity check"; wording for BNP and CompEvo; control class stated; bias stated; definition of r and threshold sentence | review comment on v1 |
| D7 | 8 | abstract rule judged on the main version (with LSTPrompt); same category (any) for the three thresholds goes into the abstract; a different category of the other version is written together; two versions if CompEvo passes only through a P-type anchor | review comment on v1 |
| D8 | 5.7 | CompEvo criteria changed from 4 to 7: strict equality, uniqueness of L, window stride, target column, forecast length 48, original scale, commit; fitting history of R2 equals L; P-type versions | review comment on v1 |
| D9 | 5.12 | no rounding in threshold comparisons | review comment on v1 |
| D10 | 5.2 | the reason for -1 now rests on the code, notes the typo on README line 88, cites the precedent of the first-round pre-check notes | review comment on v1 |
| D11 | 5.2 | frequency-table sensitivity written as a full table | review comment on v1 |
| D12 | 5.2 | no degeneration of R2 for short histories; sentinel and execution order | review comment on v1 |
| D13 | 5.2 | formula of R1 for h > m | review comment on v1 |
| D14 | 5.3, 6.1 | CiK rule changed to Direct Prompt (ours) only, value unchanged; disclosed that it was changed after reading the table | review comment on v1 |
| D15 | 5.4 | main metric now cites the Nexus text | review comment on v1 |
| D16 | 5.4 | tie-breaking order; per-column best as description; direction favourable to the system noted | review comment on v1 |
| D17 | 1.4 | scope of the magnitude check | review comment on v1 |
| D18 | 5.10 | sqrt(r) applies only to the original 8 systems, marked post hoc description | review comment on v1 |
| D19 | 5.6 | S10 **not adopted**; the full-history sensitivity of N2F deleted instead (reason in 5.6) | review comment on v1 |
| D20 | 5.6, 6.4 | parsing regex of N2F and the assertion "exactly 48 numbers each" | review comment on v1 |
| D22 | 10 | diagnostics and the "control class" column added | review comment on v1 |
| D23 | 2.3 | note on how fragile the 5% tolerance is | review comment on v1 |
| D25 | 5.11 | unit tests of the scorer (synthetic data only) | review comment on v1 |
| D26 | 2.4, 7.4 | "system value takes the most favourable cell" favours the prediction, listed among the biases | review comment on v1 |
### 14. Decisions and substantive changes

**Six items of v0 confirmed on 2026-11-18**: (1) a separate set of criteria; (2) DLinear not accepted; (3) Nexus uses R3; (4) the combined reading goes into the abstract when it falls into one category; (5) single-point RCRPS stated in the main text; (6) BNP takes the minimum cell of the paper's method.

**Substantive changes of v2 relative to v1**:

1. Single-point scoring raises the ratio of CiK: conservative for "can a cheap control match", but it makes our category prediction easier to meet; the main text writes both sides.
2. Whether Nexus passes the check is now judged "passed" from the table captions of the paper, and not judged again later, so Nexus is certainly counted.
3. The abstract rule changes to: in the version with LSTPrompt, if the three thresholds fall into the same category (including "mixed"), it goes into the abstract; if they fall into different categories, it does not.
4. The system-value rule of CiK changes to take only CiK's own Direct Prompt method (the value is still 0.159); this was changed after reading the table and will be stated.
5. The anchor of CiK counts only the result of the first formal run; a bug found later can only be reported separately as a "post hoc correction" and does not change whether CiK is counted.
6. The per-task result file of the CiK repository is not read during execution; if read later, it is only a post hoc check and affects no judgement.
7. CompEvo is computed only if it meets 7 (formerly 4) stricter conditions, so it basically stays "not computed".
8. The sensitivity analysis of N2F that fits on the full history is deleted.
9. The paper templates now cover the cases "0, 1, 2 systems pass" and "3 or more", and no longer presuppose that any system meets a threshold.
