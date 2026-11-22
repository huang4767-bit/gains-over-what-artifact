# Increment records summary

This file summarises the distribution of the LLM increment records in `margin_records.csv` and defines the rules used to band them.

The file states the distribution only. The CSV has 475 rows. Of these, 350 are of class `full`, and 337 of those (19 systems) have raw values and can be banded. Another 13 rows have only derived percentages; their raw values were not extracted. TimeCopilot and LLMTime have no numeric records, TSci has only single-slice records, and TSOrchestra has only claim records with no identifiable effect (see section 3).

## 1. Definitions and rules

**Delta**: `Delta = 100 * (E_control - E_system) / E_control`, where E is an error (lower is better). **Positive = the system has lower error**, negative = the system has higher error. For FEV-bench, the skill score is converted to an error: E = 100 - Skill.

**Bands**: |Delta| < 1 is `lt1`; 1 <= |Delta| < 5 is `1to5`; |Delta| >= 5 is `ge5`. **Boundary rule: if |Delta| equals the threshold tau (1 or 5) exactly, the record goes to the outer band** (`1to5` and `ge5`). Banding uses exact decimal arithmetic, not floating point. Two rows in the CSV fall exactly on tau, listed in `band_boundary_note`: R423 (CastFSR-Zero, ETTh2, MAE 0.380 -> 0.361, Delta = 5.00, counted in `ge5`) and R470 (CastFSR Table 4, ETTm1, MSE 0.060 -> 0.057, Delta = 5.00, counted in `ge5`).

**Rounding precision**: for both values, take plus or minus 0.5 units of the last printed digit. This gives the possible interval of Delta (column `delta_rounding_range`). `precision_insufficient = yes` means the interval contains 0 (endpoints included), so the direction cannot be reliably distinguished after rounding. `band_unstable_under_rounding = yes` means the "sign + band" labels at the two ends of the interval differ. The two columns are annotations only and do not change `delta_pct` or `band`.

**Record class** (`record_class`):
- `full`: a complete system against one control. Enters the distribution tables below.
- `subwindow`: a sub-window of the same complete system in the same case (the holiday windows of Bridging). Listed separately, not in the distribution tables.
- `example_slice`: one example slice (TSci). Listed separately.
- `partial_stage`: compares only the output of one stage of the system (CastFSR Table 4). Listed separately.
- `ablation`: ablation variants and arms with information removed (the no-context arms of Context is Key and Beyond Naive Prompting, the no-news arm of From News to Forecast, Time-R1 without domain context). **The authors' own LLM variants still contain an LLM and are not treated as no-LLM controls.** Listed separately.
- `claim`: only a claim, effect size not identifiable (TSOrchestra). Not banded.

**How the control is chosen**: for each type of control, take the strongest one printed in the same setting and under the same metric (the strongest member for pool members, the strongest baseline for external baselines). Weaker members are not recorded separately, because their Delta would only be larger with the same direction, and counting each would give one system several votes. Control types (`control_type`): `own_no_LLM`, `candidate_average`, `base_model`, `external_baseline`, `external_domain_benchmark` (does not occur in the literature records). The column `control_rung` (C1, C2, C4 or `-`) is set as well. **Comparisons with other LLM methods (LLM baselines, other agents) are not recorded.**

**Tier column**: `reference_tier_pre_reannotation` is the reference label set before the re-annotation (see `coding/agreement.md`). The MUSE-Bench reference label is "S/M/N by arm", and the extraction does not map arms to datasets, so it is recorded as `unresolved`. Informed Forecasting has no reference label and is recorded as `unlabelled` (an earlier label was M). Nexus: Leaf and GIFT-CTX are S, GIFT-Eval is N. Context is Key, Beyond Naive Prompting and From News to Forecast: arms with information are S, arms without information are N. The **MATCH column** is defined by the codebook only for tier S (see `coding/codebook.md`). Tiers M and N are recorded as `n/a`. The earlier labels of FASE and Time-R1 list `partly` and `unclear` at tier M, which disagrees with the codebook.

**Unit of counting**: one comparison record. Records of the same system over several metrics and datasets are not independent evidence. The per-system distribution is therefore given first, then the stratified tables. The stratified tables also give the average of within-system shares (macro), which gives each system one vote.

**Records without extracted raw values** (16 rows, not banded): JudgeCast Table 4 (three tasks), Nexus (four market domains) and Time-R1 MAE (six datasets). Only the derived percentages were extracted for these; they are added to the column `band_boundary_note`, with the sign convention changed to "positive = the system has lower error". TSOrchestra has three claim rows.

## 2. Per-system distribution (record_class = full)

Each cell is a record count. Symbols: `+` = the system has lower error, `-` = higher, `0` = equal.

| system | tier (reference, pre-reannotation) | n | lt1: + / - / 0 | 1to5: + / - | ge5: + / - | precision-insufficient | band unstable under rounding |
|---|---|---|---|---|---|---|---|
| MoiraiAgent | M | 1 | 0 / 0 / 0 | 1 / 0 | 0 / 0 | 0 | 0 |
| FASE | M | 12 | 1 / 0 / 0 | 0 / 1 | 10 / 0 | 0 | 1 |
| TimeRSI | S | 10 | 0 / 0 / 0 | 6 / 0 | 4 / 0 | 0 | 0 |
| Bridging | S | 8 | 0 / 0 / 0 | 0 / 1 | 7 / 0 | 0 | 0 |
| JudgeCast | S | 21 | 0 / 0 / 0 | 3 / 0 | 14 / 4 | 0 | 0 |
| MUSE-Bench | unresolved (S/M/N by arm) | 28 | 2 / 3 / 1 | 0 / 0 | 11 / 11 | 2 | 0 |
| Beyond Naive Prompting | S | 56 | 0 / 0 / 0 | 0 / 1 | 53 / 2 | 0 | 0 |
| Nexus | S, N | 9 | 0 / 0 / 0 | 1 / 0 | 8 / 0 | 0 | 0 |
| TimEvolve | S | 16 | 1 / 0 / 0 | 8 / 1 | 6 / 0 | 0 | 2 |
| LSTPrompt | M | 12 | 0 / 0 / 0 | 1 / 1 | 5 / 5 | 0 | 0 |
| Informed Forecasting | unlabelled | 32 | 0 / 0 / 0 | 2 / 0 | 24 / 6 | 0 | 0 |
| Context is Key | S | 14 | 0 / 0 / 0 | 1 / 0 | 9 / 4 | 0 | 0 |
| Time-R1 | M | 12 | 2 / 0 / 1 | 3 / 3 | 2 / 1 | 2 | 2 |
| MemCast | S | 10 | 1 / 1 / 0 | 2 / 0 | 6 / 0 | 0 | 0 |
| From News to Forecast | S | 9 | 1 / 0 / 0 | 1 / 0 | 6 / 1 | 1 | 1 |
| FLAIRR-TS | N | 12 | 0 / 0 / 0 | 0 / 0 | 11 / 1 | 0 | 0 |
| KairosAgent | M | 17 | 0 / 0 / 1 | 1 / 1 | 8 / 6 | 1 | 1 |
| CompEvo | S | 8 | 0 / 0 / 0 | 4 / 0 | 2 / 2 | 0 | 1 |
| CastFSR | S | 50 | 1 / 2 / 0 | 6 / 0 | 39 / 2 | 3 | 6 |
| TimeCopilot | - | 0 banded (non-banded rows: 0) | - | - | - | - | - |
| TSci | - | 0 banded (non-banded rows: 3) | - | - | - | - | - |
| TSOrchestra | - | 0 banded (non-banded rows: 3) | - | - | - | - | - |
| LLMTime | - | 0 banded (non-banded rows: 0) | - | - | - | - | - |

The last four rows: TimeCopilot and LLMTime have no numeric records. TSci has only 3 single-slice records (section 3). TSOrchestra has only 3 claim records, which cannot be banded. The 20 sub-window records of Bridging are also in section 3.

## 3. Records outside the distribution tables

Each cell is the number of signed banded records. `n banded` and `n not banded` are the numbers of rows with and without raw values. The controls of `ablation` rows still contain an LLM (or are arms with information removed) and are not no-LLM controls. The `partial_stage` CastFSR row is the output of the model-selection stage, not a complete system.

| record_class | system | n banded | n not banded | lt1 (+/-/0) | 1to5 (+/-) | ge5 (+/-) |
|---|---|---|---|---|---|---|
| subwindow | Bridging | 20 | 0 | 0/0/0 | 0/0 | 20/0 |
| example_slice | TSci | 3 | 0 | 0/0/0 | 0/2 | 0/1 |
| partial_stage | CastFSR | 8 | 0 | 0/0/0 | 2/1 | 3/2 |
| ablation | FASE | 12 | 0 | 2/0/0 | 5/1 | 4/0 |
| ablation | TimeRSI | 4 | 0 | 0/0/0 | 2/0 | 2/0 |
| ablation | Bridging | 2 | 0 | 0/0/0 | 0/1 | 1/0 |
| ablation | JudgeCast | 4 | 0 | 0/0/0 | 0/0 | 4/0 |
| ablation | Beyond Naive Prompting | 9 | 0 | 0/0/0 | 0/2 | 4/3 |
| ablation | Nexus | 15 | 0 | 3/4/0 | 2/2 | 4/0 |
| ablation | TimEvolve | 1 | 0 | 0/0/0 | 0/0 | 1/0 |
| ablation | Informed Forecasting | 3 | 0 | 0/0/0 | 0/0 | 3/0 |
| ablation | Context is Key | 18 | 0 | 1/0/0 | 1/0 | 10/6 |
| ablation | Time-R1 | 6 | 0 | 0/0/0 | 1/0 | 5/0 |
| ablation | MemCast | 3 | 0 | 0/0/0 | 0/0 | 3/0 |
| ablation | From News to Forecast | 12 | 0 | 0/0/0 | 1/0 | 7/4 |
| ablation | CompEvo | 2 | 0 | 0/0/0 | 0/0 | 2/0 |
| claim | TSOrchestra | 0 | 3 | 0/0/0 | 0/0 | 0/0 |

Ablations and arms with information removed, by the reference tier of the arm:

| tier | n | lt1 (+/-/0) | 1to5 (+/-) | ge5 (+/-) |
|---|---|---|---|---|
| S | 48 | 3/4/0 | 5/3 | 32/1 |
| M | 18 | 2/0/0 | 6/1 | 9/0 |
| N | 22 | 1/0/0 | 1/2 | 6/12 |

Records with tier N:

- Beyond Naive Prompting, ablation: 6
- Nexus, full: 1
- Context is Key, ablation: 12
- From News to Forecast, ablation: 4
- FLAIRR-TS, full: 12

## 4. Stratified summaries (record_class = full, bandable)

The "macro" columns are the averages of each system's share within the stratum, one vote per system. "records" is the number of records. Several records of one system are not independent evidence, so the record count in a table must not be read as a system count.

### By tier (reference tier before re-annotation)

| tier | systems | records | lt1 + / - / 0 | 1to5 + / - | ge5 + / - | macro share lt1 | macro 1to5 | macro ge5 | macro share system-lower-error (+) |
|---|---|---|---|---|---|---|---|---|---|
| S | 11 (TimeRSI, Bridging, JudgeCast, Beyond Naive Prompting, Nexus, TimEvolve, Context is Key, MemCast, From News to Forecast, CompEvo, CastFSR) | 210 | 4 / 3 / 0 | 31 / 3 | 154 / 15 | 4% | 22% | 74% | 89% |
| M | 5 (MoiraiAgent, FASE, LSTPrompt, Time-R1, KairosAgent) | 54 | 3 / 0 / 2 | 6 / 6 | 25 / 12 | 8% | 37% | 55% | 71% |
| N | 2 (Nexus, FLAIRR-TS) | 13 | 0 / 0 / 0 | 1 / 0 | 11 / 1 | 0% | 50% | 50% | 96% |
| unresolved (S/M/N by arm) | 1 (MUSE-Bench) | 28 | 2 / 3 / 1 | 0 / 0 | 11 / 11 | 21% | 0% | 79% | 46% |
| unlabelled | 1 (Informed Forecasting) | 32 | 0 / 0 / 0 | 2 / 0 | 24 / 6 | 0% | 6% | 94% | 81% |

### By control type

| control_type | systems | records | lt1 + / - / 0 | 1to5 + / - | ge5 + / - | macro lt1 | macro 1to5 | macro ge5 |
|---|---|---|---|---|---|---|---|---|
| own_no_LLM | 5 (MoiraiAgent, FASE, Beyond Naive Prompting, KairosAgent, CastFSR) | 71 | 0 / 0 / 0 | 2 / 2 | 65 / 2 | 0% | 27% | 73% |
| candidate_average | 1 (FASE) | 4 | 1 / 0 / 0 | 0 / 0 | 3 / 0 | 25% | 0% | 75% |
| base_model | 5 (TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting) | 51 | 2 / 3 / 1 | 7 / 0 | 26 / 12 | 9% | 23% | 69% |
| external_baseline | 16 (FASE, TimeRSI, Bridging, MUSE-Bench, Nexus, TimEvolve, LSTPrompt, Informed Forecasting, Context is Key, Time-R1, MemCast, From News to Forecast, FLAIRR-TS, KairosAgent, CompEvo, CastFSR) | 211 | 6 / 3 / 2 | 31 / 7 | 131 / 31 | 5% | 20% | 75% |
| external_domain_benchmark | 0 | 0 | - | - | - | - | - | - |

### Tier x control type

| tier | control_type | systems | n | lt1 (+/-/0) | 1to5 (+/-) | ge5 (+/-) |
|---|---|---|---|---|---|---|
| S | own_no_LLM | 2 (Beyond Naive Prompting, CastFSR) | 58 | 0/0/0 | 1/1 | 54/2 |
| S | base_model | 4 (TimeRSI, Bridging, JudgeCast, Beyond Naive Prompting) | 37 | 0/0/0 | 7/0 | 25/5 |
| S | external_baseline | 9 (TimeRSI, Bridging, Nexus, TimEvolve, Context is Key, MemCast, From News to Forecast, CompEvo, CastFSR) | 115 | 4/3/0 | 23/2 | 75/8 |
| M | own_no_LLM | 3 (MoiraiAgent, FASE, KairosAgent) | 13 | 0/0/0 | 1/1 | 11/0 |
| M | candidate_average | 1 (FASE) | 4 | 1/0/0 | 0/0 | 3/0 |
| M | external_baseline | 4 (FASE, LSTPrompt, Time-R1, KairosAgent) | 37 | 2/0/2 | 5/5 | 11/12 |
| N | external_baseline | 2 (Nexus, FLAIRR-TS) | 13 | 0/0/0 | 1/0 | 11/1 |
| unresolved (S/M/N by arm) | base_model | 1 (MUSE-Bench) | 14 | 2/3/1 | 0/0 | 1/7 |
| unresolved (S/M/N by arm) | external_baseline | 1 (MUSE-Bench) | 14 | 0/0/0 | 0/0 | 10/4 |
| unlabelled | external_baseline | 1 (Informed Forecasting) | 32 | 0/0/0 | 2/0 | 24/6 |

### By control rung

| rung | systems | records | lt1 (+/-/0) | 1to5 (+/-) | ge5 (+/-) |
|---|---|---|---|---|---|
| C1 | 1 (FASE) | 4 | 1/0/0 | 0/0 | 3/0 |
| C2 | 9 (MoiraiAgent, FASE, TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting, KairosAgent, CastFSR) | 115 | 2/3/1 | 9/2 | 88/10 |
| C4 | 3 (FASE, TimeRSI, MUSE-Bench) | 22 | 0/0/0 | 0/0 | 18/4 |
| - | 15 (TimeRSI, Bridging, JudgeCast, Nexus, TimEvolve, LSTPrompt, Informed Forecasting, Context is Key, Time-R1, MemCast, From News to Forecast, FLAIRR-TS, KairosAgent, CompEvo, CastFSR) | 196 | 6/3/2 | 31/7 | 116/31 |

### Precision annotations

- total rows: 475; main banded: 337; main systems: 19
- precision-insufficient (all rows): 9; in main: 9
- band-unstable (all rows): 22; in main: 14
- rows without values (not banded): 16

Records with `precision_insufficient = yes`:

- R110 MUSE-Bench Time-MMD_Security (Table 11) MASE (Table 11) 0.6952->0.6952 delta=0.00 range=[-0.01, 0.01] class=full
- R112 MUSE-Bench Retail_1D (Table 11) MASE (Table 11) 0.7620->0.7621 delta=-0.01 range=[-0.03, 0.00] class=full
- R325 Time-R1 Exchange (Table 2) MSE, raw scale, mean of 3 seeds 0.0008->0.0007 delta=12.50 range=[0.00, 23.53] class=full
- R329 Time-R1 NASDAQ (Table 2) MSE, raw scale, mean of 3 seeds 0.0007->0.0007 delta=0.00 range=[-15.38, 13.33] class=full
- R365 From News to Forecast Bitcoin (Table 3), with filtered news RMSE 3.68->3.67 delta=0.27 range=[0.00, 0.54] class=full
- R399 KairosAgent Time-MMD Climate (Table 2) MSE 0.863->0.863 delta=0.00 range=[-0.12, 0.12] class=full
- R419 CastFSR ETTh1 (Table 1), CastFSR-Zero MAE, normalised target scale 0.213->0.212 delta=0.47 range=[0.00, 0.94] class=full
- R426 CastFSR ETTm1 (Table 1), CastFSR-Zero MAE, normalised target scale 0.167->0.168 delta=-0.60 range=[-1.20, 0.00] class=full
- R451 CastFSR ETTm1 (Table 1), CastFSR-R1 MAE, normalised target scale 0.167->0.168 delta=-0.60 range=[-1.20, 0.00] class=full

Records of class full with `band_unstable_under_rounding = yes`:

- R014 FASE GIFT-Eval 29 configs (Table 1) RMSE normalised by Seasonal Naive, geometric mean over 29 GIFT-Eval configurations 0.677->0.643 delta=5.02 range=[4.88, 5.17]
- R233 TimEvolve Time-MMD Environment (Table 1) MSE 0.276->0.274 delta=0.72 range=[0.36, 1.08]
- R238 TimEvolve Time-MMD Social Good (Table 1) MAE 0.377->0.381 delta=-1.06 range=[-1.33, -0.79]
- R325 Time-R1 Exchange (Table 2) MSE, raw scale, mean of 3 seeds 0.0008->0.0007 delta=12.50 range=[0.00, 23.53]
- R329 Time-R1 NASDAQ (Table 2) MSE, raw scale, mean of 3 seeds 0.0007->0.0007 delta=0.00 range=[-15.38, 13.33]
- R364 From News to Forecast Traffic (Table 3), with filtered news MAE 1.51->1.43 delta=5.30 range=[4.65, 5.94]
- R400 KairosAgent Time-MMD Climate (Table 2) MAE 0.747->0.739 delta=1.07 range=[0.94, 1.20]
- R414 CompEvo Traffic (Table 1) RMSE x1e-2 3.12->3.08 delta=1.28 range=[0.96, 1.60]
- R423 CastFSR ETTh2 (Table 1), CastFSR-Zero MAE, normalised target scale 0.380->0.361 delta=5.00 range=[4.74, 5.26]
- R424 CastFSR ETTm1 (Table 1), CastFSR-Zero MSE, normalised target scale 0.058->0.055 delta=5.17 range=[3.48, 6.84]
- R426 CastFSR ETTm1 (Table 1), CastFSR-Zero MAE, normalised target scale 0.167->0.168 delta=-0.60 range=[-1.20, 0.00]
- R444 CastFSR ETTh1 (Table 1), CastFSR-R1 MAE, normalised target scale 0.213->0.210 delta=1.41 range=[0.94, 1.87]
- R449 CastFSR ETTm1 (Table 1), CastFSR-R1 MSE, normalised target scale 0.058->0.055 delta=5.17 range=[3.48, 6.84]
- R451 CastFSR ETTm1 (Table 1), CastFSR-R1 MAE, normalised target scale 0.167->0.168 delta=-0.60 range=[-1.20, 0.00]

## 5. Values that depend on metric, table or rounding

These items record where a single headline number hides a different result under another metric, table or rounding.

- **CastFSR Table 1 (v3), MSE against the strongest non-LLM baseline per dataset (BE, DE, FR, NP, PJM).** CastFSR-R1: 18.68, 51.63, 15.75, 42.86, 26.11 (range 15.75-51.63). CastFSR-Zero: 15.79, 50.75, 17.70, 26.58, 22.22. The better of the two variants gives 17.70-51.63. The R1 ratios (0.81, 0.48, 0.82, 0.57, 0.74) agree with the R1 range 15.75-51.63.
- **CastFSR Table 4 (v3).** Output of the model-selection stage of CastFSR-Zero against the best fixed expert in the pool (stage level, 4 datasets), MSE / MAE: ETTh1 +3.30 / -5.63, ETTm1 +5.00 / +1.12, BE +5.67 / +9.49, NP -11.96 / -4.47 (positive = the stage output has lower error). This is a stage-level comparison, not the complete system against its own control.
- **FASE.** Among its 12 full records (4 metrics x 3 controls), the CRPS against TiRex-2 is -1.64% (`1to5`, the system is worse), and the CRPS against the Uniform Ensemble is +0.80% (`lt1`). The result of the complete system changes with the metric.
- **KairosAgent, Time-MMD, zero-shot foundation models (appendix Table 22).** In three domains, the zero-shot foundation models have lower MSE than the system. Against the paper's own Table 2 baselines, Environment (-36.96%) and Security (-6.45%) are also worse for the system among the three extracted domains. Only three of the nine Time-MMD domains were extracted, and the other six were not checked.
- **From News to Forecast, Bitcoin.** The advantage with news is 0.27%, with rounding interval [0.00, 0.54] and `precision_insufficient = yes`, so the direction cannot be distinguished.
- **From News to Forecast, Exchange.** The figure 3.7% uses 6.46 from Table 1 against the iTransformer value 0.671 in Table 3 (a cross-table comparison after unit conversion). Using Table 3 only, it is 0.65 against 0.671, Delta = 3.13%, rounding interval [2.31, 3.95], same band (`1to5`).

## 6. Open items

- The identity of the three unread candidates and the inclusion rule of the corpus are not recorded in this folder.
- CastFSR values were re-fetched from the arXiv v3 HTML.
- The values in TimeCopilot Figure 2, TSOrchestra Figure 2 and appendix Figure 4, and MoiraiAgent Figure 3 were not read. The expert pool and the Table 1 baseline set of TimEvolve overlap only in part.
- The mapping from arms to datasets for MUSE-Bench was not extracted, so it is `unresolved` in the stratified tables and needs to be filled in after the re-annotation.
- From LSTPrompt Table 1, only 6 of 12 rows were extracted. Of the 9 Time-MMD domains (KairosAgent), only 3 were extracted. Of 17 LLMs in Beyond Naive Prompting, only 8 were extracted. Nexus market domains and Time-R1 MAE have only derived percentages. These unextracted records are not added to the distributions.
