# SE-3 — Corporate-Action Contamination Finding: Lead Review

**Date:** 2026-08-06
**Reviewer:** Claude (lead review role, per the standing DeepSeek-implements / Claude-reviews split)
**Subject:** DeepSeek's 2026-08-06 finding that the SE-3 substrate carries unadjusted
split/bonus corporate actions in the FUTSTK settle series
**Verdict:** **Finding CONFIRMED as a real defect. Verdict NOT moved — SE-3 stays NO-BUILD.
Do NOT reopen the frozen Phase 2 one-shot.**

---

## 1. What was verified, independently

The finding was not accepted on assertion. Two independent checks were run.

### 1.1 Mechanism — confirmed in code

`scripts/se3/certify_substrate.py:337`:

```python
fdf.loc[fdf["expiry_dt"] != fdf["prev_exp"], "ret"] = np.nan   # the §3.5 guard
```

The roll-gap guard nulls a front-month log return **only** when the selected front-month
`expiry_dt` changes between consecutive dates. A split or bonus does not change the front-month
contract, so the ex-date log return survives into `fdf["ret"]` and thence into the 21-day
rolling RV at line 338. DeepSeek's mechanism claim is exactly right, and the probe's original
rationale — "the futures settle needs no corporate-action adjustment" — is false for this window.

### 1.2 Data — confirmed, and the finding is broader than reported

An independent scan (not DeepSeek's list) reconstructed the front-month series for **every**
FUTSTK underlying over `2016-02-11 → 2022-12-31`, applied the §3.5 guard verbatim, and reported
every surviving one-day |log return| > 0.35.

**98 events survive the guard.** All 17 of DeepSeek's confirmed Nifty-50 splits reproduce, at the
ratios claimed:

| Name | Ex-date | prev → settle | ratio |
|---|---|---|---|
| JSWSTEEL | 2017-01-04 | 1649.65 → 163.15 | 0.0989 |
| BAJFINANCE | 2016-09-08 | 11423.45 → 1164.65 | 0.1020 |
| BAJAJFINSV | 2022-09-13 | 17214.75 → 1751.45 | 0.1017 |
| EICHERMOT | 2020-08-24 | 21809.40 → 2187.75 | 0.1003 |
| TATASTEEL | 2022-07-28 | 962.55 → 100.60 | 0.1045 |
| BEL | 2017-03-16 | 1574.50 → 165.30 | 0.1050 |
| GRASIM | 2016-10-06 | 4961.30 → 1010.65 | 0.2037 |
| RELIANCE | 2017-09-07 | 1646.95 → 821.25 | 0.4986 |
| TCS | 2018-05-31 | 3497.20 → 1752.25 | 0.5010 |
| INFY | 2018-09-04 | 1439.45 → 738.45 | 0.5130 |
| HDFCBANK | 2019-09-19 | 2189.60 → 1100.80 | 0.5027 |
| HCLTECH | 2019-12-05 | 1128.00 → 563.10 | 0.4992 |
| WIPRO | 2017-06-13 | 524.45 → 258.70 | 0.4933 |
| BPCL | 2016-07-13 | 1115.95 → 546.70 | 0.4899 |
| IOC | 2016-10-18 / 2018-03-15 | 641.70 → 321.95 / 390.85 → 192.40 | 0.5017 / 0.4923 |
| M&M | 2017-12-21 | 1542.80 → 745.45 | 0.4832 |
| BRITANNIA | 2018-11-29 | 5986.05 → 3027.50 | 0.5058 |

*(RELIANCE's prev settle is 1646.95 in my reconstruction, matching DeepSeek exactly; TATASTEEL's
is 962.55 vs the 958.15 reported — a front-month selection difference, immaterial.)*

**Two things the original finding did not say:**

- The defect is **not confined to the 17 Nifty-50 names**. 98 events survive universe-wide
  (AARTIIND, SRF, IRCTC, IGL, MCDOWELL-N, CHOLAFIN, CANFINHOME, SINTEX, TATAELXSI, …). SE-3 only
  consumes Nifty-50 PIT members, so its exposure is the 17 — but **any future construct over the
  wider SSF universe inherits a materially larger version of this defect.** That is the more
  valuable half of the finding.
- The scan also catches **genuine** collapses (YESBANK 2020-03, JETAIRWAYS 2019, RCOM, IDEA,
  DHFL). A repair keyed on "large move" would destroy real data. The repair must be keyed on a
  **corporate-action register**, not on a return threshold.

---

## 2. Where the finding overreaches

Points 1, 2 and 3 of the original finding (RV corruption, richness distortion, delta-hedged
return corruption across an ex-date) are **valid and correctly reasoned**.

**Point 4 is wrong and should be dropped.** The claim is that a flat Rs 80/name-day cost converts
to different vega-unit fractions pre- and post-split, "mixing scales in one cross-section."

Vega scales with the price level. On any given cross-section date, every name sits at its **true
contemporaneous** price — RELIANCE at 1646.95 on 2017-09-06 and at 821.25 on 2017-09-07 are both
correct, because the bonus really did happen. The RELIANCE-vs-ITC vega-unit difference cited as
evidence exists between any high- and low-priced pair with or without a split, and is ordinary
cross-sectional heterogeneity, not contamination. Nothing in the D1 cost stack is distorted by
corporate actions. Retaining this point would weaken an otherwise sound finding.

---

## 3. Why the verdict does not move

The NO-BUILD did not rest on the IC magnitude. Its structure is:

- **G1/G2 (the gating criteria) PASSED** — mean_IC −0.1124, NW(5) t = **−21.52**, n = 1,680.
- **NO-BUILD came from D1**, which is explicitly non-gating: net is negative **at every rung
  including 0 bp**, because gross (6.8166 vega-scaled units, identical at every rung) is exceeded
  by statutory + futures-leg costs alone.

Contamination measured at **378 RV-contaminated name-days out of ~85,000 (0.44%)** and **72
dh-contaminated name-days**. Neither gate is reachable:

**On G1/G2.** Take a deliberately absurd upper bound: assume every contaminated name-day displaces
that name maximally within its daily cross-section. A single fully displaced observation in a
Spearman ρ over n≈30 moves that date's IC by at most ≈0.19. The 17 splits × 21-day RV windows
touch at most ~357 distinct dates of 1,680. Ceiling on the mean_IC contribution:
`(357/1680) × 0.19 ≈ 0.040`. Even at that ceiling — which requires every displacement to be
maximal *and* perfectly sign-aligned, neither of which is plausible — the point estimate stays
around −0.07 and t stays past −14. **Sign and significance survive by a wide margin.**

**On D1.** For contamination to rescue D1, removing 0.44% of name-days would have to multiply
gross P&L by enough to clear a cost stack that already beats it at zero assumed spread. It cannot.

**Conclusion:** the defect is real, and it is **not verdict-bearing**.

---

## 4. What the defect *does* damage

The **precision of the point estimate**, not the finding.

`mean_IC = −0.1124` should no longer be quoted to four decimals as if it were clean. The honest
statement after this finding is: *a large, unambiguously significant negative IC, whose point
estimate carries an unquantified but bounded (≤ ~0.04) corporate-action bias.* That is enough for
"IC finding stands"; it is not enough for anyone to anchor a future δ band on −0.1124.

This matters because the confirmatory review already flagged the IC magnitude as suspicious for an
unrelated reason (it looks like IV mean reversion rather than a risk premium). Both caveats point
the same way: **the SE-3 IC is a real phenomenon and a bad anchor.**

---

## 5. Governance — do NOT reopen the one-shot

The original finding proposes re-running Phase 1 → Phase 2 on an adjusted panel under operator
authorization. **I recommend against it, firmly.**

Phase 2 is pre-registered as *"one shot, never re-run"* (`SE3_PRE_REGISTRATION.md`, Phase 2
heading). Reopening it now would mean re-executing a frozen confirmatory read **after seeing its
result**, on a defect that has been shown above to be incapable of changing either gate. That is
structurally the same error that de-authorized TS Basis — a gate re-touched after the outcome was
known — and it would convert a clean NO-BUILD into a contaminated one. The repo has paid for this
lesson twice already.

The asymmetry is decisive: reopening cannot change the verdict, but it can destroy the verdict's
provenance.

**Correct disposition:** annotate, don't re-run. The frozen snapshot stays frozen; this review
becomes the disclosure attached to it.

---

## 6. Recommended actions

| # | Action | Who | Status |
|---|---|---|---|
| 1 | Land this review as the authoritative record; supersede the proposed `SE3_CA_CONTAMINATION_FINDING.md` (its point 4 is wrong) | Claude | this file |
| 2 | Annotate `SE3_CONFIRMATORY_REPORT.md` + `CLAUDE.md` SE-3 row: IC point estimate carries a bounded CA bias; verdict unchanged | DeepSeek | **authorized** |
| 3 | **Fix the guard in `certify_substrate.py`** — drop (or ratio-adjust) front-month returns spanning a CA ex-date, keyed on a corporate-action register, never on a return threshold | DeepSeek | **authorized** |
| 4 | Build the CA factor map for FUTSTK/OPTSTK, reusing `ingest_corporate_actions.py` + `symbol_entity_intervals` | DeepSeek | **authorized** |
| 5 | Re-run Phase 1 / Phase 2 on the adjusted panel | — | **NOT authorized** (§5) |
| 6 | Check the 2023–2025 probe window for splits | DeepSeek | authorized, **low priority** — contamination *inflates* dispersion, so a contaminated probe `sd_IC` 0.1877 is conservative, and the confirmatory's measured 0.1940 landed in-band anyway. This cannot have made the band too generous |

**Items 3 and 4 are the real value of this finding.** SE-3 is closed either way; what the fix buys
is that the *next* construct over the SSF universe — where 98 events, not 17, are in scope — does
not silently inherit fabricated 10× volatility spikes.

---

## 7. Standing lesson (for `CLAUDE.md` Known Pitfalls)

**A guard keyed on the contract identifier cannot catch a defect in the contract's price scale.**
The §3.5 roll-gap guard drops returns when `expiry_dt` changes — which is correct for rolls and
blind to splits, because a split changes the *price basis* while leaving the *contract identity*
untouched. Raw bhavcopy futures settles are un-adjusted; any volatility, return, or z-score
computed off them must be corporate-action-adjusted first. The equity side of this repo already
learned it (`equity_bhavcopy_adjusted`, the four-arm contract suite); **the futures side never
had the equivalent, and nothing surfaced the gap because the roll guard looked like it covered it.**

---

## 8. Remediation verification (2026-08-06, post-implementation)

Tasks 1–5 were implemented and reported complete. **Verified independently, not accepted on
assertion** — the three predictions were re-run through the *shipped* `_front_month_rv` and
`_load_ca_register` (not the implementer's harness), against the full FUTSTK universe.

| Prediction | Claimed | Independently reproduced | |
|---|---|---|---|
| P1 — Nifty-50 splits still surviving | 0 | **0** | PASS |
| P2 — genuine collapses preserved | 13/13 | **13/13** | PASS |
| P3 — residual event count | 33 | **33** | PASS |

Register loads 940 symbols / 1,304 ex-dates. `tests/se3/` **47/47 pass**. The guard fix is sound:
the register is the authority (never the price jump), the drop idiom matches the roll-gap
convention, and the `ca_ex_dates=None` default preserves the pre-fix path — which is what makes
the "no register entry → fabricated return preserved" test meaningful rather than vacuous.

**One correction to the completion report.** P3's residuals are described as "all genuine." They
are not. Roughly seven are **unregistered demergers**, not genuine moves:

| Name | Ex-date | ratio |
|---|---|---|
| CROMPGREAV | 2016-03-15 | 0.2827 |
| SINTEX | 2017-05-25 | 0.2502 |
| ARVIND | 2018-11-28 | 0.3496 |
| KPIT | 2019-01-24 | 0.5959 |
| CENTURYTEX | 2019-10-11 | 0.4469 |
| TATACHEM | 2020-03-04 | 0.4365 |
| PEL | 2022-08-30 | 0.5563 |

This contradicts the completion report's own §7, which correctly lists "demergers absent from the
equity register" as un-remediated — so the gap is disclosed, but the P3 sentence overstates the
result and should read *~26 genuine + ~7 unregistered demergers*.

**Consequence, checked rather than assumed:** PIT MCWB membership was resolved for all nine
suspected residuals at their ex-dates — **none was a Nifty-50 member**. SE-3's own panel therefore
carries no contamination beyond the bounded 17, and the ≤0.040 ceiling in §3 stands unchanged.
The demerger gap is live only for a future SSF-universe construct — which is precisely the
population items 3 and 4 were authorized to protect. It should be closed before that construct
runs, not now.

**One MEDIUM observation, recorded not fixed.** `_load_ca_register` resolves the entity
time-awarely on the *source* side (`_entity(sym, ex)`) but then broadcasts the ex-date onto every
symbol the entity has *ever* traded as, without an interval check on the target. Where NSE has
recycled a ticker across entities (the DTIL/DVL pitfall), this can drop a return on a date when
that symbol belonged to a different entity. The direction is conservative — losing 1 observation
of a 21-day window is strictly preferable to admitting a fabricated 10× volatility spike — so no
fix is required, but it should not stay silent.

**Verdict: remediation ACCEPTED.** SE-3 stays NO-BUILD, the frozen Phase 2 snapshot was correctly
left untouched, and the substrate defect is closed for the Nifty-50 panel.
