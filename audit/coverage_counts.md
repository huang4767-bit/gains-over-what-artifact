# Coverage counts

This file documents how the coverage counts of the audit (applicability and reporting of no-LLM controls) are defined and which systems enter each count.

All counts are computed only from `applicability_coverage.csv` in this folder. The file has 138 rows: 23 systems times six rows (C1 to C5 and "own no-LLM control (any)"). The corpus is in `corpus.csv` (23 systems included, LLM Processes excluded). Formula: **coverage = reported / applicable**. Numerator and denominator come from the same column conditions of that CSV.

## 1. Counting rules

Applicability (`applicable`):

| Rule | Content |
|---|---|
| A1 (C1) | The system has at least two **non-LLM** numeric candidate forecasts, and the LLM selects, weights or corrects them. Not applicable if the candidates are themselves LLM outputs (CompEvo). TimeCopilot is listed separately (`separate`): the GIFT-Eval result it reports is already a C1 without an LLM, so there is no "LLM versus C1" comparison to count. |
| A2 (C2) | The system has a fixed set of non-LLM candidates, or an uncorrected non-LLM base forecast. |
| A3 (C3) | The system retrieves historical windows **and their realised continuations** and passes them to the LLM. Systems that retrieve tool errors or ranking records (FASE, TimeRSI) are not applicable. |
| A4 (C4) | Applies to every system evaluated on numeric forecasting data. |
| A5 (C5) | The evaluation data belongs to a domain with an established public benchmark that can be identified in the files (electricity price markets: LEAR). Cases inferred only from a market code are recorded as `yes_boundary`. |
| A6 (own any) | At least one of C1, C2, C3 applies, so the system has a deterministic component that can serve as a forecast without the LLM. |

Reporting (`reported`): the paper prints the error of that control in the evaluated setting, in the same table, figure or sentence as the system result. Values: `yes`, `no`, `yes_boundary`, `separate`, `n/a`. The main count includes only `yes`. `yes_boundary` enters only the upper bound.

Report scope (`report_scope`) has four levels: `main_result` (main evaluation), `subset_of_evaluation` (covers only part of the benchmark), `stage_level_subset` (compares only the output of one stage of the system, and only on some datasets), `example_single_slice` (one example slice). Carrier (`carrier`): table / figure / sentence / appendix report text. Computability (`computability`): values+metric sufficient, claim without identifiable effect, none.

## 2. Count results

| Control | Denominator (applicable) | Numerator (reported) | Ratio | Range (boundary items) |
|---|---|---|---|---|
| C1 candidate average | 7: TSci, TSOrchestra, MoiraiAgent, FASE, Nexus, TimEvolve, CastFSR | 1: FASE | **1 / 7** | see "Boundary of C1" |
| C2 best fixed candidate / uncorrected base forecast | 14: TimeCopilot, TSci, TSOrchestra, MoiraiAgent, FASE, TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting, Nexus, TimEvolve, KairosAgent, CastFSR | 11: TSci, TSOrchestra, MoiraiAgent, FASE, TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting, KairosAgent, CastFSR | **11 / 14** | 8-12 / 14 |
| C3 retrieved-example average | 2: MemCast, FLAIRR-TS | 0 | **0 / 2** | 0 / 4 (boundary: Bridging, TimEvolve) |
| C4 seasonal naive (control row) | 23 (all) | 3: FASE, MUSE-Bench, TimeRSI | **3 / 23** | 2-3 / 23 |
| C5 domain-standard benchmark | 2: MemCast, CastFSR | 0 | **0 / 2** | 0 / 3 (boundary: JudgeCast) |
| own no-LLM control (any) | 16 (C1, C2 or C3 applies) | 11: the same 11 as C2 | **11 / 16** | 8-12 / 16; over all 23 systems: 11 / 23 (8-12 / 23) |

By rule A6, seven systems are not applicable: LLMTime, LSTPrompt, Informed Forecasting, Context is Key, Time-R1, From News to Forecast, CompEvo. They prompt an LLM directly, fine-tune an LLM, or have candidates that are LLM outputs, so they have no deterministic component usable without the LLM. For these seven, the absence of an own no-LLM control follows from the architecture and is not an omission in the report.

### Report scope and computability (own no-LLM control (any), 11 reported)

| report_scope | Systems | Count |
|---|---|---|
| main_result | TSOrchestra, MoiraiAgent, FASE, TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting | 8 |
| subset_of_evaluation | KairosAgent (four Time-IMM datasets only, none for Time-MMD) | 1 |
| stage_level_subset | CastFSR (Table 4: output of the fast model-selection stage versus the best fixed expert in the pool, on ETTh1, ETTm1, BE, NP) | 1 |
| example_single_slice | TSci (one ECL slice, report text in appendix 12.3) | 1 |

| Carrier (the 11 reported for C2) | Systems |
|---|---|
| table (including figures) | FASE, TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting, KairosAgent, CastFSR (8) |
| sentence | MoiraiAgent (one sentence in the blog text), TSOrchestra (one sentence in the main text; the random-metric ensemble in appendix C.1 is additionally shown in a figure) (2) |
| appendix report text | TSci (1) |

Computability: 10 are `values+metric sufficient`. The 25.5% of TSOrchestra is `claim without identifiable effect` (the metric is not defined and the values are in Figure 2, which was not read). **The report exists, but it does not enter the increment bands.** The number of own controls for which an increment can be computed is therefore 10 / 11 (of reported) or 10 / 16 (of applicable). The MoiraiAgent selector was confirmed from public code to be a language-model selector (README and `AutoModelForCausalLM` / `.generate` in `gift_eval/agent.py`), so it stays in the corpus. That commit is not necessarily the one that produced the blog value 0.689, and the normalisation was not checked.

## 3. Boundary items for each range

**Boundary of C1.**
- TimeCopilot (`separate`) is not counted in 1 / 7. If it is added to the denominator and not counted as reported, the ratio is 1 / 8. If its result row itself counts as reported, it is 2 / 8.
- CompEvo is excluded (its candidates are outputs of an LLM agent; its Uniform Weights and MAEL are averages over its own LLM agents, see the ablation rows in `margin_records.csv`).
- Nexus is in the denominator and not reported: its equal-weight row contains LLM streams (macro, micro) and an LLM-selected anchor, so it is not an average without an LLM.

**The 8-12 range for C2 / own any.**
- Lower bound 8 counts only `main_result` scope: TSOrchestra, MoiraiAgent, FASE, TimeRSI, Bridging, JudgeCast, MUSE-Bench, Beyond Naive Prompting.
- Adding three reported items with narrower scope gives 11: TSci (single slice; the best control was determined on that slice after the fact), KairosAgent (one benchmark), CastFSR (stage level, 4 of 10 datasets).
- Upper bound 12 adds Nexus (`yes_boundary`): Tables 1 and 3 print the errors of three pool TSFMs, but as external baseline rows. The authors do not use them as their own controls, and the anchor may be generated by LLM-written code.
- Two further items could flip but are not in the upper bound: TimeCopilot (the values in Figure 2 were not read) and TimEvolve (Table 1 prints only some pool members, Chronos-2 and Toto-2.0, and not Falcon-X, TimesFM-2.5 or Chronos-Bolt). If both flip, C2 would be 14 / 14. This is not used as a number.
- For TSOrchestra, the random-metric ensemble in appendix C.1 (figure and caption) is a second own control, so the system is counted as reported even though the 25.5% is not identifiable.

**Boundary of C3.** The tool retrieval in Bridging gives the historical window and overrides it with last-year actual values, but the extracted text does not say that retrieved items carry realised continuations that can be averaged. TimEvolve has an episodic memory, and the same is unstated. Neither reports C3, so the numerator is unchanged. FASE retrieves the errors of its tools on completed instances, which is not applicable, so it is no longer in the C3 denominator (the older 0/3 came from counting the memory part of FASE as a retrieval system).

**Boundary of C4.** The seasonal-naive row of TimeRSI is an external row of the public leaderboard and also the normalisation baseline. The authors did not add it as a control. Without it the count is 2 / 23. Nexus, KairosAgent and LLMTime use it (or the last value) only as a normalisation constant, which does not count as a control row.

**Boundary of C5.** The dataset codes NP, PJM, BE, FR, DE in JudgeCast have the same names as the five markets of the electricity price benchmark, but their data source was not checked, so they are recorded as `yes_boundary`. The baseline tables of MemCast and CastFSR contain no LEAR (MemCast: "no time-series foundation models"; the baseline list in CastFSR 4.1.2 has no electricity-specific benchmark).

## 4. Recount method

In PowerShell, group the three columns `control_rung`, `applicable`, `reported` of `applicability_coverage.csv`. For example, the C2 denominator is `control_rung = C2 and applicable = yes`, and the numerator adds `reported = yes`. The data and script that generated the CSV are not part of this repository.
