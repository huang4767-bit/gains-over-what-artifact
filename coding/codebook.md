# Codebook for information tier and match

This file documents the codebook used to label what the LLM component of each system receives and whether the no-LLM comparison receives the same information.

Written 2026-11-15, before the re-annotation. Status: the codebook was developed post hoc, after the authors had seen results. It was fixed before the re-annotation input was built and was not edited after the re-annotation started.

## Unit
One **setting** of one system: a (system, evaluation arm or dataset group) whose inputs are described in the excerpt. If a paper describes several arms with different inputs (for example, with and without context), each arm is labelled separately.

## Dimension 1: TIER (what the LLM component receives beyond the numeric history of the target)
- **S (substantive)**: information about the forecast target or its drivers that is not recoverable from the numeric history of the target. Examples: news or event text; event or holiday calendars, or holiday rules applied to the target dates; key free-text context written for the task; covariates over the forecast horizon (future-known or realised); last-year actual values injected as an override; retrieved external evidence (documents, reports, search results).
- **M (metadata only)**: dataset name, domain, variable names or descriptions, units, sampling frequency, seasonal period, timestamps or window dates, generic domain knowledge that is not specific to the target dates, and outputs of statistical tools computed only from the numeric history (including error or ranking records of tools on past windows).
- **N (none)**: only the numeric history of the target (possibly serialised as text).
- If an arm receives items from several tiers, the label is the highest tier present (S > M > N).

## Dimension 2: MATCH (does the no-LLM comparison in that arm receive the same Tier-S information?)
- **matched**: the comparison receives all Tier-S items the LLM receives.
- **partly**: the comparison receives some of them (state which are missing).
- **not matched**: the comparison receives none of them.
- **unclear**: the excerpt does not say what the comparison receives.
- **no comparison**: the excerpt describes no no-LLM comparison for that arm.
- **n/a**: the tier is M or N (MATCH is defined only for Tier S).

## Output per arm
System id, arm, TIER, MATCH, the verbatim quote(s) the decision rests on, confidence (high/medium/low), and an AMBIGUOUS flag with one sentence if the codebook does not decide the case.
