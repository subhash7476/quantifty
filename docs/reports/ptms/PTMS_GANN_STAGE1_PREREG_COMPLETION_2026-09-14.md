# PTMS — Gann Stage-1 Pre-Registration Completion Memo

**Date:** 2026-09-14 · **Branch:** `research/ptms-price-time-market-structure`

**Status:** PRE-REGISTRATION DESIGN COMPLETION. **Recommendations for operator ruling. Nothing frozen.**

**Operator rulings applied (2026-09-15):** R-1 → R-11 and R-13 accepted; R-14 accepted for
finalization only; R-12 accepted in principle only; R-15 open (Stage 2). The rulings of record are
`PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`; freeze status is
`PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md` (**NOT READY TO FREEZE**). Stage-1 primary set:
GF-1, GF-4T/R8, GF-10 (m = 3). The body below is preserved as written; where it says "recommend" or
"pending", read the ruling register. Accepted rulings are not a freeze.
- No market data, historical outcome or signal incidence was read. No backtest, TRAIN/HOLDOUT read,
  parameter fit, threshold tuning or RFA declaration.
- Power figures are arithmetic (`scripts/research/ptms_gann/gf_power_sketch.py`, `gf_screen_power.py`).
- Calendar checks in §1 are arithmetic on dates **printed in Gann's book**, not on market data.
- The feasibility screen was **not** run.

**Authority and inputs:**
- `PTMS_GANN_PREREG_DESIGN_DECISIONS_2026-09-14.md` (authoritative current state; commits `cb7886e`, `1247b8c`).
- `PTMS_GANN_PRIMARY_SOURCE_CLAIM_REGISTER_2026-09-14.md` §§26–27, and **§28 (Δ3, this commit)**.
- `PTMS_GANN_FAITHFUL_CONSTRUCT_DEFINITION_2026-09-14.md` §§0–12.
- `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` (§§4–6, 9 / GR-1).
- `PTMS_N100_EOD_FEASIBILITY_AUDIT_2026-09-14.md` §§K–L.

**Where this memo conflicts with the design-decisions document, this memo is the recommendation of
record — but no conflict is a ruling until the operator accepts it.**

**Source key:** [45Y] *45 Years in Wall Street*, 1949, reprint scan SHA-256
`183ed23850c7056f47e7242f6fc0264b294ecf19e87fdca303fe3137064e70dc`. [MMPTC] 1953 Calculator.
Page numbers are printed page numbers. Quotations are short.

---

## Summary

| Step | Result |
|---|---|
| 1. Finish [45Y] | **Done.** Every printed page 1–148 has now been viewed. Six findings change Stage-1 design (§1.2) |
| 2. Source-to-mechanization | §2. **Most Stage-1 slots are implementation assumptions, not Gann rules** |
| 3. GF-10 | **Evidence sufficient for the rule: recommend GF-10 = GANN-FAITHFUL**, superseding ruling 7. Its mechanization inherits the K3 ruling |
| 4. GF-8 / GF-9 | Both are genuine Gann claims. **Both excluded from Stage 1**: GF-8's anchor conflicts between rule text and every worked example; GF-9's population is hand-selected with overlapping bins |
| 5. K3 | **Not reproducible as Gann's detector.** Gann's own published 3-Day record departs from the strict rule in 7 of 61 swings (1912–14). Strict K3 is at best a declared approximation |
| 6. Construct set | **Recommend three primaries: GF-1, GF-4T/R8, GF-10.** GF-7 excluded (section scale undefined); GF-5, GF-6 deferred as under-powered; GF-8, GF-9 excluded; GF-2 and Stage 2 unchanged |
| 7. Primary cells | §7. Every cell carries at least one assumption another researcher could choose differently; three are unresolvable from primary text and go to the operator |
| 8. Surrogate IC | **Revise.** Per-date differencing is ill-defined under a date-resampling surrogate. Replace with a Monte Carlo rank test on the time-averaged IC, a synchronized bar bootstrap, and an intersection-union conjunction with a placebo test |
| 9. Power / RFA | **Accept "no RFA now"**, for three reasons besides power. **Correct** the earlier wording: GF-5/6/8 are under-powered under stated assumptions, **not** permanently infeasible |
| 10. Screen | **Admissible only if confined to 2011-03-25 → 2022-12-30.** The earlier proposal reached 2026-09-11 and would have spent the one span whose freshness is unresolved |
| 11. Memo | §11 A–H |
| 12. Verdict | **NOT READY — unresolved operator rulings (§11.E)**. *2026-09-15: rulings made; freeze verdict NOT READY TO FREEZE (freeze checklist)* |

---

## 1. Remaining [45Y] pages — design-relevant findings only

### 1.1 Coverage

Viewed this pass: pp. 46–55, 60–81 (text and the 3-Day and 9-Point record tables), 84–99, 102–148.
pp. 100–101 were covered earlier. Chapters X–XVI (volume, utilities, air transport, individual
company notes, puts/calls, operators, liquidated stocks, war and depression commentary, 1950–53
outlook) and the chart plates pp. 134–146 contain **no construction text**. Findings with no bearing
on Stage 1 are not listed.

### 1.2 Findings

| # | Source | What Gann says | Changes a design decision? | Mechanizable? | Faithful / assumption |
|---|---|---|---|---|---|
| F1 | [45Y] p. 61 | Moves are recorded "in 3-day moves or more, except when extreme highs or lows are reached and we wish to catch a turn"; then "we sometimes use 1 and 2-day moves. All of these moves are based on calendar days" | **Yes** — confirms the 2-day exception is discretionary ("sometimes", "we wish") | Exception: **no** | Strict K3 omits a Gann practice → approximation |
| F2 | [45Y] pp. 66–67 record, 1912-09-30 → 1914-03-06 (62 extremes transcribed) | Published date of each recorded swing extreme | **Yes.** 7 of 61 consecutive recorded swings are **fewer than 3 Mon–Sat sessions** apart (e.g. 1913-01-18 Sat → 01-20 Mon: 1 session). Holidays ignored, so 7 is a lower bound. Whether each departure was "near an extreme" was **not** assessed | — | **Gann's own detector cannot be reproduced by the strict rule** |
| F3 | [45Y] pp. 61–62 | A broken 3-day bottom "indicates lower prices", but "all other rules must be applied" and the last low and last high "major swings are of greater importance". "Until the averages or an individual stock breaks out of the trading range, you must not consider that the main trend has changed" | **Yes** — the Rule 10 K3 signal is a *minor / temporary* change; a *main*-trend change needs a trading-range breakout, which is not defined | Minor: yes. Main: **no** ("trading range" undefined) | Outcome scale is an operator ruling |
| F4 | [45Y] pp. 64–65 | Example: "no lows were broken on the 3-Day Chart by 3 points until February 10, 1947" | Yes — a penetration threshold appears in practice, in **points** | Only under a translation ruling | Stage 2; Stage 1 uses any penetration (assumption) |
| F5 | [45Y] pp. 98, 124 | Level breaks judged on the **close** ("should they ever close below 160"; GM "breaks 51⅞ and closes below") | Partly — K3 text uses tops and bottoms (intraday); level rules use closes | Yes | Break basis for O-R10 is an assumption |
| F6 | [45Y] pp. 46, 48, 55 vs p. 11 | Worked examples cite Rule 8 as "60 to 67 days" (p. 46), "90 to 98 days" (p. 48), "60 to 72 days" (p. 55). **The printed Rule 8 list on p. 11 says 57–65 and 85–92.** p. 10 has no day-count list | **Yes — corrects register §27.4 item 2.** Gann does not supply one consistent tolerance; *w* is a declared choice again | Yes, once pinned | Printed list = rule text; wider windows = Gann's usage |
| F7 | [45Y] pp. 46–55 (48 printed date pairs with stated day counts; arithmetic) | Counts such as "121 days", "224 days", "154 days" | Confirms T = **calendar days**, start date excluded: 42 of 48 match the calendar difference exactly; the 6 misses are 2–6 days off or have an unstated start; none fits a session count better | Yes | Faithful |
| F8 | [45Y] p. 50; p. 54; p. 125 | "50 per cent of the highest selling price" = the **1937 bull top**; "25% of the highest selling price 213.36" = the **1946 top**; Electric Bond & Share "a 50% decline from the 1946 High" | **Yes — contradicts the GF-8 anchor** pinned on Rule 3's "any high level" (design doc §D.4) | Only if "campaign high" is defined; Gann does not define it | GF-8 anchor unresolved |
| F9 | [45Y] pp. 85–88 | "It is important to have a record of when extreme High and Low prices are reached **in each calendar year**"; "study the exact dates each month when Highs and Lows have been reached … Watch around these same dates" | Yes — a **second sense of "extreme"** (calendar-year extreme) and a date-level anniversary practice | Yes | Anchor sense is an operator ruling |
| F10 | [45Y] pp. 92–93 | Anniversary record anchored on the 1929 all-time high and the 1932 low ("lowest since 1897"), plus campaign extremes (Mar 1937, Mar 1938, Apr 1942, May 1946) | Yes — a **third sense** (all-time and campaign extremes) | Yes per sense | Three senses: all-time-to-date, calendar-year, campaign |
| F11 | [45Y] pp. 88–89 | Time-swing statistics: "The swings recorded are mostly the major swings when there was a rapid advance or a rapid decline"; bins 3–11, 11–21, 22–35, 36–45, 43–60, 61–95, 96–112, >112 days | **Yes — GF-9.** Population hand-selected; bins overlap (11; 43–45), so not a partition | **No** to Gann's standard | GF-9 not faithfully mechanizable |
| F12 | [45Y] p. 53 | 1946 decline "the sharpest reaction that had occurred since April 28, 1942, and was the First Warning" | Supports the p. 39 greatest-period reference as a live Gann alternative to "previous" | Yes | GF-10 comparison ambiguity is real |
| F13 | [45Y] p. 48; p. 51 | 1 point per day "as prices were low below $100.00 per share this was a normal market"; "a normal decline for the prices at which the Averages were selling" | Reinforces Stage-2 deferral: point rules depend on price level with no conversion | No | Stage 2 |
| F14 | [45Y] p. 84; pp. 96–97 | "Study the past time periods in connection with individual stocks"; "applying all of the rules to the individual stocks as well as to the Averages" | Supports per-stock construction | — | Faithful |
| F15 | [45Y] pp. 96–98 | Ten different percentage and range constructions from many anchors "prove" one level band ex post: "There is always a mathematical proof" | Yes — the percentage point set is dense and applied ex post; point-density hazard for any GF-8 revival | — | Coverage-matched null mandatory |
| F16 | [45Y] p. 123 | "(1946 High 31½ after stock dividend)" — prices quoted as traded, the corporate action noted, no adjustment rule | No — Gann stays silent on adjustment | — | CA policy remains an assumption |
| F17 | [45Y] p. 130; p. 133 | "The Master Time cycle which I have used to forecast every important boom and depression" — named, not disclosed | No — confirms withholding (register TOB-06); no further reading can close it | — | — |
| F18 | [45Y] p. 131–132 | 1950 outlook uses "48 and 49 months from the 1946 high", "six years from April 1942 low", "two years from the 1948 low" | Rule 10 counts are applied from **campaign** extremes | — | Consistent with F10 |
| F19 | [45Y] p. 66 | Only 1-day reactions; "there will come a time when the Averages will react 3 days or more. After that when they cross the top of the First Reaction, it will be a definite indication that the main trend has turned up" | Clarifies K3 signal timing: a 3-day reaction must first be recorded; the signal is the later cross | Yes | Faithful |
| F20 | [45Y] p. 67 (1913-01-18 is a Saturday) | 1913 NYSE traded six days a week | K3 "3 consecutive days" on a 6-day week is not the same object on NSE's 5-day week | — | K3-on-NSE is a **transfer** |

**Bearing on Rule 8, Rule 10, percentage, duration, culmination, anniversary, price basis:** covered
by F3–F12, F16. **Nothing in the remaining pages changes the Rule 8 overbalance sentences (register
Δ2-01/02), Rule 4 norms, or the Rule 5 section count.**

### 1.3 *Puts and Calls* (added 2026-09-15)

Read in full after the memo's first commit (register §29). Design-relevant only:

| # | Source | What Gann says | Changes a design decision? | Mechanizable? | Faithful / assumption |
|---|---|---|---|---|---|
| F21 | [PC37] p. 10, p. 14 | Rule 7: "Buy a Call when a stock reacts 40 to 50% of the last advance"; after fast moves the reaction "runs one-half or 50%" | No — adds a **fourth** percentage anchor sense (last move) and deepens the GF-8 anchor conflict; GF-8 stays excluded. Not added as a construct | Only with a defined "last advance" scale (rides on R-1) | Arm-1 claim; not in Stage 1 |
| F22 | [PC37] pp. 8–9, 15–16 | Trading ranges described by duration ("several weeks, several months, or even several years"; 4–6 months for low-priced stocks) and narrowness in points | No — R-2's main-trend outcome stays unmechanizable scale-free | No | Stage 2 |
| F23 | [PC37] pp. 11–12, 17 | "Stocks always move faster at higher levels than they do at low levels", with price bands | No — reinforces Stage-2 deferral and the price-level strata diagnostic (§11.H item 12) | — | — |
| F24 | [PC37]; [SPC41] | No 3-Day Chart, Rule 8 overbalance, day-count windows, anniversary, 144 square or circle divisions | Confirms GF-1, GF-4T/R8, GF-10 and the K3 findings unchanged | — | — |

---

## 2. Source-to-mechanization table

**Legend:** **G** = specified by Gann · **D** = statistical design choice · **IA** = implementation
assumption (Gann silent or discretionary).

| Component | Primary-source wording / evidence | Current mechanization | Still ambiguous? | Proposed resolution |
|---|---|---|---|---|
| **K3 / 3-Day Chart** | [45Y] p. 63 rule; p. 61 "3-day moves or more … sometimes use 1 and 2-day moves … calendar days"; record pp. 66–73 | Strict rule, exception not applied (design doc §D.2) | **Yes — severely.** Record departs in 7/61 swings (F2); 6-day vs 5-day week (F20); asymmetric down-switch wording; equal and outside bars; initialization (§5) | **Operator ruling R-1**: admit strict K3 as a *declared approximation of a discretionary Gann detector*, or exclude every K3-consuming construct (all of Stage 1) |
| **Rule 8 time overbalance** | [45Y] p. 11: time of a decline exceeding the time of "a previous decline"; bear mirror; p. 12 "The Time change is more important than reversal in price"; p. 39 "the greatest TIME PERIOD" | GF-10: current K3 decline vs immediately preceding K3 decline | **Yes**: previous vs greatest (F12); swing scale of a "decline" (K3 vs major swing) | Primary "previous" (the rule sentence), greatest = robustness (D). Swing scale rides on R-1 (IA) |
| **Rule 10 change in trend** | [45Y] p. 13; p. 63 (break of last 3-Day low; cross of last top); p. 66 (after a recorded 3-day reaction); pp. 61–62 trading-range qualifier | O-R10: K3 break of last swing low / cross of last swing top | **Yes**: minor vs main trend (F3); penetration size (F4); intraday vs close (F5) | **R-2**: O-R10 = *minor* change ("at least temporarily"), any penetration (IA), intraday high/low basis (IA, matches "tops and bottoms"). Main-trend outcome not mechanizable → not used |
| **Rule 9 market state** | [45Y] p. 12: higher tops and bottoms = up trend | S9: last two K3 highs and last two K3 lows both rising / both falling | Yes: "two" is IA; mixed states | Pin S9 as IA; no state → construct inactive |
| **Percentage rule** | [45Y] p. 8 Rule 3 "any high level"; ch. IV; applied from campaign tops pp. 50, 54, 125 (F8); ex-post density pp. 96–98 (F15) | GF-8 on a K3 top | **Yes — text vs every example** | **Exclude from Stage 1** (§4). Anchor ruling needed before any revival |
| **Duration rules** | [45Y] pp. 8–9 Rule 4 (3 weeks; after 30+ days next ~6–7 weeks; after 45–49+ days ~60–65 days); WSSS p. 50; NSTD p. 38 | GF-6: bull K3 reaction beyond 65 calendar days | Yes: whether 6–7 weeks is elapsed-from-start or next-window; "reaction" scale (R-1) | **Defer** (under-powered under assumed *p*; §9) |
| **Culmination** | [45Y] p. 9 Rule 5 "campaigns move in 3 to 4 Sections"; p. 12 smaller price and shorter time at 3rd/4th section | GF-7 R8S on K3 upswings | **Yes — section scale.** Rule 5 sections are **campaign** waves (e.g. a 56-month bull market in 3–4 sections, p. 49); K3 upswings last days | **Exclude from Stage 1**: no primary text makes a 3-day swing a "section" (§6) |
| **Master Square time points** | [MMPTC] p. 4 (½, end, ⅓, ⅔, ¼, ¾ of 144 from highs and lows; wheat example uses the all-time high and low); p. 6 (144 market days or 144 calendar days); p. 7 | GF-1: P4 = {36, 48, 72, 96, 108, 144} + repeats, calendar days, from to-date extreme high and low | Yes: calendar vs market days (both G); days vs weeks vs months (all G); anchor sense | Anchor = all-time-to-date extreme (G: wheat example), left-censored (IA). **T: R-9** (calendar recommended for battery consistency, D) |
| **Circle divisions / Rule 8 day windows as time** | [45Y] p. 11 windows "from any high or low" with importance weighting; inconsistent usage pp. 46, 48, 55 (F6); [MMPTC] pp. 2, 8 circle divisions | GF-4T/R8 from last confirmed K3 turn, p. 11 windows | **Yes**: *w* (F6); "any" high or low vs last turn; importance weighting unmechanizable | Printed p. 11 list primary (G); usage windows robustness. Last turn only (D: "any" over all turns covers nearly every date and is unfalsifiable) → **R-4, R-9** |
| **Anniversary** | WSSS p. 55; NSTD p. 14; [45Y] pp. 92–93 (all-time + campaign extremes), pp. 85–88 (calendar-year extremes, exact dates), p. 13 Rule 10 | GF-5: month of to-date extreme | **Yes — three senses of "extreme"** (F9, F10) | **Defer** (under-powered; §9). Anchor sense → R-3 before any revival |
| **Anchor definition (all)** | "extreme", "important", "any high or low", "major swings" used without definition (F3, F8–F10) | Mixed per construct | Yes | Per construct in §7; cross-cutting ruling **R-3** |
| **Time counting** | [45Y] pp. 46–55 arithmetic (F7); p. 61 | Calendar days, start excluded | No | Faithful (G) |
| **Price basis / CA** | [45Y] p. 60 (true average excludes split-ups); p. 123 (quotes as traded, notes stock dividend) | Ratio-adjusted as-of-*t* series for Stage 1 | Gann silent on adjustment | IA; spin-off / special-dividend windows excluded (external enumeration required, EOD audit §L) |

---

## 3. GF-10 status

| Item | Content |
|---|---|
| **Old ruling** | Operator ruling 7, 2026-09-14: "Keep relative time-overbalance unresolved / Arm 2". Based on F0 TOB-02 (NOT FOUND in [TST]/[WSSS]) and TOB-03 (secondary-only) |
| **New evidence** | [45Y] p. 11, Rule 8, *Market Over-Balanced*: "When a Time period on a decline exceeds the Time period of a previous decline it indicates a change in trend"; bear-market mirror; p. 12 "The Time change is more important than reversal in price". Read at two resolutions (register §27). Nothing in pp. 46–148 qualifies or withdraws it |
| **Exact contradiction** | Ruling 7 treats the relative form as unestablished in Gann's corpus. [45Y] states it as a numbered rule, for averages **and individual stocks** (p. 11), with a time-over-price ranking |
| **Recommended new ruling** | **GF-10 = GANN-FAITHFUL (Arm 1).** The rule text is sufficient. Its Stage-1 **mechanization** is not independent: it is admissible only if R-1 (K3) is accepted. **Ruled 2026-09-15: accepted (R-5), ruling 7 superseded; R-1 accepted** |
| **What remains ambiguous** | (1) "a previous decline" (p. 11) vs "the greatest TIME PERIOD" (p. 39) and "sharpest reaction since" (p. 53) — both Gann; (2) the swing scale of a "decline" — Gann gives no detector in Rule 8; (3) "advancing" market state (S9 is IA); (4) the outcome scale (R-2). None is resolvable from primary text; (1) is pinned by design reason, (2)–(4) by operator ruling |

The catalogue's old GO-2 modern additions (log depth, session counts, "longest prior" as primary,
*k* ∈ {1, 2}) remain Arm 2.

---

## 4. GF-8 and GF-9 status

| | GF-8 percentage | GF-9 modal swing duration |
|---|---|---|
| **Primary evidence** | [45Y] p. 8 Rule 3; ch. IV pp. 30–38; worked applications pp. 50, 54, 125; ex-post levels pp. 96–98 | [45Y] p. 57 (ch. VI); pp. 88–89 time-swing statistics |
| **Literal Gann content** | Buy/sell on a 50% decline from any high or 50% advance from any low, with the main trend; bands 3–5 … 85–87%; 50% and 100% most important | With a record of each important swing's time, watch for a change at the end of the cycle that has repeated most often |
| **Implementation extensions needed** | An anchor: the rule says "any high level", but every worked example anchors on a **campaign** top, and "campaign" is undefined (F8). The "main trend" filter (S9, IA) | A swing population: Gann's is "mostly the major swings when there was a rapid advance or a rapid decline" (hand-selected, F11). Bins: Gann's overlap. Per-stock application: stated for the averages |
| **Arm 1?** | **Yes, as a claim.** Not faithfully mechanizable without an anchor ruling | **Yes, as a claim** on the averages. A per-stock mechanized mode over K3 swings would be an **Arm-2** extension |
| **Stage-1 role** | **Excluded.** (1) Rule text and all examples conflict on the anchor; (2) the example-consistent anchor needs an undefined campaign detector; (3) under the assumed flag rate it is under-powered (§9) | **Excluded.** Population and bins are not mechanizable to Gann's standard (rule 14) |

**The design doc's §D.4 GF-8 cell (anchor "any K3 top") is withdrawn as a recommendation.** It rested
on the rule wording alone, which the worked examples contradict.

**Ruled 2026-09-15 (R-6):** GF-8 and GF-9 excluded from Stage 1; retained as Arm-1 claims / deferred
research items.

---

## 5. K3 lock-down

**Primary text** ([45Y] p. 63, paraphrased except where quoted): when advancing, with higher bottoms
and higher tops for 3 consecutive days, move the chart up to the top of the third day; if it reacts
2 days, do not record it; when it moves above the first top, keep moving the line up to the top of
each day "until there were 3 days lower Bottoms", then move the line down to the low of the third day;
ignore 2-day rallies except near extreme highs or lows, especially in very wide fluctuations. p. 61:
"All of these moves are based on calendar days."

| # | Item | Gann | Status | Proposed pin (if R-1 accepts strict K3) |
|---|---|---|---|---|
| 1 | Construction | p. 63 rule as above | G (core); exception discretionary | Two-state machine: UP line / DOWN line, updated once per completed session |
| 2 | Swing high | The line's highest top before the switch to DOWN | G | Swing high = max daily high while UP; date = day of that high |
| 3 | Swing low | Mirror | G (by mirror; text is written for the advancing case) | Swing low = min daily low while DOWN |
| 4 | Confirmation timing | Switch happens on the 3rd day | G | Swing extreme **usable from the close of the 3rd qualifying session**; time counts run from the extreme's own date (G, p. 11 "from any high or low"); causality lag is required (IA) |
| 5 | Equal highs / lows | Silent | **IMPLEMENTATION ASSUMPTION** | Strict inequality; an equal value breaks the run |
| 6 | Gaps | Silent | **IMPLEMENTATION ASSUMPTION** | No special handling; daily high/low as recorded |
| 7 | 2-day exception | "sometimes", "we wish to catch a turn", "especially if the fluctuations were very wide"; applied in the record including cases not shown to be near extremes (F1, F2) | **Discretionary — not mechanizable** | Not applied. **Declared departure**; any mechanized exception rule would be an invention (Arm 2) |
| 8 | Initialization | Silent | **IMPLEMENTATION ASSUMPTION** | No state until the first 3-session run of higher highs + higher lows, or of lower lows; first swing extreme usable only after the first switch; per-stock burn-in from its data start |
| 9 | Calendar vs sessions | Construction counts "days" of price bars; time periods are calendar days (p. 61; F7) | G for time counting; **IA** for construction on a 5-day NSE week (F20) | Runs counted in consecutive NSE sessions; all durations in calendar days |
| 10 | Construction vs time-counting | Distinct in the text | G | As item 9 |
| 11 | Up-switch vs down-switch conditions | Up: higher bottoms **and** higher tops. Down: "3 days lower Bottoms" only | **Ambiguous** (literal asymmetry or shorthand) | **IMPLEMENTATION ASSUMPTION**: literal — up needs HH+HL, down needs LL (and mirror: from DOWN, switch up needs HH+HL; from UP, switch down needs LL). Symmetric HH+HL / LL+LH as robustness |
| 12 | Day-over-day comparison | "higher Bottoms and higher Tops for 3 consecutive days" | **IA** | Each session vs the previous session |
| 13 | Outside / inside days | Silent | **IMPLEMENTATION ASSUMPTION** | Outside day (HH + LL): extends a DOWN run's lower-low count and breaks an UP-switch run; inside day breaks both runs |

**Conclusion.** The strict rule is well defined and reproducible by code. It is **not** Gann's
detector as practised: his record shows discretionary short swings (F2), on a 6-day week (F20). Every
Stage-1 construct consumes K3 through the outcome O-R10, so **R-1 gates the whole of Stage 1**.

**Ruled 2026-09-15 (R-1):** strict K3 admitted as an explicitly labelled approximation of Gann's
discretionary detector, all implementation assumptions above preserved, with the ≥ 7 of 61 disclosure.
Row 7's "declared departure" is to be read as that label.

---

## 6. Stage-1 construct set reassessment

| Construct | Fidelity after Steps 1–5 | Mechanizable without an unresolvable pin? | Power under stated assumptions (§9) | Recommendation |
|---|---|---|---|---|
| **GF-1** Master Square | Arm 1; anchor resolved by [MMPTC] wheat example | Yes, given R-1 (outcome) and R-9 (T) | Screen opt 1.00; confirmatory opt 0.99 at 3.69 y | **Primary** |
| **GF-4T/R8** Rule 8 windows | Arm 1 | Yes, given R-1, R-4 (*w*), R-9 (anchor scope) | Screen opt 1.00; confirmatory opt 1.00 | **Primary** |
| **GF-10** time overbalance | Arm 1 (pending §3 ruling) | Yes, given R-1, R-2, R-5 | Screen opt 1.00; confirmatory opt 0.85 | **Primary** (pending) |
| GF-7 culmination | Arm 1 claim | **No.** "Section" is a campaign wave; mapping it to a K3 upswing has no textual basis, and another researcher would reasonably choose a larger scale | Screen opt 1.00; confirmatory opt 0.79 | **Excluded from Stage 1** (fidelity, not power) |
| GF-5 anniversary | Arm 1 claim | No: three senses of "extreme" (R-3) | Opt fails within 10 y under assumptions | **Deferred** — not retired |
| GF-6 reaction duration | Arm 1 claim | Partly (window reading; reaction scale rides on R-1) | Opt fails within 10 y under assumed *p* | **Deferred** — not retired |
| GF-8 percentage | Arm 1 claim | No (§4) | Opt fails within 10 y under assumed *p* | **Excluded from Stage 1** |
| GF-9 modal duration | Arm 1 claim (averages) | No (§4) | — | **Excluded from Stage 1** |
| GF-2 angles | Arm 1 framework | No (course withheld) | — | Excluded (unchanged, decision B) |
| GF-3, GF-4P, TIM-10, point rules | Arm 1 conditional | Needs U-LIT | — | **Stage 2 — not in the Stage-1 experiment** |

**Pinned multiplicity if accepted: m = 3.** *(Ruled 2026-09-15 — R-5 to R-8: primaries GF-1, GF-4T/R8,
GF-10; GF-7, GF-8, GF-9 excluded from Stage 1; GF-5, GF-6 deferred, not retired.)* The earlier four-construct proposal included GF-7; it is
removed on fidelity grounds. If the operator re-admits GF-7, m = 4 and the §9–§10 figures (computed at
m = 4) apply directly.

**Observation (not a selection criterion):** fidelity review and power arithmetic converge on the
same small set. GF-5, GF-6 and GF-8 fail power under their assumptions and also carry unresolved
anchors or scales; GF-7 and GF-9 fail fidelity.

---

## 7. Primary-cell audit (surviving constructs)

Common to all three: per-stock construction on the N100 PIT panel; formation at the last session of
each calendar week; outcome **O-R10** = a K3 trend-change signal in the construct's direction during
the next 5 sessions (binary); statistic and inference per §8; eligibility = PIT member with a
confirmed K3 state and the construct's anchor available.

### 7.1 GF-1 — Master Square time points

| Question | Answer |
|---|---|
| 1. Motivating text | [MMPTC] p. 4: most changes in trend occur when time periods from highs and lows reach ½ of 144, the end, ⅓, ⅔, ¼, ¾; worked wheat example counts from the all-time low (28) and high (325) |
| 2. Specified by Gann | Point set P4 = {36, 48, 72, 96, 108, 144}, repeating every 144; counted from the high and the low; units days, weeks or months; calendar **or** market days |
| 3. Design choices | Weekly formation; score = 1 if any calendar date in the next week equals anchor date + *n* for *n* ∈ P4 (+144*k*); P4 over P8 (Gann's own "most changes" list); days over weeks/months (resolution matches a weekly outcome) |
| 4. Implementation assumptions | Left-censored all-time-to-date extremes (data start 2011-03-25 or listing); replaced extreme restarts the count; calendar days (R-9); O-R10 and K3 (R-1, R-2) |
| 5. Another reasonable choice? | Yes: market days (Gann admits both); weeks or months as units; important K3 highs/lows as anchors (p. 7) |
| 6. Resolvable from primary evidence? | Anchor: **yes** (wheat example). Unit and calendar basis: **no** — Gann states both |
| 7. Exclude rather than pin? | No: the unresolved slot is a binary choice between two Gann-admitted options. **Operator pins T (R-9)**; the other is robustness, off the pass path |

### 7.2 GF-4T/R8 — Rule 8 day windows

| Question | Answer |
|---|---|
| 1. Motivating text | [45Y] p. 11: check whether the market has run from any high or low 7–12, 18–21, 28–31, 42–49, 57–65, 85–92, 112–120, 150–157 or 175–185 days; the more important the top or bottom, the more important the change |
| 2. Specified by Gann | The window list (printed rule), calendar days, anchor = a high or low |
| 3. Design choices | Anchor = **most recent confirmed K3 swing extreme only**; score = 1 if any date in the next week falls inside a window; no importance weighting |
| 4. Implementation assumptions | K3 swing points as "highs and lows" (R-1); p. 11 widths (R-4) |
| 5. Another reasonable choice? | Yes: all swing points within 185 days ("any"); wider usage windows (F6); weighting by swing size |
| 6. Resolvable? | **No** for *w* (Gann inconsistent) and anchor scope ("any" is literal but, over every recent swing point, flags nearly every date) |
| 7. Exclude rather than pin? | Pinning is defensible only because the alternatives are either Gann's own printed rule (window list) or degenerate (all turns → coverage near 1, no contrast). **Operator ruling R-4 and R-9**; if the operator judges the last-turn choice arbitrary, exclude |

### 7.3 GF-10 — Rule 8 time overbalance (pending §3 — accepted 2026-09-15, R-5)

| Question | Answer |
|---|---|
| 1. Motivating text | [45Y] pp. 11–12 (Rule 8, *Market Over-Balanced*) |
| 2. Specified by Gann | Compare the time of the current decline with a previous decline; exceedance indicates change; mirror in bear markets; time outranks price |
| 3. Design choices | Primary comparison = **immediately preceding** completed K3 decline (the rule sentence); score = 1 from the first formation at which the current decline's calendar-day duration (from its swing-high date to *t*) exceeds the previous decline's (high date to low date), while no up-switch has occurred |
| 4. Implementation assumptions | "Decline" = K3 down-swing (R-1); "advancing market" = S9 bull state; outcome = break of the last K3 swing low (R-2); bear mirror pooled with sign |
| 5. Another reasonable choice? | Yes: greatest prior decline (p. 39, p. 53); major swings as declines |
| 6. Resolvable? | "Previous" vs "greatest": **not** by text alone; the rule sentence itself says "a previous decline", which is the stronger textual basis. Swing scale: **no** |
| 7. Exclude rather than pin? | Pin "previous" (textual), greatest as robustness. Swing scale follows R-1: if R-1 is refused, GF-10 has no mechanization and is excluded |

---

## 8. Surrogate-differenced IC — audit

### 8.1 Problems with the current proposal

1. **Per-date differencing is ill-defined.** A bootstrap that resamples dates produces a surrogate
   panel whose date *t* is not the market of date *t*. "IC_real(t) − IC_surrogate(t)" subtracts
   unrelated quantities; the paired variance and any normal approximation built on it are wrong.
2. **Independent per-stock resampling destroys cross-sectional dependence.** Market-wide swings
   synchronize K3 turns across stocks; the real per-date IC dispersion reflects that. Independent
   surrogates would understate the null variance and over-reject.
3. **Close-to-close surrogates cannot drive K3.** K3 needs daily highs and lows.
4. **A data-driven block length** (e.g. Politis–White) is estimated from the returns being tested.
   It reads no outcome linkage, but it is a data-dependent choice made on the test window.
5. **Rejecting the surrogate null is not Gann-specific.** A stationary block bootstrap removes
   dependence beyond roughly the block length, and non-stationarity. Real markets differ from that
   null in ways (long-memory volatility, regimes, trends) that could raise the IC without any Gann
   content.

### 8.2 Recommended specification

| Element | Recommendation | Reason |
|---|---|---|
| **Test statistic** | T_c = mean over formation weeks of the per-date Spearman IC (φ) of score vs O-R10 across eligible names | Single statistic, no differencing |
| **Null distribution (mechanics)** | Recompute T_c on **B** surrogate panels through identical code (K3, anchors, scores, outcomes). p_sur = (1 + #{T_c(b) ≥ T_c}) / (B + 1) | Monte Carlo rank test; valid to the extent the surrogate generates data from the null; no normal approximation |
| **Surrogate** | **Synchronized stationary block bootstrap of daily bar vectors**: for each session, the vector (ln H/C₋₁, ln L/C₋₁, ln C/C₋₁) per stock; the **same** resampled date blocks for all stocks; paths rebuilt per stock from its first observed close; placed on the **real** trading calendar (weekends and holidays unchanged, so calendar-day counts behave as in real data) | Preserves each stock's own distribution, intra-bar geometry incl. gaps, volatility clustering up to the block scale, and contemporaneous cross-sectional dependence |
| **Missing bars** | PIT membership and listing masks taken from the real calendar; a stock's drawn bar that does not exist is redrawn from that stock's own bars in the same block neighbourhood (IA) | Small for N100 (most names listed before 2011); declared |
| **Mean block length** | Pinned a priori at **20 sessions**; 5 and 60 reported off the pass path | Not estimated from data. 20 sessions spans Gann's own "11 to 35 days" most-common swing band ([45Y] p. 89), a source-based scale |
| **Draws** | **B = 1999**, fixed seed recorded, no extension after seeing p | At α = 0.0125 (m = 4) the rejection region holds 25 draws; Monte Carlo SE of p at α ≈ 0.0025. At m = 3 (α ≈ 0.0167) the same B is adequate |
| **Gann-specificity (placebo) leg** | On **real** data: T_c recomputed with a pinned placebo point set of matched coverage (GF-1: non-Gann fractions of 144; GF-4T/R8: window set with identical widths, centres shifted to non-Gann day counts). p_plac = rank of T_c among the placebo sets. For GF-10: **Gann's own contrast** — T_c(time overbalance) > T_c(price overbalance), p from the surrogate joint distribution (**R-10**; alternative: ratio placebos 0.75× / 1.33×) | Separates "Gann's numbers matter" from "any swing-timing regularity" |
| **Pass rule** | **Intersection-union test** (confirmatory tests): pass iff p_sur ≤ α **and** p_plac ≤ α. **The screen's kill rule uses the surrogate leg only** (§10) | IUT controls size at α without further adjustment; both nulls must fall. Its power is at most the weaker leg's, and the placebo leg's power is not computable a priori |
| **Date clustering / dependence** | Carried by the synchronized surrogate up to the block scale; no Newey–West or normal approximation | The null spread comes from the resampled panel |
| **Effect size report** | T_c − median T_c(b), with the 2.5–97.5% surrogate interval | **Descriptive only**, off the pass path |
| **Size calibration (pre-read, blind)** | After freeze and before the real statistic is computed: treat 200 surrogate panels as pseudo-real and run the full test; the rejection rate must be ≤ 2α. Record the result before unblinding | Checks the bootstrap test's size on this panel's dependence structure. Computes no real-data score-outcome association |

**Limitation to state in every report:** passing the surrogate leg means the real data differ from a
weakly dependent stationary process in the way the statistic detects. Only the conjunction with the
placebo leg supports Gann-specific content.

---

## 9. Power / RFA logic — audit

**Accepted: do not declare an RFA now.** Reasons, beyond power:

1. **The specification is not frozen.** R-1 to R-5 change what the construct *is*. A declaration
   frozen against an unfrozen construct would be void.
2. **`n_available` is undefined.** GR-1.3: spent windows may not contribute. Equity EOD
   2011-03-25 → 2022-12-30 is signal-spent (register Q-1, Q-2, Q-3, Q-5). **2023-01-02 → 2026-09-11
   is unresolved** — register §6 lists it as "largely unread at signal level by the cash-equity
   batteries", but the EOD feasibility audit §K records that the windows actually read by the 19
   `scripts/signal_engine/` and 4 `scripts/mrlc_test/` equity-EOD readers are not stated, and "only
   these unrecorded windows decide" freshness (**R-11**). This corrects design doc §E.4 item 1, which
   treated the span as indicated spent.
3. **The δ band is borrowed** (CB-N50 HOLDOUT IC, different hypothesis). No Gann-specific effect-size
   evidence exists.
4. **Contract fit is approximate.** The RFA's noncentral-t power is a proxy for the §8 Monte Carlo
   IUT; the IUT's power is at most the smaller leg's.

**Power under stated assumptions** (`gf_screen_power.py`; α = 0.05/4 one-sided; *q* = 0.30; attenuation
and defined-date corrections as in design doc §E.2):

| Construct | Window | n | Power opt | Power cen |
|---|---|---|---|---|
| GF-1 | Confirmatory **if** 2023-01-02 → 2026-09-11 is ruled fresh (3.69 y) | 191 | 0.99 | 0.25 |
| GF-4T/R8 | same | 191 | 1.00 | 0.28 |
| GF-10 | same | 191 | 0.85 | 0.12 |
| GF-7 (excluded) | same | 191 | 0.79 | 0.11 |
| GF-1 / GF-4T/R8 / GF-10 | Forward 5 y | 259 | 1.00 / 1.00 / 0.94 | 0.34 / 0.38 / 0.17 |

At m = 3 α rises to 0.0167 and all figures rise slightly; not recomputed, to avoid choosing *m* by
power.

**Reading.** If R-11 rules the 2023–2026 span fresh, the gate's optimistic corner would return
PROCEED for GF-1, GF-4T/R8 and GF-10 — "not provably infeasible" only; central-band power is 0.12–0.28.
If the span is spent, confirmation is forward-only.

**A vs B — correction to design doc §E.5 option 2.** That option proposed recording GF-5, GF-6 and
GF-8 as "power-infeasible". This memo **challenges** it:
- GF-5's flag rate is geometric (2 of 12 months), but δ, *q* and *k* are assumptions.
- GF-6's and GF-8's flag rates are themselves assumptions.
- Nothing in Gann's text fixes an effect size.

So each is **under-powered under the stated assumptions (A)**. None may be recorded as permanently
infeasible (B). Recommended wording: *"deferred — under-powered under declared assumptions; not
retired"*.

---

## 10. Non-confirmatory feasibility screen — admissibility

**Verdict: scientifically admissible as a GR-1.4 non-confirmatory kill-screen, on the conditions
below.** Not authorized here; requires an operator ruling (**R-12**).

| Element | Specification |
|---|---|
| **Window** | **2011-03-25 → 2022-12-30 only**, less per-stock burn-in. **Correction:** design doc §E.5 proposed 2011-03-25 → 2026-09-11; that would spend 2023-01-02 → 2026-09-11, the only span that could still be confirmatory (R-11) |
| **Constructs entering** | GF-1, GF-4T/R8, GF-10 (m = 3; m = 4 if GF-7 re-admitted). Pinned before the screen |
| **Statistic** | T_c per §8.2 |
| **Null** | IUT of the surrogate null and the placebo / contrast null, §8.2 |
| **Threshold** | **Kill decision on the surrogate leg only:** a construct survives iff p_sur ≤ 0.05/m, one-sided. The placebo / contrast leg (p_plac ≤ 0.05/m) is computed and reported as a **separate Gann-specificity finding**; it does not retire a construct |
| **Kill rule** | A construct whose surrogate leg does not reject is **retired from forward testing under this protocol**. Report wording: *"no evidence, against a surrogate null, of an effect of the optimistic size that confirmation would need"* — **never** "Gann's rule is false". A construct that survives the surrogate leg but not the placebo leg is labelled *"timing effect not shown to be Gann-specific"*; whether it proceeds to a confirmatory IUT pre-registration is an operator decision (R-12) |
| **Power** | **Proxy for the surrogate leg only** (noncentral t, `gf_screen_power.py`), dev-only window, α = 0.05/4: optimistic 1.00 for all; central GF-1 0.72, GF-4T/R8 0.77, GF-10 0.39 (GF-7 0.34). **These are upper bounds:** n takes no burn-in haircut, and dependence is assumed away. At m = 3 the threshold 0.05/3 is less strict than the 0.05/4 used here, so on that count the figures understate. **The IUT's power is not established** — the placebo leg's power depends on how far Gann's day counts differ from shifted placebo windows, which no stated assumption pins. That is why the kill rule rests on the surrogate leg alone. A central-size effect can still be missed |
| **Surrogate uncertainty** | B = 1999 fixed; +1 rank formula; no extension; size calibration (§8.2) recorded before unblinding |
| **Use of historical N100** | Legitimate: operator exposure ruling ("may be used freely … not pristine confirmation"); GR-1.1, GR-1.4. The window is already signal-spent on this surface, so the screen spends nothing new |
| **Exposure label** | **signal — non-confirmatory (GR-1.4)** |
| **Register row (draft; operator-owned; must be appended before the read)** | `\| G-S1 \| Equity EOD panel (N100 PIT, ratio-adjusted as-of-t) \| 2011-03-25 → 2022-12-30 \| **signal** (non-confirmatory, GR-1.4) \| PTMS-Gann Stage-1 screen: GF-1, GF-4T/R8, GF-10 \| <committed screen script paths> \| <frozen protocol path + SHA-256>; report labelled NON-CONFIRMATORY; feeds no gate \|` — seven fields, matching register §5c (#, Surface, Window, Level, Hypothesis family, Consumer, Evidence) |
| **Selection bias into confirmation** | (1) Confirmation must use disjoint data (2023+ if fresh, else forward). (2) **Confirmatory α = 0.05/m_entered** (pinned before the screen), not 0.05/m_survivors. (3) Winner's curse: the confirmatory δ band must **not** use screen estimates. (4) GR-1.5: the confirmatory pre-registration must disclose the screen and its results |
| **Description** | The screen must never be described as confirmation, validation, or evidence that a Gann construct works |

---

## 11. Governance decision memo

### A. Primary-source status

**Established (primary, read on the page):**
- Relative time overbalance and its time-over-price ranking ([45Y] pp. 11–12).
- The 3-Day Chart rule, its discretionary exception, and calendar-day time counting ([45Y] pp. 61, 63;
  arithmetic on pp. 46–55).
- Rule 3 percentages, Rule 4 duration norms, Rule 5 sections, Rule 8 day windows and seasonal dates,
  Rule 9 state, Rule 10 signals and exact-year/month counts ([45Y] pp. 8–13).
- Anniversary practice in three anchor senses ([45Y] pp. 85–88, 92–93).
- [MMPTC] 144-square time points, circle divisions, chart-space convention (register §26).

**Unresolved:**
- Gann's 3-Day detector as practised (discretionary; F2).
- "Extreme", "important", "campaign", "section", "trading range" — used, never defined.
- Rule 8 window tolerances (F6).
- The angle rules (Master Forecasting course) and scale Special Instructions — not supplied.
- The Master Time cycle — withheld ([45Y] p. 130).
- Square-of-Nine spiral and a 360-day annual cycle — not found.
- Stock price translation (U-LIT) — no textual resolution.

**Reading complete:** [45Y] pp. 1–148. *Commodities* copy is a translation (inadmissible for wording).
*How to Make Profits Trading in Puts and Calls* (1937, pp. 1–18) and the re-typeset *How to Sell Puts
and Calls* (1941, pp. 1–3), SHA-256 `d8ad4cb0…`: **all pages read** (register §29, Δ4). They change no
Stage-1 disposition. They add a fourth percentage sense (40–50% of the last advance, Rule 7), describe
trading ranges by duration and point width (still not scale-free), and state that stocks move faster
at higher price levels.

### B. Arm 1 — Gann-faithful (Stage-1 candidates)

| Construct | Why it qualifies | Conditional on |
|---|---|---|
| **GF-1** Master Square time points | [MMPTC] p. 4 point set and worked anchor; time-only | R-1, R-2, R-9 |
| **GF-4T/R8** Rule 8 day windows | [45Y] p. 11 printed list; calendar days | R-1, R-2, R-4, R-9 |
| **GF-10** Rule 8 time overbalance | [45Y] pp. 11–12 verbatim rule for stocks and averages | R-5 (supersede ruling 7), R-1, R-2, R-10 |

**Arm 1 claims not in Stage 1:** GF-5 and GF-6 (deferred, under-powered under assumptions), GF-7
(section scale), GF-8 (anchor conflict), GF-9 (discretionary population), GF-2 (rules withheld).

### C. Arm 2 — Gann-inspired (excluded from the faithful experiment)

- GA-3 / GS-5 and all ATR-, σ-, percentage- or prior-swing-normalized angles (ruling 6, unchanged).
- Any mechanized 1- or 2-day exception to the 3-Day Chart.
- GF-7 on K3 upswings as "sections"; GF-9 as a per-stock mechanized mode.
- GO-2's modern additions: log depth, session counts, *k* ∈ {1, 2}, "longest prior" as the primary comparison.
- GT-2 time symmetry (only a narrative example, [45Y] p. 53).
- Any common-parameter pooled construct presented as a Gann claim.

### D. Stage 2 — translation-dependent (deferred)

GF-3 (square of high/low/range), GF-4P (circle degrees as price), TIM-10 (85–100 points), Rule 2
double tops in points, Rule 6 point reactions, Rule 12 one point per day, the 9-Point Chart, the
5-point and 3-point penetration rules, GF-2 if the course is ever obtained.

**Why deferred:** each needs a quoted-point ↔ rupee translation that Gann never gives; [45Y] shows the
point rules depend on price level without conversion (pp. 8, 48, 51, 80). They need the U-LIT ruling,
as-traded prices and a CA policy, and they must not enter the Stage-1 experiment.

### E. Open governance rulings (operator)

**Ruled 2026-09-15** — see the RULING rows of `PTMS_GANN_OPERATOR_RULING_REGISTER_2026-09-15.md`. The
Recommendation column is preserved. R-12's sub-question (may a surrogate-pass / specificity-fail
construct proceed to a confirmatory test?) was not ruled. R-15 remains open.

| # | Ruling | Recommendation |
|---|---|---|
| **R-1** | Admit strict K3 (§5, incl. IA items 5, 6, 8, 11–13) as a *declared approximation* of Gann's discretionary 3-Day detector on a 5-day NSE week — or exclude all K3-consuming constructs (all of Stage 1) | Admit, labelled "approximation; Gann's own record departs in ≥ 7 of 61 swings" |
| **R-2** | Outcome scale: O-R10 as a minor ("at least temporarily") change, any penetration, intraday basis — main-trend outcome not used | Accept |
| **R-3** | Sense of "extreme" for anchors (all-time-to-date / calendar-year / campaign) | GF-1: all-time-to-date (wheat example). Leave GF-5 / GF-8 deferred until ruled |
| **R-4** | Rule 8 windows: printed p. 11 list (primary) vs worked-example windows (robustness) | Printed list primary |
| **R-5** | Supersede ruling 7: GF-10 = GANN-FAITHFUL; comparison "previous" primary, "greatest" robustness | Accept |
| **R-6** | GF-8 and GF-9: Arm-1 claims, excluded from Stage 1 | Accept |
| **R-7** | GF-7 excluded from Stage 1 (section scale undefined) | Accept |
| **R-8** | GF-5 and GF-6: "deferred — under-powered under declared assumptions; not retired" (replaces design doc §E.5 option 2) | Accept |
| **R-9** | GF-1 unit (calendar vs market days); GF-4T/R8 anchor scope (last confirmed K3 turn vs all turns) | Calendar days; last turn. If either is judged arbitrary, exclude the construct |
| **R-10** | GF-10 Gann-specificity leg: Gann's time-vs-price contrast vs ratio placebos | Time-vs-price contrast |
| **R-11** | Freshness of equity EOD 2023-01-02 → 2026-09-11: record the equity-EOD windows of the `signal_engine` and `mrlc_test` readers (EOD audit §L condition 1) | Must precede any confirmatory design |
| **R-12** | Authorize the non-confirmatory screen on 2011-03-25 → 2022-12-30 with register row G-S1 appended first; kill rule on the surrogate leg only; decide whether a surrogate-pass / placebo-fail construct may proceed to a confirmatory IUT | Authorize only after R-1–R-10, R-13, R-14 and the §H freeze. Note: the screen's power is established only as a proxy for the surrogate leg |
| **R-13** | Scoped EOD substrate certification and external enumeration of spin-offs / special dividends (EOD audit §L condition 2) | Required before any read |
| **R-14** | Surrogate and inference specification (§8.2) incl. block length 20, B = 1999, IUT, blind size calibration | Accept |
| **R-15** | U-LIT translation (Stage 2 only) | Not needed for Stage 1; unchanged |

### F. Proposed Stage-1 primary cells (one per construct; everything else off-path)

| Construct | Primary cell |
|---|---|
| **GF-1** | Anchor: each stock's all-time-to-date extreme high and extreme low (left-censored at data start; a replaced extreme restarts its count). Score at week-end *t* = 1 if any calendar date in the next 7 days equals anchor date + *n*, *n* ∈ {36, 48, 72, 96, 108, 144} + 144*k*, counted in calendar days, anchor usable only once established. Outcome O-R10 within the next 5 sessions |
| **GF-4T/R8** | Anchor: the most recent confirmed K3 swing high or low. Score = 1 if any calendar date in the next 7 days falls inside {7–12, 18–21, 28–31, 42–49, 57–65, 85–92, 112–120, 150–157, 175–185} calendar days from the anchor date. Outcome O-R10 within the next 5 sessions |
| **GF-10** | Stock in S9 bull state and in a K3 decline. Score = 1 at week-end *t* if the calendar-day duration from the current decline's swing-high date to *t* exceeds the duration of the immediately preceding completed K3 decline, and no up-switch has occurred. Outcome: break of the last K3 swing low within the next 5 sessions. Bear mirror pooled with sign |

Statistic and inference for all: §8.2, α = 0.05/m, m = 3.

### G. RFA status

**No RFA declaration is justified now.** The construct specification is not frozen (R-1–R-10),
`n_available` is undefined pending R-11, the δ band is borrowed, and central-band power on any
admissible confirmatory window is 0.12–0.38. An RFA becomes meaningful only after the freeze and R-11,
against the confirmatory window those rulings define.

### H. Empirical-read gate — what must be frozen before anyone inspects outcomes

Nothing below exists yet. **All** must be committed, hashed and operator-approved before any
score–outcome association is computed on real data, including the screen:

1. Operator rulings R-1 to R-14 recorded in writing.
2. The construct set and **m**, and the primary cell of each construct exactly as in §F.
3. The complete K3 algorithm: every §5 row, including each IMPLEMENTATION ASSUMPTION.
4. S9 state rule; O-R10 definition (direction, penetration, intraday basis, 5-session horizon).
5. Anchors (sense, left-censoring, replacement rule, confirmation lag), time unit, window lists.
6. Formation schedule, eligibility (PIT N100, listing start, burn-in, minimum names per date).
7. Price basis and CA handling: ratio-adjusted as-of-*t* series; the externally enumerated list of
   spin-offs, demergers and special dividends with exclusion windows; scoped substrate certification (R-13).
8. Surrogate specification: bar-vector definition, synchronized stationary bootstrap, mean block
   length 20, missing-bar rule, B = 1999, seed.
9. Placebo sets per construct (GF-1 fractions, GF-4T/R8 shifted windows) and the GF-10 contrast.
10. Statistic, IUT pass rule, α, one-sidedness, and the blind size-calibration procedure and threshold.
11. Screen window 2011-03-25 → 2022-12-30; kill rule and its report wording; confirmatory α pinned at
    0.05/m_entered; prohibition on using screen estimates in any later δ band.
12. Robustness list (off the pass path), declared in full, with **pre-specified diagnostics**:
    price-level strata ([PC37] pp. 11–12), anchor-age strata (GF-1's early "all-time-to-date extremes" are left-censoring artifacts of the
    2011-03-25 data start and listing dates), per-stock heterogeneity, and the realized burn-in
    haircut to n.
13. Report template with the NON-CONFIRMATORY label and the §8.2 limitation statement.
14. Code committed from a clean tree; outputs written by script only.
15. Exposure register row G-S1 appended **by the operator** before the read (GR-1.4).
16. GR-1.5 disclosure text for any later confirmatory pre-registration.

---

## 12. Verdict

**2026-09-15:** the rulings listed below were made. The freeze verdict is now kept in
`PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md`: **NOT READY TO FREEZE**. The original verdict is preserved:

> **NOT READY — unresolved issue(s):** R-1 (K3 is not reproducible as Gann's detector; admissibility
> as a declared approximation), R-2 (outcome scale), R-3 (sense of "extreme"), R-4 (Rule 8
> tolerances inconsistent in Gann's own usage), R-5 (supersede ruling 7 for GF-10), R-6 to R-10
> (construct exclusions and cell pins), R-11 (freshness of 2023-01-02 → 2026-09-11), R-13 (scoped
> substrate certification and CA enumeration), R-14 (surrogate/inference specification).

These are operator rulings, not further research. The supplied primary texts have now been read in
full (*Puts and Calls* closed 2026-09-15, register §29). **No further primary-source reading can close
the rulings above**: the remaining gaps are either undefined in Gann's text or withheld by Gann. Once they are
ruled, the §H freeze can be written and the screen (R-12) considered.

---

## 13. Governance

- No market data, outcome, signal count or incidence read. No backtest, TRAIN/HOLDOUT, fit, tuning or
  RFA declaration. The screen was not run.
- No prior operator ruling changed; every conflict is a recommendation (§11.E).
- 2026-09-15 addendum: operator rulings recorded; ruling 7 superseded by R-5 on the operator's
  instruction. The exposure register was still not edited.
- No family definition modified. The exposure register was not edited (row G-S1 is a draft).
- Nothing here states or implies that any Gann construct has predictive power.
