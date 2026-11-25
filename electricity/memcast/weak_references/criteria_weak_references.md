# Criteria for the weak references on MemCast (written before the run)

These criteria were written before the weak references were computed. The reading below was fixed for the run in `memcast_controls_v2.py`; the other two window layouts are sensitivity analyses.

**Main protocol.** `spread96`: 30 test windows spread over the whole test segment (stride 96 h). `spread48` (stride 48 h) is a sensitivity analysis. `code24` (30 consecutive days, as in MemCast's public code) is used only to check that version 2 reproduces the first version of the script.

**Validity check.** In a market, if the seasonal naive of the previous day (`SN-1d`) has an MSE that differs by more than a factor of 3 from the paper's best non-LLM baseline under the main protocol, the reconstruction is taken not to cover the same period as the paper, and the market is removed from the reading and reported separately. (Under the main protocol, `SN-1d` was computed beforehand with a separate script: NP 43, PJM 40, BE 558, FR 783, DE 448, against the paper's best non-LLM baselines 55.9, 63.3, 887, 876, 291; all five markets are within a factor of 3.)

**Reading.** In every market the MSE is compared; "the paper's best non-LLM baseline" is taken from Table 2 of MemCast.

| Id | Comparison | Reading | Written before the run |
|---|---|---|---|
| R1 | SameInfo against the paper's best non-LLM baseline | At least 4 markets with SameInfo better: the paper's baselines are weaker than a standard linear electricity-price model with the same information, so the comparison was not made under the same information | yes |
| R2 | SameInfo against MemCast | At least 3 markets with SameInfo <= MemCast: the advantage of MemCast on electricity prices is also obtained without an LLM. At least 4 markets with MemCast better by 10% or more: MemCast has an increment over the same-information control, reported as a counter-example | yes |
| R3 | R-3 (mean of the three retrieved windows) against MemCast | At least 3 markets with R-3 <= MemCast: retrieval alone suffices | yes |
| D1 | SN-1d against the paper's baselines and MemCast | Descriptive. The numbers had been seen before this item was written, so it is not a criterion fixed in advance | no |

**Wording limit.** The electricity-price data and the per-window outputs of MemCast are not public. The result can therefore only be described as holding "on reconstructed windows with an error scale consistent with the paper", and the comparison is between summary numbers without a paired test.