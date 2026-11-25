# Gains Over What? Artifact

This repository holds the records, codes, criteria, scripts, and outputs behind the paper *Gains Over What? Control Strength and Information Parity in LLM-Based Time Series Forecasting* and its supplementary material. `PAPER_MAP.md` lists, for every table and figure and for the main numbers, the file that holds them.

## Contents

| Folder | Paper | What it holds |
|---|---|---|
| `audit/` | Section 4; Supplement B, D | The 23 audited systems (`corpus.csv`), which no-LLM references apply to each system and which are reported (`applicability_coverage.csv`, `coverage_counts.md`), and one row per printed comparison with both errors (`margin_records.csv`, `margin_summary.md`). `removal_experiment_values.csv` lists the removal-experiment values of Supplement D that need the strongest numerical baseline beside them. The location columns (`source_location` in `margin_records.csv`, `evidence_location` in `applicability_coverage.csv`) give the place in the audited paper that holds the evidence: a table, figure, section or appendix. A reference that the paper does not report reads `not reported ...` (found absent by a full-text search), a rung without its ingredient reads `not applicable ...`, and the 20 C5 cells decided by applicability rule A5 read `rule A5`. Where one table holds several rows, the parenthesis names the rows or columns used. Quotations are in `evidence_quote` for 96 of the 138 applicability rows. For MoiraiAgent, which has no paper, the locations refer to the blog post and the repository README; some TimeCopilot locations refer to its repository README. |
| `coding/` | Sections 3.1-3.2; Supplement C | The codebook, the outcome-redacted input excerpts given to the coder, the input and match codes per experiment and per system, the reference coding, and the agreement between the two. |
| `recheck/` | Section 5; Supplement A, F | The criteria written before each round (`criteria_round1.md`, `criteria_round2.md`), the protocol of every system (`system_protocols.csv`), the scripts, and their outputs. `round1/` covers the first round (12 systems, main reading of eight), `round2/` the second round (five context systems). Each round has a `recomputation_report.md`, an independent recomputation of the main numbers from the stored outputs, written separately from the analysis scripts. |
| `electricity/` | Section 6; Supplement E | CastFSR against the public LEAR forecasts on five day-ahead markets (criteria, script, results, a separate recomputation), notes on the inputs in CastFSR's public code, the MemCast window placements, the weak references on MemCast (`memcast/weak_references/`: criteria, script, outputs, results), the ARIMA baseline check of CastFSR, and the wind diagnostic. |
| `llmtime_case/` | Supplement A | Seasonal naive and AutoETS on the forecasts released with LLMTime. |
| `environment/` | | Python packages used for the statistical controls. |
| `data/` | | Where to obtain the public data and forecasts that the scripts read. No third-party data are redistributed here. |

## Conventions

- **Ratios.** `r` is the error of the main control divided by the error the system reports, in the paper's main metric, with the geometric mean over datasets; `r > 1` means the system has the lower error. The reported margins in `audit/` use the papers' convention, 100 (E_control - E_system) / E_control.
- **Input codes.** S (substantive inputs), M (metadata), H (history only); match codes: matched, partly matched, not matched, unclear, no comparison. Input code N in some older files is H in the paper.
- **Match codes.** In `audit/margin_records.csv`, `match_code` is the record-level code of an earlier coding pass. The paper's match counts use the experiment-level codes in `coding/codes_by_experiment.csv`, mapped as listed in `PAPER_MAP.md`.
- **Post hoc.** Analyses added after the results of a round were known are marked post hoc in file names (`out_posthoc_native_period/`, `sensitivity_posthoc.md`) or in the text. The analysis with the original seasonal periods was decided after the criteria and the read values were fixed and before the rebuilt results existed; it ran after those results and is marked post hoc in the paper.
- **Research groups.** In `recheck/criteria_round1.md`, the systems of one research group are listed in a separate row so that no single group decides the count. In `recheck/system_protocols.csv`, Time-R1, MemCast, and CastFSR share one laboratory (column `lead_institution`), and LSTPrompt and TimeRSI share one research group at one university; the first-round check counts CastFSR from the first laboratory (MemCast is described only) and LSTPrompt and TimeRSI from the second.
- **Paths.** Outputs and logs were produced on the authors' machines. Local paths in them are replaced by placeholders: `<repo>` is the root of this repository, `<data>` the folder with the public data listed in `data/README.md`, `<work>` a temporary working folder, `<venv>` the Python environment, `<python>` the Python interpreter.
- **Extraction.** Notes in `audit/` that mention "the extraction" refer to the authors' reading of the paper full text, from which the values and quotations were taken.
- **Language.** Some outputs and logs were first written with Chinese labels and messages. These were translated into English for this repository; numbers and column order are unchanged. Three summary files whose translated free-text fields contain commas (`recheck/round1/out/ur_b_summary.csv`, `recheck/round1/out_posthoc_native_period/ur_b_summary.csv`, `recheck/round2/out/status.csv`) are written with every field in quotes (RFC 4180), so that every row has the number of fields of its header. The scripts here print the English labels.
## Counting categories

The scripts and their outputs label the categories of the re-check with working names. They correspond to the terms of the paper as follows.

| Label in scripts and outputs | Files | Term in the paper | Definition |
|---|---|---|---|
| `control matched` | per system, `recheck/round1/` (`ur_b_summary.*`, `summary.log`, `read_values.md`, `sensitivity_posthoc.md`) | match | r <= 1.05 |
| `system clearly ahead` | same | ahead | r > 1.05 |
| `matched tier` | reading over all systems, `recheck/round2/` (`ur_c_summary.*`, logs) | match | at least ceil(N/2) systems with r at or below the threshold |
| `ahead tier (counter-evidence)` | same | ahead | at most floor(N/4) systems with r at or below the threshold |
| `mixed tier` | same | mixed | all other counts |
| `close` | same | close | the three thresholds (r <= 1.00, 1.05, 1.10) give different categories |

In `recheck/round2/`, `P1` and `P2` are expectations 1 and 2 of Section 7.1 of `recheck/criteria_round2.md` (r > 1.221 and r > 1.10), `K` is the number of counted systems, and `N_comb` is the number of systems in the combined reading.

## Reproducing the re-check

The statistical controls use Python 3.14.2 (the version recorded in the logs) with the packages in `environment/requirements.txt` (statsforecast 2.1.1); `electricity/memcast/weak_references/memcast_controls_v2.py` additionally needs scikit-learn. Run every Python script with `python -I`. The electricity scripts (`.ps1`) need Windows PowerShell 5.1. No step calls an LLM, and no audited system is run. Obtain the public data of `data/README.md` first; `<data>` below is the folder that holds it.

| Step | Command | Inputs needed | Outputs already in the repository |
|---|---|---|---|
| First round, checksums | `python -I recheck/round1/ur_b.py verify --out recheck/round1/out [--ett-dir D] [--timemmd-dir D] [--entsoe-file F] [--monash-dir D] [--darts-csv-dir D] [--epf-raw-dir D] [--wind-csv F]` | any of the public input folders | `out/verify.csv`, `out/verify.log` |
| First round, LLMTime on Darts | `... ur_b.py llmtime-darts --out <out> --darts-csv-dir D --llmtime-root D [--r12-stat-csv llmtime_case/out/stat_forecasts.csv]` | Darts CSV files, LLMTime repository with its precomputed outputs | `out/llmtime_darts.csv`, `llmtime_darts_points.csv`, `llmtime_darts.log` |
| First round, Monash rows (LLMTime, LSTPrompt) | `... ur_b.py monash --out <out> --monash-dir D --llmtime-root D --r12-monash-csv llmtime_case/out/monash_per_dataset.csv [--datasets a,b]` | Monash `.tsf` archives, LLMTime repository, `llmtime_case/out/monash_per_dataset.csv` (in the repository) | `out/monash_dataset_*.csv`, `monash_series_*.csv`, `monash.log` |
| First round, electricity caches | `... ur_b.py epf-cache --out <out> --raw-dir D [--markets BE,DE,...]`; `... ur_b.py entsoe-cache --out <out> --parquet F` | epftoolbox price files; ENTSO-e parquet file | `out/epf_meta.json` (the cache tables themselves are rebuilt by the command) |
| First round, MemCast and JudgeCast | `... ur_b.py memcast --out <out>`; `... ur_b.py judgecast --out <out>` | the two caches above | `out/memcast_markets.csv`, `memcast_placements.csv`, `memcast.log`; `out/judgecast_datasets.csv`, `judgecast_members.csv`, `judgecast.log` |
| First round, CastFSR | `... ur_b.py castfsr --out <out> --ett-dir D --wind-csv F` | ETT files, CastFSR `wind.csv`, the electricity cache | `out/castfsr_datasets.csv`, `castfsr_windows.csv`, `castfsr.log` |
| First round, Time-MMD | `... ur_b.py timemmd --out <out> --timemmd-dir D [--domains a,b]` | Time-MMD `numerical` folder | `out/timemmd_<domain>.csv`, `timemmd.log` |
| First round, summary | `... ur_b.py summary --out <out> [--r12-darts-metrics llmtime_case/out/darts_metrics.csv]` | the outputs above | `out/ur_b_summary.csv`, `ur_b_summary.txt`, `ur_b_per_dataset.csv`, `summary.log` |
| First round, post hoc | add `--r2-native-period` to any subcommand except `verify` (writes to `<out>/POSTHOC_r2_native_period/`) | as above | `out_posthoc_native_period/` |
| Second round, tests | `python -I recheck/round2/ur_c.py selftest`; `... ur_c.py smoke --parquet F --json F` | CiK parquet file, N2F JSON file | logs in `out/logs/` |
| Second round, CompEvo | `... ur_c.py compevo-check --ext-root D` (uses the network; code is saved as text and not run) | network access | `out/compevo_check.json`, `compevo_check.txt`, `compevo_evidence.txt`, `compevo_tree.csv` |
| Second round, CiK and BNP | `... ur_c.py cik --parquet F` | CiK parquet file | `out/cik_primary.json`, `cik_primary.txt`, `cik_instances.csv`, `cik_forecasts.csv`, `cik_anchor_*`, `cik_sens_freq.csv`, `cik_descriptive.json` |
| Second round, N2F | `... ur_c.py n2f --json F` | N2F JSON file | `out/n2f_summary.json`, `n2f_summary.txt`, `n2f_forecasts.csv`, `n2f_windows.csv` |
| Second round, Nexus | `... ur_c.py nexus` | none (values of Table 1 are in the script) | `out/nexus_r3.csv`, `nexus_r3.json`, `nexus_r3.txt` |
| Second round, summary | `... ur_c.py summary [--out-dir D] [--ur-b-summary F] [--round1-readings F]` | first-round summary, `recheck/round1/read_values.md`, the outputs above | `out/ur_c_summary.json`, `ur_c_summary.txt`, `status.csv` |
| LLMTime case | `python -I llmtime_case/llmtime_controls.py stats --darts-csv-dir D --out <out>` (environment with statsforecast); `... llmtime_controls.py compare --llmtime-root D --darts-csv-dir D [--monash-dir D] [--stat-csv F] [--only all\|darts\|monash] --out <out>` | Darts CSV files, LLMTime repository, Monash files (optional) | `llmtime_case/out/` (statistical forecasts, per-series and per-dataset errors, logs, `summary.txt`) |
| CastFSR against LEAR | `electricity/castfsr_lear.ps1 -DataRoot D -LearForecastDir D [-OutDir D]` (or `-InDir D`) | epftoolbox price files and published LEAR forecasts | `electricity/castfsr_lear_results.csv` (discussed in `results_castfsr_lear.md`) |
| Separate recomputation | `electricity/independent_recompute.ps1 -DataRoot D -LearForecastDir D [-OutDir D]` | same as above | none (it writes `indep.csv`; the agreement is described in `results_castfsr_lear.md`) |
| MemCast, day-aligned placements | `electricity/memcast/epf_dayaligned.ps1 -DataRoot D -LearForecastDir D [-OutDir D]` | same as above | `electricity/memcast/dayaligned_summary.csv`, `dayaligned_placements.csv` |
| CastFSR ARIMA check | `python -I electricity/arima_epf/arima_epf.py --raw-dir D --out D [--markets BE,DE,FR,NP,PJM] [--max-windows N]` | epftoolbox price files | `electricity/arima_epf/out/` |
| Wind diagnostic | `electricity/wind_diagnostic/c2_wind.ps1 -WindCsv F [-OutDir D]` | CastFSR `wind.csv` | `electricity/wind_diagnostic/c2_results.csv`, `c2_per_window.csv`, `c2_log.txt` |
| MemCast weak references | `python -I electricity/memcast/weak_references/memcast_controls_v2.py --csv NP=F --csv PJM=F --csv BE=F --csv FR=F --csv DE=F --test-stride 96 --n-test 30 --out D` | epftoolbox price files | `electricity/memcast/weak_references/out_spread96/`; criteria in `criteria_weak_references.md`, results in `results_weak_references.md` |

### Checks without downloading data

The following numbers can be recomputed from files in this repository alone.

- The coverage counts of Table 2 (for example 11 / 14 for C2): group `control_rung`, `applicable`, and `reported` in `audit/applicability_coverage.csv`, as described in `audit/coverage_counts.md`.
- The counts of experiment codes (35 experiments with substantive inputs, the match tally, the agreement of the two codings): `coding/codes_by_experiment.csv` and `coding/reference_codes.csv`.
- The margin counts (337 banded records, 225 / 45 / 67 by band, the strata of Supplement D): `audit/margin_records.csv`, or the tables of `audit/margin_summary.md`.
- The re-check ratios: the geometric means of the per-dataset ratios in `recheck/round1/out/ur_b_per_dataset.csv`, the values in `ur_b_summary.csv`, the counts at the three thresholds from the eight main ratios in `recheck/round2/out/ur_c_summary.json`, and the read values of `recheck/round1/read_values.md`. The two `recomputation_report.md` files do this independently.
- The CastFSR ratios against the paper's best baseline and against LEAR (`r_LEAR`, the reductions of 17.7-51.6%): `electricity/castfsr_lear_results.csv`.
- The MemCast shares by stride: `electricity/memcast/dayaligned_summary.csv`; the weak-reference counts: `electricity/memcast/weak_references/out_spread96/memcast_controls.txt`.
- The removal-experiment comparisons of Supplement D that are not in `margin_records.csv`: `audit/removal_experiment_values.csv`.
Before computing, `recheck/round2/ur_c.py` checks the size and SHA-256 of its two public input files against pinned values (the Context is Key parquet file and the From News to Forecast JSON file), and the CompEvo check records the SHA-256 of every file it downloads. `recheck/round1/ur_b.py` and `llmtime_case/llmtime_controls.py` pin the public data files in the same way (git blob hash, MD5 or SHA-256). The original run of `ur_c.py` also checked hashes of the authors' own files (the criteria and the first-round result files). These checks were removed from the published script, and their hash values were removed from the outputs and logs; they entered no computation.

## Versions of third-party code and data

| Source | Version used |
|---|---|
| CastFSR public code | commit def273e |
| MoiraiAgent public code | commit cfd46d4 |
| Context is Key data (Hugging Face) | revision 32da467 |
| fev-bench ENTSO-e data | revision d3e7e72 |
| CompEvo repository | commit e320421 |
| GIFT-Eval and fev-bench leaderboard files | read on the day of the analysis (see `recheck/round1/read_values.md`) |

## Licence

Code: MIT. Records, codes, and documentation: CC BY 4.0. See `LICENSE`.