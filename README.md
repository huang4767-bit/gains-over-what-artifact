# Gains Over What? Artifact

This repository holds the records, codes, criteria, scripts, and outputs behind the paper *Gains Over What? Control Strength and Information Parity in LLM-Based Time Series Forecasting* and its supplementary material. `PAPER_MAP.md` lists, for every table and figure and for the main numbers, the file that holds them.

## Contents

| Folder | Paper | What it holds |
|---|---|---|
| `audit/` | Section 4; Supplement B, D | The 23 audited systems (`corpus.csv`), which no-LLM references apply to each system and which are reported (`applicability_coverage.csv`, `coverage_counts.md`), and one row per printed comparison with both errors (`margin_records.csv`, `margin_summary.md`). The location columns (`source_location` in `margin_records.csv`, `evidence_location` in `applicability_coverage.csv`) give the place in the audited paper that holds the evidence: a table, figure, section or appendix. A reference that the paper does not report reads `not reported ...` (found absent by a full-text search), a rung without its ingredient reads `not applicable ...`, and the 20 C5 cells decided by applicability rule A5 read `rule A5`. Where one table holds several rows, the parenthesis names the rows or columns used. Quotations are in `evidence_quote` for 96 of the 138 applicability rows. For MoiraiAgent, which has no paper, the locations refer to the blog post and the repository README; some TimeCopilot locations refer to its repository README. |
| `coding/` | Sections 3.1-3.2; Supplement C | The codebook, the outcome-redacted input excerpts given to the coder, the input and match codes per experiment and per system, the reference coding, and the agreement between the two. |
| `recheck/` | Section 5; Supplement A, F | The criteria written before each round (`criteria_round1.md`, `criteria_round2.md`), the protocol of every system (`system_protocols.csv`), the scripts, and their outputs. `round1/` covers the first round (12 systems, main reading of eight), `round2/` the second round (five context systems). |
| `electricity/` | Section 6; Supplement E | CastFSR against the public LEAR forecasts on five day-ahead markets (criteria, script, results, a separate recomputation), notes on the inputs in CastFSR's public code, the MemCast window placements, the ARIMA baseline check of CastFSR, and the wind diagnostic. |
| `llmtime_case/` | Supplement A | Seasonal naive and AutoETS on the forecasts released with LLMTime. |
| `environment/` | | Python packages used for the statistical controls. |
| `data/` | | Where to obtain the public data and forecasts that the scripts read. No third-party data are redistributed here. |

## Conventions

- **Ratios.** `r` is the error of the main control divided by the error the system reports, in the paper's main metric, with the geometric mean over datasets; `r > 1` means the system has the lower error. The reported margins in `audit/` use the papers' convention, 100 (E_control - E_system) / E_control.
- **Input codes.** S (substantive inputs), M (metadata), H (history only); match codes: matched, partly matched, not matched, unclear, no comparison.
- **Post hoc.** Analyses added after the results of a round were known are marked post hoc in file names (`out_posthoc_native_period/`, `sensitivity_posthoc.md`) or in the text.
- **Paths.** Outputs and logs were produced on the authors' machines. Local paths in them are replaced by placeholders: `<repo>` is the root of this repository, `<data>` the folder with the public data listed in `data/README.md`, `<work>` a temporary working folder, `<venv>` the Python environment, `<python>` the Python interpreter.
- **Extraction.** Notes in `audit/` that mention "the extraction" refer to the authors' reading of the paper full text, from which the values and quotations were taken.
- **Language.** Some outputs and logs were first written with Chinese labels and messages. These were translated into English for this repository; numbers, column order, and file structure are unchanged. The scripts here print the English labels.

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

The statistical controls use Python with the packages in `environment/requirements.txt` (statsforecast 2.1.1). The electricity scripts use Windows PowerShell 5.1. No step calls an LLM, and no audited system is run.

1. Obtain the public data listed in `data/README.md`.
2. First round: `python recheck/round1/ur_b.py <subcommand> --out recheck/round1/out ...` with the data folders as arguments (`python recheck/round1/ur_b.py -h` lists the subcommands for LLMTime/Darts, Monash, the electricity markets, CastFSR, JudgeCast, MemCast, Time-MMD, and the summary). The read values of MoiraiAgent, TSOrchestra, FASE, and TimeRSI are documented in `recheck/round1/read_values.md`.
3. Second round: `python recheck/round2/ur_c.py <subcommand> ...` (`-h` lists the subcommands for CiK, N2F, Nexus, the CompEvo check, and the summary).
4. CastFSR against LEAR: `electricity/castfsr_lear.ps1 -DataRoot <data>/castfsr_repo_data/raw -LearForecastDir <data>/epftoolbox/forecasts`; `electricity/independent_recompute.ps1` recomputes the same quantities with a separately written script.

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