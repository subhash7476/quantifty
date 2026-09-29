# M1c Research Protocol v1 — Hostile Scientific Review

**Date:** 2026-09-29 · **Reviewed:** `docs/reports/strategies/M1C_RESEARCH_PROTOCOL_v1.md` (commit `d0dfb30`) against MAP v1.1.
**Scope:** protocol audit only. No data read, no run, no code, no new hypotheses, no parameter changes. Nothing here says whether M1c is promising.

**Reviewability caveat.** The committed protocol file is **truncated**: it ends mid-sentence in §9 (line 173, "If no combination clears the descript") followed by the literal string `...[truncated 6154 chars]`. §9's fallback rule, §9.1 (MRLC-overlap diagnostic), §10 (test), §11–§13 (evidence/failure criteria), §14 and §15 (open items, incl. §15.1, §15.8) are absent. Audit items 3 (part), 12 and 13 (part) cannot be completed.

## Dimension verdicts

| # | Dimension | Verdict |
|---|---|---|
| 1 | Hidden DoF / multiple testing | MATERIAL (M4, M5, M6, M8); multiplicity itself controlled (N1) |
| 2 | TRAIN/VAL/HOLDOUT leakage | BLOCKER (B2) + MINOR (m3) |
| 3 | Pinning makes VAL confirmatory | NO ISSUE on leakage (N1); MATERIAL on rule ambiguity (M6); fallback unseen (B1) |
| 4 | F1/F2/F3 distinct? | MATERIAL definitions (M4); wording MINOR (m5) |
| 5 | 5 / 252 / 5-95% / H defensible | NO ISSUE on values (N4); MATERIAL on prior exposure (M7) |
| 6 | Universe / PIT / survivorship | MATERIAL (M1, M8) |
| 7 | CA and calendar | NO ISSUE on basis (N5); MATERIAL on judgement drops (M8) |
| 8 | Forward timing / gap | NO ISSUE (N2); MINOR residue (m1) |
| 9 | Overlap / dependence / NW | NO ISSUE on lag (N3); MATERIAL on session definition (M5) |
| 10 | Isolation from M2c/M3b/M5b | M2c, M5b NO ISSUE (N6); M3b MATERIAL (M3); M1a/market MATERIAL (M2) |
| 11 | Implementation ambiguity | MATERIAL (M4, M5, M6, M8) |
| 12 | Evidence/failure criteria coherent | NOT ASSESSABLE (B1) |
| 13 | Post-hoc decision points | BLOCKER (B2), MATERIAL (M6, M8) |

## A. BLOCKERS

**B1 — Protocol text is truncated.** See caveat above. A frozen protocol must contain its test, α, sidedness, pass/fail and holdout rules; none are visible. *Fix:* restore the full text from source and re-submit for review. Findings on §9.1–§15 are outstanding until then.

**B2 — HOLDOUT is undecided (§9 table, §15.1).** Choosing the holdout window/mechanism after VAL is run is a post-hoc decision point, and the 2023+ window is sealed-era and already MRLC-read (MAP §2.1). *Fix:* before freeze, name the holdout (dates or forward-accumulation start date plus minimum session count) and state that it is not touched until VAL has run as pinned.

## B. MATERIAL CORRECTIONS

**M1 — Universe is self-contradictory (§3).** "PIT F&O equity membership" is ~200 names; the "~2,300 PIT symbols" MRLC panel is all-NSE equity. Every downstream number depends on this. Equal-weight aggregation over 2,300 names is small/illiquid-name-dominated, and no liquidity statement is made. *Fix:* pick one universe, delete the other phrase, and state that no liquidity filter is applied (or pin one).

**M2 — H0 is not the no-signal null (§1, §6).** Under no predictability the session-portfolio mean is E[s]·μ + cov(s, market forward return); E[s]≈0 by percentile construction, but the covariance term is market-level reversal, and tail events cluster on market-wide days. A positive result cannot be attributed to single-instrument exhaustion. *Fix:* pin either (i) forward return net of the same-window equal-weighted universe return, or (ii) raw f with an explicit statement that the estimand includes market-level reversal. Event definition unchanged either way.

**M3 — M3b isolation is contradictory (§2 vs §4).** §2 says any level event voids the interpretation; §4 says "no other condition". A ≤5th-percentile 5-session return will very likely close below the prior 10-session low, so M3b breach content is near-implied by the down-tail; exclusion would gut the event set. *Fix:* delete the "voids" sentence; state that overlap with MRLC-type breach is admitted and quantified report-only (§9.1), with no effect on pinning or pass/fail. (§9.1 is not visible — confirm it agrees.)

**M4 — Measurement ambiguities that are researcher judgement.**
- Percentile convention: is R5(t) inside its own 252-value reference set; inclusive/exclusive rank; ties; interpolation.
- Lookback completeness: §3 says 252 closes, but F1 needs ≥257, F2 ≥320 (252 + 63 + 5), so eligibility differs by family.
- F2: does σ(t) include the 5 sessions in R5(t); is the reference series R5/σ computed with each date's own σ.
- F3: "same 5%/95% tail rule" is false as written — F3 is one-sided at 95th of |R5|/median (≈5% of name-sessions vs ≈10% for F1/F2); and whether the ratio's trailing distribution uses historical ratios (each with its own median) or today's median.
*Fix:* one sentence each; declare eligibility as the max lookback across families.

**M5 — "Session observation" is ambiguous (§8.1).** Either (a) cohort series indexed by formation date (mean f over formations formed at τ) or (b) calendar-time series of concurrent stacked positions. They differ in variance and MA structure. Also unspecified: empty sessions, weighting across cohort sizes. *Fix:* pin (a) or (b); NW lag = H is right for (a).

**M6 — Pinning rule is under-specified (§9, §6).** (i) If the largest-|t| combination has the wrong sign, does the rule take the largest right-sign one or pin nothing? (ii) Ties. (iii) §6 "proposed default H = 5" conflicts with "rule only". (iv) The §9 table has TRAIN "confirm power feasibility": RFA is a data-free gate, and a selected-max TRAIN estimate is winner's-curse inflated (the C2 / CB-N50 lesson). *Fix:* "among right-sign combinations, largest |t|; none → STOP; ties → smaller H then F1<F2<F3"; delete the default-H sentence; replace TRAIN power check with "power is assessed only via the frozen RFA declaration".

**M7 — Prior exposure undisclosed in visible text.** 2012–22 daily on the 2,300-name panel was read by MRLC (25-day stretch construct, MAP §4 M3b), and PSB-1 C1/C2 (weekly reversal) and RELIANCE `reversal_5` used overlapping 2012–22 data. VAL 2018–22 is therefore not naive to this construct family, and N=5 "by precedent" was chosen with that knowledge. *Fix:* add a prior-exposure clause (PSB-2 D2 style) and state that a VAL pass is a consistency check whose confirmatory weight is carried by HOLDOUT (after B2).

**M8 — Missing-data and judgement drops (§3).** No rule for delisting/suspension inside a forward window (dropping those formations is survivorship in the crash-prone direction); entity bar-count vs calendar-session for "5 sessions"; "unresolvable adjustment status" is a judgement call. *Fix:* mechanical rules (delisting → last available close as terminal price; missing bar → formation dropped by rule; CA status from the committed disposition register only).

## C. MINOR CLARIFICATIONS

- **m1** §6 contains a garbled residue `f = s·(C(t+1+H)/C(t+2 open…))` before the correct formula; delete it.
- **m2** H1 (§1) is written for F1/H=5; state it applies to the pinned combination.
- **m3** Purge at boundaries: TRAIN formations in the last H+1 sessions of 2017 and VAL formations in the last H+1 of 2022 have forward windows in the next stage, contradicting "no information flows backward". Restrict formations to windows ending inside their stage.
- **m4** "Residual autocorrelation reported, not patched" means PASS rests on the lag-H test alone; say so.
- **m5** F1/F2/F3 are heavily overlapping event sets, not independent lenses; a VAL pass supports only the pinned family, not "M1c" in general.

## D. NO ISSUES

- **N1 Multiplicity / VAL confirmatory.** Selection uses TRAIN only via a mechanical rule; VAL is a single pinned test, so the 9-combination search never enters VAL inference. Overlap among F1–F3 only reduces the effective number of TRAIN shots.
- **N2 Timing.** Window t+2..t+1+H with base C(t+1) is internally consistent; the gap session is never in the return; signal and return are never same-day.
- **N3 NW lag = H.** Covers the MA(H−1) overlap from H-session windows; cross-sectional dependence is removed by session aggregation.
- **N4 Parameter values.** N=5, W=252, 5/95%, H∈{1,5,10} are fixed conventions, none searched inside the protocol; H is chosen by a TRAIN-only rule.
- **N5 CA basis / calendar.** Certified adjusted view, no mixed 1m/bhavcopy join, calendar from `trading_calendar`, 2012-11-11 excluded, entity intervals with ISIN-prefix linkage.
- **N6 M2c / M5b isolation.** Opposite predicted sign (continuation counts as null); volume never read.

## E. FREEZE RECOMMENDATION

**DO NOT FREEZE.** Restore the truncated §9–§15 (B1) and pin the holdout (B2); then apply M1–M8. All are targeted text corrections; no redesign is needed. Re-review §9.1–§15 once restored.
