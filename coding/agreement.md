# Re-annotation agreement

This file documents the model-based re-annotation of information tiers (2026-11-15), the agreement with the reference labels, and the adjudication of disagreements.

**Procedure.** The codebook (`coding/codebook.md`) was written first, then the reference labels. The codebook was developed post hoc, after results were known.
- Input builder: extracted verbatim English input descriptions only, with result values and evaluative statements removed (outcome-redacted excerpts).
- Annotator: a separate model instance with fresh context. It read only the codebook and the redacted input. It did not see the reference labels, results, or earlier discussions.
- Type of annotation: an independent model-based re-annotation from outcome-redacted input excerpts, with a codebook developed post hoc. No human annotation or blind double annotation was performed.

**System level (highest tier over main-evaluation arms), 22 systems with a reference label** (Informed Forecasting had none):

| reference \ re-annotation | S | M | N |
|---|---|---|---|
| S | 12 | 0 | 0 |
| M | 1 | 7 | 0 |
| N | 0 | 1 | 1 |

- Exact agreement: 20/22. S vs non-S: 21/22.
- 50 of 89 arms were flagged AMBIGUOUS by the annotator. Most flags concern MATCH (what the comparison receives is often stated only as a table label).

**Disagreements and adjudication** (final labels are listed separately; the matrix above compares against the reference labels, not the adjudicated labels):
1. **MoiraiAgent**: reference M, re-annotation S. This is aggregation, not disagreement. At arm level, the GIFT-Eval selection arm (the arm behind the 1.3% increment record) is M in both. The S comes from the GIFT-CTX context-forecasting arm, which has no no-LLM comparison. Final: GIFT-Eval arm M; GIFT-CTX arm S (no comparison). Lesson: report the tier per arm wherever an increment record is attached.
2. **FLAIRR-TS**: reference N, re-annotation M (low confidence). The codebook assigns error records on past windows and numeric-history-derived outputs to M. The method feeds retrieved segments with their outcomes and error feedback. Final: **M** (the re-annotation is adopted, as it is the literal codebook reading). The annotator also flagged that "recent ground truth X_{t:t+H}" in Algorithm 1 could be the evaluated horizon, while App. F.3 says validation samples. This stays an open question, and leakage is not asserted.
3. **Informed Forecasting** (no reference label): re-annotation M (low confidence). The covariates are calendar-derived (date, month, weekday), which are timestamps, so M under the codebook. Final: M.
