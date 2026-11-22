# Data sources

The scripts read the following public data. Download them into a folder of your choice and pass its subfolders to the scripts; logs and outputs in this repository refer to that folder as `<data>`.

| Used for | Source |
|---|---|
| LLMTime forecasts, Darts and Monash series | The forecasts and data released with LLMTime (Gruver et al.), https://github.com/ngruver/llmtime |
| Day-ahead electricity prices (BE, DE, FR, NP, PJM) and the published LEAR forecasts | The open benchmark of Lago et al. (2021), https://github.com/jeslago/epftoolbox |
| CastFSR datasets and prompts | The public repository of CastFSR (see the paper's reference), at the commit given in `README.md` |
| GIFT-Eval leaderboard (MoiraiAgent, TSOrchestra) | https://huggingface.co/spaces/Salesforce/GIFT-Eval |
| fev-bench results (TimeRSI) and ENTSO-e data | https://github.com/autogluon/fev |
| Context is Key (CiK, BNP) | The Context is Key benchmark data on Hugging Face (see the paper's reference) |
| From News to Forecast (N2F), CompEvo, Nexus, Time-MMD, ETT, wind data | The data released with each paper (see the paper's references) |

No third-party data are redistributed in this repository.