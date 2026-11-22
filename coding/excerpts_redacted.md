# Excerpts (verbatim, redacted)

Notation: each line gives [locator] followed by the quoted text between guillemets. "[…]" marks removed text. Mathematical symbols from the HTML sources are rendered as plain text. Arms are named as in the source papers.

=== SYSTEM S01 | Time-R1 | arXiv 2506.10630v4 ===
--- ARM: Time-R1 (full prompt template) ---
- [Sec. 3.3] «Our training template standardizes inputs and encodes task-specific knowledge through five carefully designed components: (1) Task Definition ...; (2) Dataset Description specifying temporal characteristics and application scenarios; (3) Channel Information ...; (4) Testing Data providing timestamps and historical series; and (5) Format Instruction»
- [Sec. 4.3] «(ii) contextual information such as seasonal period and task constraints»
- [GenAI disclosure] «DeepSeek-R1 was used to generate candidate forecasts and label-conditioned synthetic reasoning trajectories for constructing the supervised fine-tuning data»
--- ARM: Comparison methods (baselines) ---
- [Sec. 4, baselines] «Baselines follow their official or commonly adopted experimental configurations»
--- ARM: Ablation variants ---
- [Table 4 row labels] «w/o SFT»; «w/o RL»; «w/o Timestamps»; «w/o domain context»
- [Table 5 row labels] «No Think»; «Shuffled Think»; «Corrupted Think»

=== SYSTEM S02 | MoiraiAgent | Salesforce AI Research blog post, 14 January 2026 (no arXiv version) ===
--- ARM: Expert selection (GIFT-Eval) ---
- [Blog, section "[…] time-series forecasting"] «The selection model takes as input a comprehensive set of features: historical numerical values, temporal characteristics (timestamps and recording frequency), predictions from candidate models, and cross-validation errors computed on a short lookback window.»
- [Blog] «Our expert pool comprises three […] models […]: Chronos-v2 (Amazon), TimesFM-2.5 (Google), and Tirex (NXAI).»
- [Blog] «To train the expert selector, we built a dataset of two million training examples»
--- ARM: Context-aware forecasting (GIFT-CTX) ---
- [Blog] «MoiraiAgent addresses this gap by integrating natural language context with numerical time-series data»
- [Blog, GIFT-CTX description] «Each sample in GIFT-CTX is carefully constructed so that accurate forecasts cannot be produced using historical values alone or context alone—both are essential.»
- [Blog, GIFT-CTX description] «120 samples from CIK ... 125 manually created synthetic samples»
- [Blog] «Note that all methods used medium reasoning effort.»

=== SYSTEM S03 | CastFSR | arXiv 2608.03031 (v1, v2, v3) ===
--- ARM: CastFSR, wording of v3 ---
- [v3, Sec. 3.1] «Given historical target observations, historical contextual features, and task description and domain metadata at the forecast origin, context-aware time series forecasting aims to predict future target values by incorporating temporal patterns, contextual evidence, and domain knowledge.»
- [v3, Sec. 3.1] «where X_{1:L} denotes the target history of length L, C contains historical contextual features, D contains the task description and domain metadata, Y-hat_{1:H} denotes the H-step forecast, and f is the forecasting function evaluated at origin t_0. Only information available at the forecast origin is used, excluding forecast-horizon target and covariate values.»
- [v3, Sec. 3.2] «Given target history, historical context, and task metadata, fast-thinking forecasting selects a diagnostic tool and a numerical forecaster to construct a data-driven prior.»
- [v3, Sec. 3.3.1] «Each coordinator request combines a system prompt, stage instructions, and the current state snapshot. The situation and covariate block is cached within a run. Contextual fields are aligned with historical observation timestamps, and all LLM reasoning uses values in their original units.»
- [v3, Sec. 3.3.2] «Future target values are unavailable. All evaluated expert calls, including Chronos-2, use historical target observations and historical covariates according to their input interfaces.»
- [v3, Sec. 3.3.2] «In the evaluated setting, the Context Library in Figure 2 denotes each dataset's existing contextual covariates organized by observation timestamp. It is constructed from the non-target fields accompanying the time series. At each forecast origin, retrieval follows the look-back observation timestamps to obtain C, excluding forecast-horizon covariates.»
- [v3, Sec. 4.1.3] «To prevent information leakage, policy inputs are restricted to historical target observations and covariates, excluding forecast-horizon target and covariate values.»
- [v3, App. C.4, Template 1] «Forecast the next H values using historical targets and covariates, task metadata, domain priors, and tool evidence. Use original units throughout; exclude forecast-horizon target and covariate values.»
- [v3, Sec. 4.1.1] «ETT and Wind are used for long-term forecasting, while EPF focuses on short-term forecasting across multiple electricity markets. ETT includes hourly and sub-hourly observations, Wind provides weather-related covariates, and EPF contains market-specific load and generation covariates.»
- [v3, Sec. 4.1.1] «For long-term evaluation, the look-back length, horizon, and stride are all 96 steps. […] For EPF, we retain the final 604 days per market, using a 168-hour look-back, 24-hour horizon, and 48-hour stride.»
- [v3, App. A.1] «ETT: In the electricity transformer temperature benchmark (Zhou et al., 2021), oil temperature (OT) is the forecasting target, and HUFL, HULL, MUFL, MULL, LUFL, and LULL are the six load features.» «Wind: This dataset is distributed with the TFB benchmark (Qiu et al., 2024) and covers 2020-01-01 00:00 through 2021-05-22 00:00, inclusive. Wind power is the target. Its contextual fields are predicted humidity, pressure, temperature, wind direction, wind speed, and observed wind speed.»
- [v3, App. A.2] «The EPF data come from Lago et al. (Lago et al., 2021), with market price as the target and ComEd prices used for PJM. Covariates are day-ahead forecasts: BE uses French load and generation; DE uses aggregated wind and solar generation and Amprion load; FR uses load and generation; NP uses grid load and wind generation; and PJM uses system and zonal loads.» «Validation and test examples reuse the preceding 168 hours as historical context; their forecast targets remain within the assigned partition.»
- [v3, App. A.3] «Each forecast origin is the first target timestamp. The first origin is 2018-02-01 00:00 for all four ETT datasets and 2021-02-10 00:00 for Wind. For EPF, the first origins are 2016-09-04 00:00 for BE and FR, 2017-09-04 00:00 for DE, and 2018-08-28 00:00 for NP and PJM. Each EPF market has 60 origins spaced 48 hours apart. Each window scores the next 24 hourly values […]. All methods use the same forecast origins and target timestamps under this protocol.»
--- ARM: CastFSR, wording of v1 and v2 (identical in these passages) ---
- [v1 and v2, Appendix "Prompt Construction Details"] «Each prompt contains the shared forecasting situation, including task metadata, domain priors, timestamp scope, sampling frequency, target variable, and available future-known covariates.»
- [v1 and v2, "Fast–Slow Agentic Forecasting Prompt", Role & Context] «All decisions remain target-blind, grounded in historical observations, task and domain priors, temporal context, available future-known covariates, diagnostic evidence, and auxiliary forecasts.»
- [v1 and v2, "Overview / Sequential Forecasting Formulation"] «H_ctx denotes available contextual histories or future-known contextual resources.»
--- ARM: Numerical experts and comparison methods ---
- [v3, App. C.3] «The shared expert pool comprises ARIMA, DLinear, PatchTST, iTransformer, and Chronos-2.»
- [v3, Sec. 4.1.3] «Both variants employ ARIMA, DLinear, PatchTST, iTransformer, and Chronos-2 as numerical forecasting tools, retaining their respective fitting or pretraining procedures. Deep learning baselines follow their official configurations.»
- [v3, Sec. 4.1.2] «The statistical baselines are ARIMA (Box et al., 2015) and Prophet (Taylor and Letham, 2018). Neural baselines include DLinear (Zeng et al., 2023), ConvTimeNet (Cheng et al., 2025a), PatchTST (Nie et al., 2023), iTransformer (Liu et al., 2024), and TimeXer (Wang et al., 2024). We also compare with foundation models TimesFM (Das et al., 2024), Sundial (Liu et al., 2025), and Chronos-2 (Ansari et al., 2025).»
- [v3, App. B] «Chronos-2 (Ansari et al., 2025) supports zero-shot forecasting with multivariate inputs and covariates.»
--- ARM: Fixed-expert comparison (Table 4) ---
- [v3, Sec. 4.3.2] «Table 4 compares adaptively selected experts with the best fixed expert in the candidate pool for each dataset, using the same expert as the reference for both metrics. The comparison considers direct expert forecasts before slow or reflect.»
--- ARM: Context ablation (Figure 5) ---
- [v3, Sec. 4.3.4] «Both variants share the same numerical prior, with historical covariates retained in the numerical expert's inputs. The w/o context variant removes contextual evidence only from the slow stage, isolating its contribution to forecast refinement.»

=== SYSTEM S04 | Bridging the Last Mile | arXiv 2606.02497v1 ===
--- ARM: Framework (all case studies) ---
- [Sec. 4.4] «The baseline forecast is produced from the observed series, but many revision decisions depend on information outside that series. The agent therefore uses tools to read different evidence sources, such as past windows in the same workspace, calendar events, external event descriptions, or memories from previous forecast outcomes.»
- [Sec. 5.1] «The agent is designed as a code-executing agent equipped with tools for baseline forecasting, historical data retrieval, holiday lookup, memory query, and long-horizon map-reduce planning. In this work, TimesFM is used to generate the baseline forecast.»
- [App. B.4, Table 7] «Holiday lookup provides calendar information for future event windows»; «Historical retrieval retrieves past windows from the current series»; «Memory query retrieves prior reflection entries for similar events and recent experience»
- [App. B.1, Listing 1] «Revision policy (evidence priority) realized multipliers from reflection > memory critiques > historical same-period ratios > user instructions.»
- [App. B.2, Listing 2] «Ground the magnitude: retrieve_history_tool over the same-period window returned by holiday_search_tool; compute realized/baseline ratio.» «override (per-day values from a historical analog) for distinctive shapes.»
- [App. C.1, revision record] «Override uses day-by-day 2025 analog values as the 2026 forecast»
- [Sec. 5.2] «A daily ticket-sales dataset from a popular domestic air route in China, covering 2024-01-01 to 2026-05-05. All three case studies in Sections 5.3–5.5 share this dataset; they differ only in the forecast origin and horizon.»
- [Sec. 5.2] «For the case studies in Sections 5.3 and 5.4, we evaluate three methods: Prophet (Taylor and Letham, 2018), TimesFM, and our framework. TimesFM is used without task-specific fine-tuning, while Prophet is fitted on the available history with holiday information. In each case study, all methods are evaluated from the same forecast origin over the same target horizon.»
--- ARM: Holiday-aware forecast revision (Sec. 5.3, Table 3) ---
- [Sec. 5.3] «All three methods are evaluated from 2026-02-01, over a 23-day horizon ending on 2026-02-23. The horizon covers the days before Spring Festival and the official holiday window from 2026-02-15 to 2026-02-23.»
--- ARM: Long-horizon event forecasting (Sec. 5.4, Table 4) ---
- [Sec. 5.4] «All three methods are evaluated from forecast origin 2025-12-31 over a 126-day horizon ending on 2026-05-05. The horizon contains four event windows: New Year's Day, Spring Festival, Qingming Festival, and Labor Day.»
--- ARM: Self-improvement mechanism (Sec. 5.5, Table 5) ---
- [Sec. 5.2] «Section 5.5 reports only our framework, as reflection and memory are internal agent mechanisms rather than numerical forecasting models.»
- [Sec. 5.5] «For W2 and W3 we run two configurations: with-memory, which has access to the memory bank populated by previous reflections, and no-memory (control), in which the memory bank is temporarily hidden from the agent.»
- [Sec. 5.5] «each forecast is produced from an origin one day before the window»
- [App. A.2, Table 6] «Self-improvement (Round 1) 2026-01-05 7 days (2026-01-05 – 01-11)»; «Self-improvement (Round 2) 2026-01-12 7 days (2026-01-12 – 01-18)»; «Self-improvement (Round 3) 2026-01-19 7 days (2026-01-19 – 01-25)»

=== SYSTEM S05 | JudgeCast | arXiv 2609.36966v2 ===
--- ARM: JudgeCast (adjustment of a base forecast) ---
- [Introduction] «a frozen TSFM produces the base forecast from the target's past alone»
- [App. A.1 and Figure 8, prompt] «Covariates available at forecast time, with their descriptions and values»
- [Sec. 4.1, datasets NP, PJM, BE, FR, DE] «two market-specific forecast covariates»
- [Sec. 4.1, dataset Rossmann] «calendar and promotion covariates»
--- ARM: Comparison methods in Table 1 ---
- [Figure caption] «Chronos-2 is the target-only frozen TSFM used as the base forecaster in JudgeCast»
- [Table 1 row labels] «ARIMA»; «Prophet»; «DLinear»; «PatchTST»; «iTransformer»; «TimeXer»; «ConvTimeNet»; «Time-LLM»; «LSTPrompt»; «LLM-Time»; «TimeReasoner»; «MemCast»; «Chronos-2»
- [Baseline descriptions, TimeXer] «covariates at the variate level»
- [Table 2] «TSFM-only rows report base forecasts»
--- ARM: Direct covariate conditioning (Table 5 and Table 7) ---
- [Sec. 4.4 and Table 4] «direct covariate conditioning with Chronos-2»
- [Table 5 and Table 7 row labels] «Target-only»; «Direct cov.»; «JudgeCast»
--- ARM: Ablation (Table 3) ---
- [Table 3] «Explicit Judgment»; «Experience Construction»; «None»

=== SYSTEM S06 | Informed Forecasting | arXiv 2505.10213v3 ===
--- ARM: All prompt formats (common setting) ---
- [Sec. 4] «Our objective is to predict future values y_{T+1},…,y_{T+H} given a history of past observations y_{1},…,y_{T} and the covariates x_{1},…,x_{T+H} where T and H denote the length of the observed data and the forecast horizon, respectively.»
- [Sec. 4] «the covariates, which are known exogenous variables aligned with the time series that may influence future outcomes and are available both for the observed data and forecast horizon.»
- [Sec. 4] «To assess model performance, we partition the dataset into a validation set and a test set, where the validation set is used to choose the best prompt-covariate pair.»
- [Sec. 4.1] «Specifically, we focus on prompts that rely solely on observed time series data and avoid the use of external knowledge or example completions.»
- [Sec. 5.1] «We evaluate our approach with OpenAI's GPT-4o-mini model on three real-world datasets from healthcare, service operations, and transportation […]. In all cases, covariates are extracted directly from the datasets, such as calendar date, month, or day-of-week, to capture temporal and seasonal patterns beyond the raw time series.»
- [Sec. 5.1, Influenza dataset] «the covariates include the calendar year, the calendar month (e.g., January or February), and a combined year-week indicator (e.g., 2024-W01)»
- [Sec. 5.1, Call Center dataset] «the covariates are the exact date and the day of the week»
- [Sec. 5.1, Air Passengers dataset] «the covariates consist of the exact date and a categorical month-of-year indicator»
- [Sec. 5.1, Influenza dataset] «For evaluation, we used 25 weeks for validation and 25 weeks for testing within the year 2024, and assessed performance over 1-, 2-, and 5-week forecast horizons.»
- [Sec. 5.1, Call Center dataset] «a seven-week interval with three weeks for validation and two weeks for testing. The forecasting horizons include short-term (one day ahead) and mid-term (one week ahead) predictions»
- [Sec. 5.1, Air Passengers dataset] «We used the last four years (January 1956 to December 1959), with the first two years reserved for validation and the final two years for testing. The forecast horizons are 1, 6, and 12 months»
--- ARM: No-Covariate prompt (Baseline) ---
- [Sec. 4.1] «No-Covariate prompt (Baseline). Only the raw sequence of target values without any accompanying temporal or contextual information is included, which serves as a baseline to evaluate the effect of including covariates.»
- [Table 2] «data: [ y_{1} , y_{2} , … , y_{T} ]. Predict the next H values of the time series. Just return the values as a list. No explanation.»
--- ARM: Coupled prompt ---
- [Sec. 4.1] «Each observation is represented as a key-value pair, combining covariates with their corresponding target values in an ordered sequence. Forecasting is performed by adding future covariates without associated targets.»
- [Table 2] «x_{1}:y_{1} , x_{2}:y_{2} , … x_{T}:y_{T} , x_{T+1} : , x_{T+2} : , … x_{T+H} : Predict the next H values in the time series. Just return the values as a list. No explanation.»
--- ARM: Decoupled prompt ---
- [Sec. 4.1] «Covariates and target values are separated into distinct lists. The prompt contains both target values and covariates for the observed data and asks to forecast future targets using a list of upcoming covariates.»
--- ARM: Contextualized prompt ---
- [Sec. 4.1] «This format extends the Decoupled structure by adding context about the covariates. […] The prompt avoids revealing dataset-specific details and instead leverages the pre-trained knowledge of the LLM through high-level information.»
--- ARM: PromptCast ---
- [Sec. 4.1] «This format presents the input as a compressed natural language sentence that implicitly integrates covariate and target information.»
--- ARM: Knowledge-Guided prompt ---
- [Sec. 4.1] «This format builds on the Decoupled structure by including domain-specific knowledge, such as the subject or source of the time series (e.g., 'This series represents US electricity demand').»
--- ARM: Covariate censoring (Sec. 6.4, Table 7) ---
- [Sec. 6.4] «Next, we examine how sensitive the forecasts are by analyzing the effect of random censoring of covariates on the evaluation metrics. Table 7 reports the forecast results when covariates are subjected to random censoring at different ratios.»
--- ARM: ARIMA and LSTM (Sec. 6.5, Table 8) ---
- [Sec. 6.5] «In particular, we compare our methods with ARIMA, a widely used classical statistical model, and LSTM, a standard deep learning baseline.»
- [Sec. 6.5] «All experiments were carried out in the same setting, using identical datasets, forecast horizons, and validation/test splits.»

=== SYSTEM S07 | Context is Key | arXiv 2410.18959v4 ===
--- ARM: With Context (LLM-based forecasters) ---
- [Abstract] «we introduce "Context is Key" (CiK), a time series forecasting benchmark that pairs numerical data with diverse types of carefully crafted textual context, requiring models to integrate both modalities; crucially, every task in CiK requires understanding textual context to be solved successfully.»
- [Sec. 3.2] «For each task in the benchmark, we jointly sample numerical data from one of the series described in Sec. 3.1 and then manually craft the natural language context necessary to unlock accurate forecasts.»
- [Sec. 5.2] «We propose "direct prompt", a simple approach where we instruct the model to directly output a forecast as a structured output for all of the required timestamps (see Sec. D.1 for more details).»
- [Sec. 5.2] «We also evaluate LLM Processes (llmp; Requeima et al. (2024)), a method which autoregressively prompts the LLM multiple times to output a forecast.»
- [Sec. 5.2] «We also evaluate multimodal forecasting models, ChatTime (Wang et al., 2025) (zero-shot), UniTime (Liu et al., 2024c) and Time-LLM (ETTh1) (Jin et al., 2024) (trained according to their respective authors' guidelines)»
--- ARM: Without Context (same LLM-based forecasters) ---
- [Sec. 5.2] «For all of these approaches, inference is performed zero-shot on the benchmark and we compare their performance with and without the natural language context.»
- [Table 3 column labels] «With Context»; «Without Context»
--- ARM: Quantitative forecasting models ---
- [Sec. 5.2] «Quantitative Forecasting Models: We also evaluate a number of models that process only numerical data, but cannot integrate natural language. We evaluate Exponential Smoothing (Gardner Jr. (1985)), ETS (Hyndman et al., 2008), and ARIMA (Box et al., 2015) […]. We also evaluate four […] TSFMs: Lag-Llama (Rasul et al., 2023), Chronos (Ansari et al., 2024), Moirai (Woo et al., 2024) and TimeGEN (Garza et al., 2023).»
- [Sec. 5.2] «We fit Exponential Smoothing, ETS and ARIMA to the individual numerical history of each task instance, which is the same input that the TSFMs process to produce forecasts zero-shot.»
- [Table 1 caption] «An asterisk (*) denotes models that do not use natural language context.»

=== SYSTEM S08 | KairosAgent | arXiv 2605.30002v2 ===
--- ARM: KairosAgent (reasoner with tools, then text-conditioned forecaster) ---
- [Sec. 3.1] «We denote the historical observations within a lookback window of length L as X=(x_1,x_2,…,x_L), while c represents the optional textual context (e.g., dataset metadata or variable-level information).»
- [Sec. 3.2] «Given the historical observations X and textual context c, the LLM-based reasoner interacts with the tool set T to inspect both global and local temporal structures (e.g., trend, periodicity, volatility, and regime changes; Appendix B.2).» «Based on the tool outputs and its own world knowledge, the reasoner synthesizes a compact morphology description r.»
- [Sec. 3.2] «A text encoder (GIST (Solatorio, 2024)) followed by a projection layer (MLP) maps the morphology description into the hidden space of Kairos»
- [App. B.2] «The agent is equipped with 23 statistical analysis tools adapted from tsfresh (Christ et al., 2018). All tools operate on a user-specified window [left, right) of the history»
- [App. B.4] «When metadata is available, the prompt provides the dataset name, domain, frequency, dataset description, variable name, variable description, unit, timestamp ranges for history and both future windows, and the comma-separated history values.» «When metadata is masked, all metadata fields are replaced with unavailable, and only the history length, forecast horizons, and raw history values are provided.»
- [App. C.3.1, KairosAgent] «The reasoner receives textual context on both Time-MMD and Time-IMM. We annotate the evaluation datasets with metadata following the same format used during training.»
- [App. I, prompt example] «Dataset: SHMetro; Domain: Transport; Frequency: 15T; Variable: inbound_passenger_count; History window: ...; Future window (short term): ..., horizon: 96»
--- ARM: Comparison methods on Time-MMD ---
- [App. C.3] «(i) Zero-shot TSFMs: Aurora (Wu et al., 2025b), Sundial (Liu et al., 2025d), Moirai (Woo et al., 2024), and ChronosBolt (Ansari et al., 2024); (ii) Full-shot multimodal models: T3Time (Chowdhury et al., 2026), TimeCMA (Liu et al., 2025b), CALF (Liu et al., 2025c), TiMi (Lin et al., 2026), IMM-TSF (Chang et al., 2026), and Time-MMD (Liu et al., 2024), which leverage both textual and numerical modalities but require task-specific supervised training; (iii) Full-shot unimodal models: PatchTST (Nie et al., 2023) and DLinear (Zeng et al., 2023), which operate solely on numerical time series with full supervision.»
- [App. C.3.1, Full-shot Multimodal Models] «We follow the original textual-input construction protocols of each model rather than supplying benchmark metadata directly. T3Time (Chowdhury et al., 2026) and TimeCMA (Liu et al., 2025b) construct template-based prompts from the numerical history. CALF (Liu et al., 2025c) uses embedding-level textual tokens extracted from the pretrained LLM vocabulary space.»
- [App. C.3.1, Zero-shot Multimodal Foundation Model] «For Aurora (Wu et al., 2025b), we use the textual prompts provided in its original paper.»
- [App. C.3.1, Zero-shot TSFMs and Unimodal Models] «Sundial (Liu et al., 2025d), Moirai (Woo et al., 2024), ChronosBolt (Ansari et al., 2024), PatchTST (Nie et al., 2023), and DLinear (Zeng et al., 2023), do not accept textual input.»
--- ARM: Comparison methods on Time-IMM ---
- [Table 13 column labels] «Fine-Tuned Forecaster»; «Pretrained Forecaster»; «KairosAgent»
- [Figure 6 caption] «'w/o text' denotes the pretrained unimodal forecaster.»
- [App. E.1] «(ii) pretrained forecaster, which retains the original Kairos weights and corresponds to 'w/o text' in Figure 6»
- [Time-IMM baselines] «the results are directly adopted from TiMi»
--- ARM: Additional zero-shot foundation models (App. H.2, Table 22) ---
- [Table 22 column labels] «Kairos»; «Chronos-2»; «TiRex»; «Moirai-2»

=== SYSTEM S09 | MUSE-Bench refinement | arXiv 2609.15087v1 ===
--- ARM: LLM-guided refinement of Chronos2 (Sec. 4.2.3, Table 11) ---
- [Sec. 4.2.3] «We evaluate LLM-guided refinement with Chronos2 on all fourteen datasets and visualize four representative datasets from different domains in Figure 3.»
- [Sec. 4.2.3] «Chronos2 first generates a numerical forecast, which Qwen3.6 then refines using context available at prediction time under multimodal prompting. Prompts are in Figure 5.»
- [App. C.2] «Figure 5 presents the prompt for LLM-guided refinement of TSFM forecasts. In this setting, the forecast produced by TSFMs is treated as the numerical baseline, and the LLM is instructed to modify it only when the supplied context provides clear and time-aligned evidence for a correction. To reduce unsupported adjustments, the prompt favors conservative revisions and limits the magnitude and temporal scope of each correction.»
- [App. C.2, Table 11 title] «MASE comparison between Chronos2 and Qwen-refined forecasts.»
- [App. C.1.1] «Chronos2 (Ansari et al., 2025) employs group attention to exchange information among related series, allowing a single pretrained model to perform zero-shot univariate, multivariate, and covariate-informed forecasting.»
--- ARM: Direct LLM forecasting (Table 3) ---
- [Sec. 4.1, LLM paragraph] «where historical observations and contextual information are serialized into prompts and future values are generated as text. We evaluate this paradigm using both general-purpose and time-series-adapted LLMs under multimodal prompting.»
- [App. C.2] «As illustrated in Figure 4, the direct-forecasting prompt requires the LLM to generate future values directly from the normalized target history and the available, temporally aligned contextual information.»
- [Sec. 3.2.2] «MUSE-Bench further includes general-purpose LLM baselines, such as ChatTime (Wang et al., 2025a), Qwen3.6-27B-Prompt (Team, 2025) and Gemma-4-26B-A4B-it (Team et al., 2026), which are evaluated under standardized prompting settings for direct forecasting, context interpretation, or forecast revision.»
--- ARM: Numerical-only and context-aware model groups ---
- [Sec. 3.2] «Based on the information available at inference time, the evaluated models are grouped into numerical forecasting models and context-aware forecasting models. The former establishes […] baselines using historical time series, whereas the latter additionally incorporates metadata, textual, or event-based context.»
- [Sec. 3.2.1] «Statistical approaches provide transparent reference baselines, including SeasonalNaive, Moving Average SeasonalNaive, LastValueNaive, and MeanForecast.» «Time series foundation models further represent the large-scale pretraining paradigm, including Chronos2 (Ansari et al., 2025), Toto2 (Khwaja et al., 2026), TimesFM (Das et al., 2024), Moirai2.0 (Liu et al., 2025a), Moirai1.0 (Woo et al., 2024), Timer-S1 (Liu et al., 2026c), Sundial (Liu et al., 2025e), Time-MOE (Shi et al., 2025), and Timer (Liu et al., 2024d). Together, these methods provide numerical-only references ranging from dataset-specific supervision to cross-domain pretraining.»
- [Sec. 3.3.2] «Foundation models are directly evaluated using their pretrained checkpoints without adaptation to the evaluation datasets, thereby measuring their zero-shot generalization ability.»
--- ARM: Benchmark input conventions (all arms) ---
- [Abstract] «fourteen datasets across eight domains and six types of context: metadata, events, holidays, news, images, and numerical covariates.»
- [Sec. 3.1.2] «The target series and numerical covariates are stored independently and indexed by timestamps […]. Textual descriptions, events, holidays, and visual information follow a unified context schema that accommodates both regularly collected records and sparse events.»
- [Sec. 3.1.2] «At each forecast origin, models can access only numerical observations and contextual records available at prediction time, while legitimately known future events remain accessible under the same temporal constraint.»
- [Sec. 3.3.3] «For every forecast origin, numerical observations and contextual information are filtered according to their actual availability. Context describing a future event is accessible only when it is known before prediction, which distinguishes legitimate known-future information from post-event evidence.»

=== SYSTEM S10 | Nexus | arXiv 2605.14389v2 ===
--- ARM: Nexus on Leaf (event records) ---
- [Sec. 2] «let X_{1:τ}=(x_1,x_2,…,x_τ) represent a univariate numerical time series observed over a context window of length τ. Concurrently, let E_{1:τ}=(e_1,e_2,…,e_τ) represent the associated unstructured textual data for each timestep in the context window.»
- [Sec. 3, overview] «In the first stage of temporal profiling (§3.1), an LLM analyzes numerical sequences and dated event records to distill a causal-temporal profile, committing a purely historical forecasting anchor via a TSFM or a tailored forecasting model.»
- [Sec. 3.1] «the agent crafts a tailored prediction code in an isolated sandbox restricted to X_{1:τ}, or selects from a pool of pre-trained TSFMs (Chronos-2, TimesFM-2.5, and TiRex).»
- [Sec. 3.1] «By aligning historical regime changes with synchronous records in E_{1:τ}, the agent distills the history into a structured causal-temporal profile I_{1:τ}»
- [Sec. 3.2] «the forecasting anchor π (Section 3.1) […] operates in a contextual vacuum and cannot anticipate regime shifts driven by qualitative catalysts in E_{1:τ}. To incorporate these signals, Nexus queries the LLM […] through two contextual streams, macro and micro, each combining the causal-temporal profile I_{1:τ} with calibrated context C_ctx.»
- [Sec. 4.1] «LEAF [Tan et al., 2026] provides dense event records across domains like temperature and electricity, with data postdating September 2025 to rule out parametric leakage»
- [App. A, Leaf] «Leaf [Tan et al., 2026] is a living benchmark that pairs numerical series with fact-checked, timestamped events, with forecast origins placed after the knowledge cutoff of the evaluated models. It covers hourly weather (ten cities) and electricity load (three regions), forecast 72 steps ahead from origins between October 2025 and July 2026, and daily equity and commodity prices, forecast three and seven trading days ahead from origins between September 2025 and January 2026. We use the benchmark's own forecast windows.»
- [Sec. 4.1, baselines] «We compare against four baseline families: (i) Supervised deep models: Autoformer [Wu et al., 2021], TimesNet [Wu et al., 2023], PatchTST [Nie et al., 2023], iTransformer [Liu et al., 2024b], and TimeMixer [Wang et al., 2024], we trained these baselines per domain using the Time-Series-Library protocol [Wang et al., 2026] prior to the evaluation period, (ii) LLM-based supervised models: the parameter-efficient reprogramming architectures One-Fits-All [Zhou et al., 2023] and Time-LLM [Jin et al., 2024] - also supervised trained on the entire domain, (iii) Zero-shot foundation models: TimesFM-3.0 and TimesFM-2.5 [Das et al., 2024], Chronos-2 [Ansari et al., 2025], Chronos-Bolt [Ansari et al., 2024], TiRex [Auer et al., 2025], and Moirai-2.0 [Liu et al., 2025], and (iv) Language models with event records: Gemini-3.1-Pro and Claude-Sonnet-4.5 using Leaf's official prompts, alongside MoiraiAgent. All baseline prompts are used from their benchmarks.»
- [Table 1 caption] «[…] Gemini-3.1-Pro and Claude-Sonnet-4.5 is driven by the benchmark's own prompt with the event record, MoiraiAgent is the released selector on the input history. […]»
--- ARM: Component rows on Leaf (Table 5) ---
- [Table 5 caption] «Contribution of each component and of calibration on the Leaf windows of Table 1 (Gemini-3.1-Pro). The first three rows forecast with one component alone; the fourth combines all three with fixed equal weights and no calibration.»
- [Table 5 row labels] «Forecasting anchor π»; «Nexus w/o calibration»
--- ARM: Nexus on GIFT-CTX (single shock description) ---
- [Sec. 4.1] «GIFT-CTX [Salesforce AI Research, 2026] pairs numerical sequences with natural-language descriptions of isolated regime shifts and shock events»
- [App. A, GIFT-CTX] «GIFT-CTX [Salesforce AI Research, 2026] contains 245 instances, 120 real series from CIK and 125 synthesized from GIFT-Eval, each paired with a single textual description of an anomaly, a phase change or an upcoming event. The description is localized to a region of the horizon that the metric weights more heavily.»
- [Sec. 4.3] «GIFT-CTX evaluates zero-shot adaptation when the context is a single shock description localized to a region of the forecast horizon. In addition, the numerical histories are too short to support causal temporal profiling or to construct the disjoint rolling backtest folds D_hist required for empirical calibration (Section 3.2). Consequently, the stream error covariances (Omega_macro, Omega_micro) cannot be estimated. Nexus therefore falls back to an equal-weight average of the macro and micro outlooks.»
- [Table 2 caption] «[…] on GIFT-CTX, across all 245 instances […]. Nexus runs on Gemini-3.1-Pro; the Gemini-3.1-Pro row is the benchmark's agent harness. † denotes original GIFT-CTX Leaderboard entries.»
--- ARM: Nexus on GIFT-Eval (numerical series) ---
- [Sec. 4.1] «GIFT-Eval [Aksu et al., 2024] evaluates zero-shot numerical extrapolation without textual context across healthcare and sales domains.»
- [App. A, GIFT-Eval] «GIFT-Eval [Aksu et al., 2024] is the standard leaderboard for zero-shot numerical forecasting and provides no multimodal context, therefore it isolates the numerical capability of Nexus. […] On the remaining five configurations (Table 6) we use the leaderboard's windows, horizons and seasonal periods, and report MASE.»

=== SYSTEM S11 | From News to Forecast | arXiv 2409.17515v3 ===
--- ARM: Filtered News and Non-Filtered News (LLM with news) ---
- [Fig. 1 and Sec. 4.1] «news is retrieved to align with time series data»
- [App. A.3, example] «On 2019-11-09 08:51:00, the news can change the time series fluctuation that The ongoing fires lead to ...»
- [Sec. 4.1, "Supplementary information"; App. A.3 example] «Weather forecast of the prediction date: the minimum temperature is 284.92 ...»
--- ARM: Only Numeric Prompt; Textual Prompt without News (LLM without news) ---
- [Table 1 row labels] «Only Numeric Prompt»; «Textual Prompt without News»; «Non-Filtered News»; «Filtered News»
- [App. Table 6 row labels] «Only Numeric Prompt with all Supplementary Information»; «Filtered News (No Supplementary Information)»
--- ARM: Comparison methods (Table 3) ---
- [App. A.1] «When conducting comparative experiments, all the information utilized in our method, except for the news content, is also provided to the baseline methods. ... For non-numeric variables, we represent them using dummy variables for these baseline methods.»
- [Table 3 column labels] «Auto»; «In»; «Dlin»; «iTrans»; «FiLM»; «Times»; «Pyra»; «PatchTST»; «FED»; «GPT4TS»

=== SYSTEM S12 | FASE | arXiv 2609.32689v1 ===
--- ARM: FASE (full system) ---
- [Sec. 3.1] «For each forecasting instance, the forecasting tools and the LLM receive different representations of the observed history. Each forecasting tool operates directly on the original numerical values.»
- [Sec. 3.1] «FASE therefore represents the observed history using a fixed collection of statistical features, which summarise properties such as scale, trend, periodicity, temporal dependence, and missingness.»
- [Sec. 3.1] «FASE provides the LLM with the task context, statistical representation, retrieved experience, available policy guidance, and descriptions of the forecasting tools. The LLM selects a single tool to produce the point forecast and corresponding quantile forecasts for the current forecasting instance.»
- [Sec. 4.2] «The features characterise temporal dynamics, missingness, periodicity, covariate relationships, and other properties of the history.»
- [Sec. 3.2] «After the ground-truth target for a forecasting instance becomes available, FASE organises the statistical representation, task context, invoked tool, and observed errors into an episodic memory entry for subsequent retrieval. For each candidate tool, the entry records the point forecast error and its corresponding rank, together with the probabilistic forecast error as auxiliary feedback.»
- [Sec. 3.2] «Given the current statistical representation s_i, FASE ranks all active entries according to d(s_i,s_j), retrieves those with the smallest distances, and presents their contextual statistics and observed tool performance to the LLM as evidence for selecting the current action.»
- [Sec. 5.4] «Episodic memory influences tool use by retrieving completed instances with contexts similar to the current forecasting instance and presenting the observed performance of each forecasting tool in those instances.»
- [App. B] «The LLM chooses its action using the current statistical context and any memory or policy information derived from previously completed instances. […] The candidate forecasts are not provided to the LLM, and none of the tools has access to the target during inference.»
- [Sec. 4.1] «We evaluate FASE on 29 dataset configurations selected from the 97 configurations in GIFT-Eval (Aksu et al., 2024), retaining those with 500 to 5,000 forecasting instances in the test split.» «We follow the GIFT-Eval protocol for test splits and the construction of forecasting instances.»
--- ARM: Fixed forecasting tools (individual model baselines) ---
- [Sec. 4.2] «FASE uses a fixed tool pool that comprises Seasonal Naive and five time-series foundation models: Chronos-2 (Ansari et al., 2025), TimesFM 2.5 (Google Research, 2025), Moirai-2.0-R-Small (Liu et al., 2025a), TiRex-2 (Podest et al., 2026), and Toto-2.0-313m (Khwaja et al., 2026). These forecasters also serve as the individual model baselines.»
- [App. B] «At each forecast origin, tool inputs are constructed only from the information available at that time. All evaluated forecasting instances are univariate.»
- [App. B] «Seasonal Naive uses the complete available history and a seasonal period inferred from the sampling frequency. For Chronos-2, TimesFM 2.5, Moirai-2.0-R-Small, TiRex-2, and Toto-2.0-313m, we retain the most recent 8,192, 15,360, 4,000, 8,192, and 4,096 time steps, respectively. Where available, past and known future covariates are supplied to TiRex-2, while Toto-2.0-313m receives past covariates; the remaining tools receive only the target history.»
--- ARM: Uniform Ensemble ---
- [Table 1 footnote a] «Uniform Ensemble averages the forecasts of the five foundation models with equal weights.»
- [App. B] «Uniform Ensemble is constructed by averaging the point forecasts of the five foundation models with equal weights and applying the same averaging operation separately at each quantile level.»
--- ARM: Base Agent ---
- [Sec. 4.2] «To isolate the effects of episodic memory and online policy learning, we define Base Agent as an additional baseline. Its LLM receives only the context of the current forecasting instance, including the statistical summary and descriptions of the available forecasting tools, without retrieved instances or policy guidance.»
--- ARM: Memory Only; Policy Only ---
- [Table 3 caption] «Ablation of episodic memory and online policy learning over the same 29 evaluated GIFT-Eval configurations. Base Agent uses neither mechanism; Memory Only uses episodic memory; Policy Only uses online policy learning; FASE combines both.»
- [App. E] «Memory Only and FASE additionally include the episodic memory instruction and retrieved memory block, whereas Policy Only and FASE include the online policy instruction and ranking block.»

=== SYSTEM S13 | FLAIRR-TS | arXiv 2508.19279v1 ===
--- ARM: FLAIRR-TS (retrieval and iterative prompt refinement) ---
- [Sec. 2.1] «The core iterative cycle ... involves forecasting, evaluating the forecast against recent ground truth (e.g., via a metric like MAE), and refining the prompt.» «This adaptive optimization occurs at test-time without any model training.»
- [Sec. 2.2] «These segments, along with their actual outcomes, ... directly augmenting the context»
- [Algorithm 1, input line] «Training data X, Historical series X_{1:t-1}, Horizon H, Initial prompt P_0, Context length L, #Segments M, Max iterations N_iter, Recent ground truth X_{t:t+H}, Stopping threshold tau_stop»
- [Algorithm 1, line 9] «mae_curr ← CalculateMAE(X-hat_cand, X_{t:t+H})»
- [Algorithm 1, line 13 comment] «Refiner sees history of prompts and errors»
- [App. B, Refiner prompt] «The Ground-Truth OT values.»; «Overall Mean Absolute Error (MAE) for this batch of samples»
- [App. F.3] «ts_sample_size — Value: 3. The number of validation samples used within each refinement iteration to evaluate the quality of a candidate prompt.»
- [App. G] «One direction is to incorporate quantitative validation in the loop: currently, the Refiner-agent's feedback quality is not directly measured. If we had a small hold-out set or could use the model's own likelihood of the data, we might select or weight feedback.»
- [Sec. 3] «report the median performance over five independent runs»
--- ARM: Simple Prompt; +Retrieval; iterative refinement (Fig. 2) ---
- [Sec. 3.1] «We disentangle the impact of Retrieval and Iterative Refinement (IR) by successively activating them on top of a Simple Prompt.»
--- ARM: Comparison methods (Tables 1 and 2) ---
- [Table 1 column labels] «Informer»; «DLinear»; «FEDformer»; «PatchTST»; «TTM»; «Time-LLM»; «LSTP»; «FLAIRR»; «ASP(G2.5P)»; «ASP(G2.0F)»
- [Table 2 column labels] «Informer»; «AutoFormer»; «FedFormer»; «PatchTST»; «LSTP»; «FLAIRR»; «ASP(G2.5P)»; «ASP(G2.0F)»

=== SYSTEM S14 | MemCast | arXiv 2602.03164v2 ===
--- ARM: MemCast (memory-conditioned reasoning) ---
- [Sec. 3.1] «C represents the associated contextual features aligned with the historical observations ... static features C^s and dynamic features C^d»
- [App. A.3, prompt example] «predict Nord Pool electricity prices ... given a 168-hour history (H) and 24-hour future covariate forecasts (F)»; «(2) Future Covariates: Known future values for Load and Wind to guide the forecast trend»
- [Sec. 4.6, case study] «future covariates exhibit an anomalous out-of-distribution (OOD) peak»
- [Sec. 3.6] «A prediction is successful if L_LLM < L_MA»
- [Table 7] «Exogenous Descriptions»
--- ARM: Comparison methods (Table 2) ---
- [Sec. 4.1, Implementation] «Deep learning baselines are trained in PyTorch using the Adam optimizer ... following official implementations and recommended hyperparameter configurations»
- [App. A.2, TimeXer description] «incorporating and aligning exogenous variables»
- [Table 2 row labels] «ARIMA»; «Prophet»; «PatchTST»; «iTransformer»; «TimeXer»; «ConvTimeNet»; «DLinear»; «LSTPrompt»; «LLM-Time»; «TimeReasoner»; «Time-LLM»
--- ARM: Memory ablations (Table 3, Table 5, Table 6) ---
- [Table 3 row label] «w/o All»
- [Table 5, text] «ablation results of textual components»
- [Table 6] «Top-k=1»; «Top-k=3»; «Top-k=5»; «Top-k=7»
--- ARM: Aggregation strategies (Sec. 4.4, Fig. 4) ---
- [Sec. 4.4] «The experiment compares our approach against a baseline without refinement, which relies on a single stochastic pass and a mean ensemble method that averages predictions across M sampled paths.»

=== SYSTEM S15 | TSOrchestra | arXiv 2512.16022v1 ===
--- ARM: TSOrchestra (LLM selects ensemble weights) ---
- [Sec. 3.3, Eq. (4)] «P_cv represents cross-validation performance across all metrics in L, F_data contains dataset characteristics, and K_domain encodes domain knowledge such as model capabilities.»
--- ARM: Weight-selection accuracy (Table 1) ---
- [Table 1 title] «Domain-specific weight selection accuracy over MASE/CRPS»
- [Table 1 row labels] «NA: MSE_Best»; «NA: MAE_Best»; «NA: SMAPE_Best»; «A: GPT-4O»; «A: Sonnet-3.7»; «A: Qwen-2.5-3B»; «A+R1: Qwen-2.5-3B»
- [Sec. 4, text on Table 1] «oracle-style baselines that select weights purely by optimizing a single metric, with no reasoning, adaptation, or forward-looking assessment»
--- ARM: Agent contribution (App. C.1) ---
- [App. C.1, heading] «Isolating the Agent's Contribution»
- [App. C.1] «Random Optimization Metric Ensemble»; «serving as a stochastic control»
--- ARM: Direct LLM weight prediction (Figure 3) ---
- [Figure 3, right panel label] «Direct LLM weight prediction without iterative refinement»

=== SYSTEM S16 | CompEvo | arXiv 2609.09195v1 ===
--- ARM: CompEvo (news-driven multi-agent system) ---
- [App. D.3, template] «Predict next-day load for VIC. Context includes date, holiday status, weather, and aligned news with rationales.»
- [Sec. 3] «the time-aligned public news pool»
- [Sec. 5.4] «Uniform Weights: replaces fitness-based selection with equal aggregation (w_i = 1/I).»
- [Table 5 row labels] «Uniform Weights»; «Simplified Logic Gen»
--- ARM: Numerical forecasting baselines ---
- [Sec. 5.1] «(1) Numerical forecasting baselines, which rely solely on historical time-series signals»
- [App. D.4] «These methods rely solely on historical time-series numerical data for forecasting.»
- [Table 1 column labels] «DLin.»; «iTrans.»; «FiLM»; «Pyra.»; «FED.»; «GPT4TS»
--- ARM: News-consuming baselines and multi-agent baselines ---
- [App. D.4] «methods that consume news receive the same candidate news pool»
- [Table 1 column labels] «N2F»; «GPT4MTS»; «LTP-LLM»
- [App. D.4] «MAEL (Multi-Agent Ensemble Learning): A parallel-agent averaging baseline without interaction or evolution.»
- [Table 3 column labels] «MAEL»; «MAD-RL»
- [App. D.3] «The input-output construction follows Wang et al. (2024)»
- [Sec. 5.1] «The comparison is not capacity matched»
--- ARM: News perturbation (Sec. 5.8, App. E.2) ---
- [Sec. 5.8 and App. E.2] «shuffled news order (Shuffle), irrelevant news injection (Irrel.), and noisy news injection (Noisy)»

=== SYSTEM S17 | LSTPrompt | arXiv 2402.16132v1 ===
--- ARM: LSTPrompt ---
- [Sec. 2.2] «it prompts tasks with specific datasets, decomposes tasks into short-term and long-term sub-tasks, and guides LLMs to incorporate appropriate forecasting mechanisms and domain knowledge.»
- [Sec. 3.3] «the most suitable LLMs (e.g., GPT3.5-Turbo-Instruct for LLMTime and GPT4 for LSTPrompt)»
--- ARM: LLMTime (naive prompt) ---
- [Figure 1 caption] «Comparison between naive prompt Gruver et al. (2023) and LSTPrompt»
--- ARM: Prompt ablations (Sec. 3.3) ---
- [Sec. 3.3] «three ablated versions of LSTPrompt: (1) Base, using standard prompts; (2) LSTPrompt\TD ...; (3) LSTPrompt\TB»
--- ARM: Other comparison methods ---
- [Table 1 column labels] «SP»; «ARIMA»; «TCN»; «N-BEATS»; «TimesFM»; «LLMTime»; «LSTPrompt»
- [Table 2 column labels] «Informer»; «AutoFormer»; «FedFormer»; «PatchTST»; «LPTM»; «LLMTime»; «LSTPrompt»

=== SYSTEM S18 | LLMTime | arXiv 2310.07820v3 ===
--- ARM: LLMTime (all benchmark experiments) ---
- [Abstract] «By encoding time series as a string of numerical digits, we can frame time series forecasting as next-token prediction in text.»
- [Sec. 1] «At its core, this method represents the time series as a string of numerical digits, and views time series forecasting as next-token prediction in text»
- [Sec. 2, "Our work"] «Unlike PromptCast, we show that LLMs can be used directly as forecasters without any added text or prompt engineering, if we carefully preprocess the numerical values themselves. Our method solely relies on LLM's abilities to extrapolate patterns in general sequences and nothing particular to English or any other language.»
- [Sec. 4, Informer datasets] «In order to predict multivariate data with LLMTime, we forecast each covariate independently.»
- [App. C.2, GPT-3 hyperparameters] «To avoid exceeding the context window, we truncate the history to at most 500 most recent observations.»
- [App. C.3, LLaMA-2 70B hyperparameters] «The series in the Informer datasets are very long and we put as much as possible in the LLaMA-2 context window (4096).»
- [Sec. 6, "Connecting time series and textual understanding"] «we can augment the numerical time series with useful text. We can do so either by providing textual side information as inputs, or by producing textual outputs from a given time series.»
--- ARM: Darts benchmark comparison methods ---
- [Sec. 4, Datasets] «Darts [24]: A collection of 8 real univariate time series datasets. For Darts, we use several methods that are implemented directly in the package, including neural network models (TCN [29], N-BEATS [38], N-HiTS [11]) and simple moving average models (ARIMA [8]). […] We also include Spectral Mixture Gaussian Process (SM-GP) [49], a Bayesian nonparametric method (details in Appendix C.1).»
- [App. C.1] «The test set is the last 20% of each series.»
--- ARM: Monash benchmark comparison methods ---
- [Sec. 4, Datasets] «Monash [19]: The Monash forecasting archive contains 30 publicly available datasets along with baseline numbers for 12 forecasting models, including simple exponential smooth (e.g. ETS [27]), gradient boosting (e.g. CatBoost [40]) and deep learning models (e.g. DeepAR [41], WaveNet [36]).»
- [App. C.2] «For the baselines, we report their performance as presented in [19].»
- [App. C.2] «To aggregate across datasets, we normalized the mean absolute error by the MAE achieved by simply predicting the last observed value before the test series (a naive baseline).»
- [App. C.2] «The normalized MAE values shown in Figure 4 (center) are obtained by normalizing by the lowest baseline MAE on each dataset before aggregating.»
--- ARM: Informer benchmark comparison methods ---
- [Sec. 4, Datasets] «Informer [55]: We evaluated on multivariate datasets widely used for benchmarking efficient transformer models [16, 55]. […] We baseline against numbers obtained by running public implementations from the Autoformer [50] and FEDFormer [56] codebases (Appendix C.3).»
- [App. C.3] «we use a smaller evaluation set for each dataset, taking the last 96 or 192 timesteps of each series within each dataset as the test set.»

=== SYSTEM S19 | TimeRSI | arXiv 2610.19725v2 ===
--- ARM: TimeRSI (code agent with iterative search) ---
- [Problem description] «Agents can use task and variable descriptions, timestamps, observed values, and available covariates.»
- [Formalisation] «let m describe the task, variable meanings, and sampling frequency»
- [Figure 3 caption] «The agent adds calendar features for parking, separates tidal patterns for ocean currents, applies holiday rules for supply-chain demand»
- [Limitations] «TimeRSI relies on clear task and variable descriptions to connect numerical patterns with domain knowledge.»
--- ARM: Direct inference ---
- [Table 6 title] «Paired comparison with direct inference»
- [Figure 4 label] «Direct TimesFM 3.0»
--- ARM: Non-iterative search ---
- [Figure 4 section title] «Non-Iterative Search for Deployment»
--- ARM: Leaderboard rows ---
- [Tab. 5 and Tab. 8 row labels] «seasonal_naive»; «Seasonal Naive»; «Stat. Ensemble»

=== SYSTEM S20 | TimeCopilot | arXiv 2509.00616v3 ===
--- ARM: GIFT-Eval entry ---
- [Sec. 2.1] «computes focused diagnostics (trend, seasonality, stationarity) that directly inform model choice»
- [Sec. 2.2] «ADIDA, AutoARIMA, AutoETS, Theta, and SeasonalNaive [40]»
- [Sec. 3.1] «The TimeCopilot results rely on its MedianEnsemble feature […] used to combine three […] foundation models (Chronos-2 [35], TimesFM [12], and TiRex [39]) with an isotonic regression [50]»

=== SYSTEM S21 | Beyond Naive Prompting | arXiv 2508.09904v3 ===
--- ARM: Direct Prompt (DP) ---
- [Sec. 3.1] «The goal of context-aided forecasting is to produce statistical forecasts by incorporating relevant side information (i.e., context). […] We focus on the case where context is available in textual form.»
- [Sec. 3.2] «Direct Prompt (DP), a method that instructs an LLM to generate forecasts as structured output for all required timestamps, given historical data and textual context.»
- [Fig. 2 caption] «CiK comprises 2,644 time series across 7 real-world domains/datasets; it is designed to benchmark context-aided forecasting models, with tasks where the textual context is necessary for accurate forecasts.»
--- ARM: CorDP (Median-CorDP, SampleWise-CorDP) ---
- [Sec. 5.2] «The LLM receives probabilistic forecasts from a quantitative model and is instructed to correct them based on the textual context, modifying only the portions where the context provides relevant insights.»
- [Sec. 5.2] «Median-CorDP: The LLM corrects the median of the forecast distribution multiple times, generating a new context-informed distribution.» «SampleWise-CorDP: The LLM corrects each sample from the original probabilistic forecast, preserving the original distribution's structure.»
- [App. D.1, CorDP prompt] «My statistical forecasting model does not support taking in context as part of its input. I would like you to correct its forecasts to incorporate the context wherever necessary […]»
--- ARM: Base Quantitative Forecaster ---
- [Table 1 row label] «Base Quantitative Forecaster»
- [Table 1 entries] «Lag-Llama»; «Chronos Large»; «arima»
--- ARM: Without Context; With Context (DP) ---
- [App. B] «Results of various models with Direct Prompt (DP), with and without context are given in Table 3.»
- [App. B, Table 3 column labels] «Without Context»; «With Context»
--- ARM: RouteDP ---
- [Sec. 7] «We compare RouteDP against two baselines: random routing (assigning k random tasks to the large model) and ideal routing […].»

=== SYSTEM S22 | TSci | arXiv 2510.01538v2 ===
--- ARM: TSci (Curator, Planner, Forecaster) ---
- [Sec. 3.1] «given a univariate time series D, the system generates a comprehensive report R containing: statistics of the input data, visualizations, […] and the final forecasting result.»
- [Sec. 3.2] «Rather than computing fixed summaries, Curator leverages LLM-driven reasoning to both diagnose issues and execute appropriate preprocessing. Specifically, given a univariate series D={x_t}_{t=1}^{T}, the agent first outputs a vector Q containing data statistics S, missing value information M, outlier information O, and data-process strategy pi.»
- [Sec. 3.2, Figure 3 caption] «The raw dataset D is first diagnosed and processed into a cleaned dataset D-tilde. Next, the agent generates tailored visualizations V to expose temporal structures and facilitate interpretability. Finally, the agent integrates the processed data and visualizations to extract trends, seasonality, and stationarity, producing a comprehensive analysis summary S.»
- [Sec. 3.2] «Formally, given the processed dataset D-tilde and visualizations V, the agent generates an analysis report A through LLM reasoning: A={t,s,u}, where t,s,u denote trend, seasonality, and stationary, respectively.»
- [Sec. 3.3] «Planner extracts visual features from visualizations V via lightwise pattern recognition and LLM reasoning. It then maps the recognized data pattern to suitable model families and forms a candidate pool M_p, which has n_p candidate models from a pre-defined model library M»
- [Sec. 3.4] «Forecaster takes the top-k selected models M_selected and their validation metrics S_val as input. The agent leverages an LLM-guided policy to select an ensemble strategy from among three families: single–best selection, performance-aware averaging, or robust aggregation. The ensemble strategy and (if applicable) weights are fixed before touching the test set to avoid data leakage.»
- [Sec. 13, prompt for Curator] «You have access to: - The raw time series data (as a Python dict) - Any prior preprocessing history or known data issues»
- [App. 9.1] «The input time series length T for each slice is set as 512, and we use four different prediction horizons H in {96,192,336,720}.» «Due to a limited budget, we divided all datasets into 25 slices and conducted experiments on these slices instead of the entire dataset.»
--- ARM: Comparison methods (LLM-based baselines; statistical baselines) ---
- [Sec. 4] «To ensure fairness, we strictly follow the same evaluation protocols for all baselines.»
- [App. 9.3] «We benchmark TSci against several […] large language models, including GPT-4o, Gemini-2.5 Flash (Gemini Team, Google, 2025), Qwen-Plus (Cloud, 2025a), DeepSeek-v3 (Liu et al., 2024), and Claude-3.7 (Cloud, 2025b).»
- [Table 1 caption] «Time Series forecasting results compared with five LLM-based baselines.»
- [Figure 6 caption] «Performance comparison of TSci with statistical baselines on ETT-small benchmarks.»
- [Figure 11 caption] «Performance comparison of TSci with three statistical baselines across eight datasets.»
--- ARM: Ablation variants (Figure 7) ---
- [Figure 7 caption] «Ablation study of TSci with three variants: w/o Data Pre-process, w/o Data Analysis, and w/o Parameter Optimization.»

=== SYSTEM S23 | TimEvolve | arXiv 2609.24862v1 ===
--- ARM: TimEvolve (orchestration policy over numerical experts) ---
- [Sec. 3] «the history x_{1:t} and time-aligned context c_t are available»
- [Sec. 3] «c_t supplies reports and search evidence available by t ... contextual evidence informs expert selection and local corrections»
- [Table 2 description] «The language model, numerical forecasters, analytical tools, and prompts remain frozen while the orchestration policy evolves.»
--- ARM: Variants (Table 2) ---
- [Table 2 row labels] «w/o EvolveTrust»; «w/o EvolveReason»; «w/o EvolveIntervene»; «TimEvolve-Stack»
- [Table 2 description] «the forward computation»
--- ARM: Comparison methods (Table 1, Time-MMD domains) ---
- [Table 1 row labels] «Aurora»; «TimesFM-3»; «Chronos-2»; «Toto-2.0 (313M)»; «Sundial»; «Moirai-Large»; «PatchTST»; «T3Time»; «TimeCMA»; «CALF»; «CastFlow»; «MemCast»; «KairosAgent»
- [Table 1 category label] «full-shot multimodal»
- [Table 1 row labels, domains] «Agriculture»; «Climate»; «Economy»; «Energy»; «Environment»; «Security»; «Social Good»; «Traffic»
