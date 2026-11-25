# Data sources

The scripts read the following public data. Download them into a folder of your choice and pass its subfolders to the scripts; logs and outputs in this repository refer to that folder as `<data>`. Versions (commits, revisions) are listed in `README.md` and in the pins of `recheck/round1/ur_b.py` and `recheck/round2/ur_c.py`.

| Used for | Source |
|---|---|
| LLMTime forecasts, Darts and Monash series | The forecasts and data released with LLMTime (Gruver et al.), https://github.com/ngruver/llmtime; the Monash `.tsf` files come from the Monash Time Series Forecasting Archive on Zenodo (Godahewa et al.) |
| Day-ahead electricity prices (BE, DE, FR, NP, PJM) and the published LEAR forecasts | The open benchmark of Lago et al. (2021), https://github.com/jeslago/epftoolbox; the price files are also on Zenodo (record 4624805) |
| CastFSR datasets (wind data) and prompts | The public repository of CastFSR, https://github.com/Xiaoyu-Tao/CastFSR, at the commit given in `README.md`; `wind.csv` is read from its data folder |
| ETT (ETTh1, ETTh2, ETTm1, ETTm2) | https://github.com/zhouhaoyi/ETDataset (folder `ETT-small`) |
| Time-MMD (TimEvolve, KairosAgent) | https://github.com/AdityaLab/Time-MMD (folder `numerical`) |
| GIFT-Eval leaderboard (MoiraiAgent, TSOrchestra) | https://huggingface.co/spaces/Salesforce/GIFT-Eval |
| fev-bench results (TimeRSI) and ENTSO-e data | https://github.com/autogluon/fev; the ENTSO-e series is in https://huggingface.co/datasets/autogluon/fev_datasets (folder `entsoe/1H`) |
| Context is Key (CiK, BNP) | https://huggingface.co/datasets/ServiceNow/context-is-key (file `data/ICML2025-00000-of-00001.parquet`) |
| From News to Forecast (N2F) | https://github.com/daydreamer-amelia/From_News_to_Forecast (file `AULF_test_data_2021.json`) |
| CompEvo | https://github.com/Aliiina-z/CompEvo (text of the repository only; the check in `recheck/round2/` reads it as text) |
| Nexus | No data files. The values of Table 1 of the Nexus paper are entered in `recheck/round2/ur_c.py` and `recheck/criteria_round2.md`. |
| Other audited systems (for example Time-R1) | Values are read from the printed tables of each paper; no data files are used. |

No third-party data are redistributed in this repository.