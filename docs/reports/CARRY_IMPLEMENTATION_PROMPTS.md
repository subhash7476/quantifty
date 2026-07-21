# Carry Sleeve — Implementation Prompt Pack (for DeepSeek)

**Created:** 2026-07-21
**Parent docs:** `SIGNAL_ENGINE_DESIGN.md` (engine), `CARRY_PHASE0_PRE_REGISTRATION.md` (sleeve #1
pre-reg, DRAFT), `CARRY_SUBSTRATE_CERTIFICATION_SPEC.md` (substrate gate, DRAFT).
**Role split (standing):** DeepSeek implements from these written prompts. Claude writes the
prompts and reviews the output; Claude does not implement gate deliverables.
**Consumes no sealed data.** Nothing in this pack touches 2023-01-01 → present.

---

## 0. Governance note — read before issuing

Both parent docs are **DRAFT**. Issuing P1 (the RFA declaration) is the act that pins §7's
bands: once `governance/rfa/declarations/carry.py` exists and its SHA-256 is recorded, the
delta band `[0.020, 0.045]`, the SD band `[0.10, 0.18]`, `n* = 42`, and the §1 sign
(**short high residual carry** → negative IC) **cannot be revised in response to results**.
That is the point of the gate. Confirm the bands read correctly before P1 goes out.

**Freezing `carry.py` in Wave 1 while the parent pre-reg is still DRAFT is not a
contradiction.** The two OPEN items below touch §3.2 (dividend adjustment) and §4
(neutralization) — *construction*. The RFA declaration pins §1 (sign), §7 (bands), and n* —
and those are deliberately construction-independent: the bands are literature-defended, not
derived from how the basis happens to get built. The two freezes are orthogonal and can
proceed in either order.

---

## 1. Substrate reality check (verified 2026-07-21, not assumed)

Queried directly against the stores. These supersede the parent docs where they disagree.

| Store | Table | Verified state |
|---|---|---|
| `data/market_data/futures_bhavcopy.duckdb` | `futures_bhavcopy` | 1,470,294 rows · 2016-02-11 → 2026-07-20 · 376 underlyings · `inst_type` ∈ {FUTSTK 1,422,979 · FUTIDX 47,315} |
| same | `fo_eligible_intervals` | **UNUSABLE as PIT membership** — 9,092 rows, only 2024-09-02 → 2025-07-18, 235 underlyings |
| same | `stock_futures_continuous` | **Stale F1 artifact** — 2022-08-08 → 2025-07-17, 270 names. Carry must not consume it (see §5, RULE) |
| `data/market_data/stock_options_bhavcopy.duckdb` | `stock_options_bhavcopy` | **98,320,092 rows · 2016-02-11 → 2026-07-20 · 363 underlyings — ingest is COMPLETE** |
| `data/market_data/equity_bhavcopy.duckdb` | `equity_bhavcopy` | raw OHLC + `series`, `deliv_pct` |
| same | `equity_bhavcopy_adjusted` | 7,030,920 rows · 2010-01-04 → **2026-07-09** |
| same | `corporate_actions` | 11,965 rows · 2000-07-26 → 2026-07-31 · DIVIDEND 10,771 / BONUS 603 / SPLIT 591 |
| same | `symbol_entity_intervals`, `symbol_isin`, `symbol_changes` | CSMP entity machinery present — reuse, do not rebuild |

**Doc corrections this implies** (apply when the parents are frozen):
- `SIGNAL_ENGINE_DESIGN.md` §2.1 says the options ingest is in progress through 2024-06-30. It
  is **complete to 2026-07-20 at 98.3m rows**. The Skew sleeve is data-unblocked *now*; the
  3-sleeve path (≈0.75 composite power) is available without further ingest.
- `CARRY_PHASE0_PRE_REGISTRATION.md` §2's "363 stock-futures underlyings" is confirmed (376
  total includes 13 FUTIDX).

---

## 2. Open decisions — operator must resolve BEFORE the pre-reg is frozen

> **SUPERSEDED IN PART by `CARRY_DATA_GAP_AUDIT.md` (2026-07-21).** That audit measured every
> gap below against the live stores. Net changes:
> - **OPEN-1 (dividend PIT) is DOWNGRADED** — measured exposure is **1.55%** of TRAIN+HOLDOUT
>   cells. Option (a) + robustness column, no ingest. Treat as closed.
> - **OPEN-2 (sector) is CONFIRMED blocking and is solvable** — 311/363 names live and
>   downloadable, 52 delisted (**14.8% of cells, concentrated in early TRAIN**) recoverable via
>   entity-map inheritance + BSE scrip master + a small committed register.
> - **NEW BLOCKER G1 — no Nifty 50 daily history before 2023-01-02.** The §4 **beta** leg is
>   uncomputable on TRAIN and HOLDOUT. Free NSE download; must be fixed before P4.
> - The futures↔spot join measured **99.69% complete**, all misses in the known 11-day tail.

Three gaps sit between the pre-reg as written and what the store can actually support. P1–P3
are unblocked regardless; **P4 (signal build) cannot be issued until OPEN-2 and G1 are
resolved**, because both change or block frozen §4 text.

### OPEN-1 — Dividend PIT is not verifiable from the store
Pre-reg §3.2 requires **announced/ex-date-known** dividends with no lookahead; cert spec Arm C
requires certifying `announcement_date ≤ formation_date`. **`corporate_actions` has no
announcement-date column.** Verified payload: `{Ex_date, BCRD (record date), PAYMENT_DATE,
Details (₹/share)}` — the dividend *amount* is available, its *knowability at t* is not.

Options:
- **(a) Recommended — declare the approximation and bound it.** Use ex-date-known-at-*t*
  dividends, disclose it as bounded lookahead, and make "IC without dividend adjustment" a
  **mandatory robustness column** in every Carry report, plus report the fraction of
  name-formations where a dividend ex-date falls between *t* and expiry. If the two IC columns
  agree in sign and the neutralized magnitude moves <20%, the approximation is not load-bearing.
- (b) Drop §3.2 entirely; let dividend yield sit inside the residual. Cheapest, but Indian
  ex-dates cluster Apr–Aug and dividend yield is name-specific, so this injects a known
  seasonal contaminant the cross-sectional demean does not remove.
- (c) Ingest announcement dates (BSE board-meeting / NSE announcements). Real work, uncertain
  historical coverage back to 2016.

### OPEN-2 — No sector classification exists in any store
Pre-reg §4 freezes **sector neutralization**. Searched every store: `instrument_master`,
`nse_fo_instruments`, and all `universe_*` tables carry no sector/industry field. The only
sector data in the repo is `data/market_data/universe_raw/nifty200_current.csv`
(`Company Name, Industry, Symbol, Series, ISIN Code`) — **200 names, current snapshot, not
point-in-time**, and it will not cover the whole F&O universe.

Options:
- **(a) Recommended — ingest a wider NSE industry master (P3b below) and use it as a static,
  non-PIT control**, disclosed. Sector classification is slow-moving and is a *control*, not the
  signal, so a current snapshot is a defensible approximation — but it must be stated in the
  pre-reg, not discovered later.
- (b) Neutralize to beta only; record sector-neutrality as deferred. Contradicts design §4.1's
  "three places cross-sectional books quietly die" and leaves the covert-sector-bet risk open.

**The snapshot problem is worse than "non-PIT" — it is survivorship-shaped.** A *current* NSE
constituent list structurally cannot contain a name that was F&O-eligible in 2016–2020 and is
delisted or dropped today. So UNCLASSIFIED will not be a random residual: it is
**survivorship-correlated and concentrated in early TRAIN**, precisely the oldest and thinnest
part of the sample. That biases the §4 neutralization on the historical windows specifically,
and it should weigh on the (a)/(b) choice — not just on the disclosure wording.

Whichever is chosen, the **UNCLASSIFIED handling must be pre-registered**: names with no sector
map either (i) form their own dummy bucket, or (ii) are dropped from that formation. Pick one
before freeze, not after seeing coverage.

**P3b presupposes OPEN-2(a).** Do not run it until the operator picks (a); under (b) the ingest
is wasted work.

### OPEN-3 — Spot tail is 11 days short of futures
`equity_bhavcopy_adjusted` / `equity_bhavcopy` end **2026-07-09**; futures run to **2026-07-20**.
Immaterial for TRAIN/HOLDOUT; it truncates the *sealed* window's last formation. Either re-run
the equity ingest before the sealed read, or pin the sealed window end at 2026-07-09. Decide at
sealed-read time, not now.

---

## 3. Issue order (gates, not preferences)

```
WAVE 1  (issue now, parallel, independent)
  P1  RFA declaration + gate run          -> pre-reg §9 gate 1
  P2  Substrate certification suite       -> precondition for §9 gate 2
  P3a Futures fee model                   -> needed by §8
  P3b Sector master ingest                -> HELD until operator picks OPEN-2(a); wasted under (b)

WAVE 2  (HELD — do not issue until ALL of:)
  - P2 report shows zero un-dispositioned violations and all three §2 predictions hold
  - OPEN-1 and OPEN-2 resolved by the operator and written into the pre-reg
  - pre-reg FROZEN (SHA-256 recorded)
  P4  Signal build + neutralization + TRAIN read
```

Do **not** hand DeepSeek the whole pack at once. It will run TRAIN before certification passes.

---

## 4. P1 — RFA power pre-check declaration

```
TASK: Create the frozen RFA declaration for the Carry sleeve and run the gate.

CONTEXT YOU MUST READ FIRST (do not skip):
  docs/reports/CARRY_PHASE0_PRE_REGISTRATION.md  -- sections 1, 5, 7, 10
  governance/rfa/declaration.py                  -- the frozen input contract
  scripts/rfa/gate.py                            -- METHODOLOGY_VERSION, corner logic
  governance/rfa/declarations/o1_vrp.py          -- the one existing example (WITHDRAWN,
                                                    but the file shape is correct)

DELIVERABLE 1: governance/rfa/declarations/carry.py

  Construct a single module-level `DECLARATION = Declaration(...)` with EXACTLY these values:

    name                = "CARRY"
    methodology_version = "2.0.0"        # must match scripts/rfa/gate.py METHODOLOGY_VERSION
    metric              = "rank_ic"
    test_type           = "one_sided"
    cadence             = "monthly"
    n_available         = 42
    delta_lo            = 0.020
    delta_hi            = 0.045
    sd_lo               = 0.10
    sd_hi               = 0.18
    window              = the sealed projection window 2023-01-01 -> 2026-07-20, ~42 monthly
                          formations; state that the futures substrate begins 2016-02-11 and
                          NSE F&O history before that is unobtainable (SFB-1/F1 lockdown
                          finding), so n* cannot be raised by pulling more history.

  SIGN -- CRITICAL, do not get this wrong:
    Pre-reg section 1 declares SHORT high residual carry, i.e. the expected realized rank-IC is
    NEGATIVE. The RFA gate treats `delta` as a MAGNITUDE (it evaluates the optimistic corner as
    delta_hi with sd_lo) and the direction lives in `test_type="one_sided"`. Therefore declare
    delta_lo/delta_hi as POSITIVE magnitudes as given above, and state explicitly in
    delta_provenance that the declared direction is negative-signed IC. Do NOT encode a negative
    delta. Do NOT supply sharpe_lo/sharpe_hi/cadence_per_year -- declaration.py rejects the
    rank_ic + Sharpe combination by design (it is the coupled-band defect that withdrew O1).

  delta_provenance  -- write it from pre-reg section 7's table row for delta: cross-sectional
    carry/basis IC in the equity and futures literature (Koijen-Moskowitz-Pedersen-Vrugt 2018;
    Asness-Moskowitz-Pedersen 2013) sits ~0.02-0.05 for a single well-constructed factor;
    residual-basis in Indian SSF defended at the same range, upper end reflecting India's
    stronger borrow-demand dispersion. Include the sign sentence above.

  sd_provenance     -- from the SD row: monthly cross-sectional IC dispersion for a ~150-name
    cross-section is dominated by true time-variation rather than sampling noise; equity-factor
    monthly IC SD is ~0.10-0.18.

  prior_exposure    -- from pre-reg section 10: operator's prior reads are momentum/delivery
    constructs (PSB-1 C1-C5, PSB-2 C2/C4, SFB-1/F1); NONE is a carry/basis construct, so prior
    exposure to this signal is nil. The general demonstrability finding (RFA retrospective) is
    methodological, not a peek at carry's realized numbers, and is already priced into
    pre-reg section 7.1.

DELIVERABLE 2: run the gate and commit its output.
  python -m scripts.rfa.run_rfa carry
  -> writes docs/reports/CARRY_RFA.md . Do not hand-edit that file.

STATE THESE PREDICTIONS IN YOUR REPORT BEFORE YOU RUN (research-script equivalent of a RED
test), then report the actual numbers next to them:
  1. Verdict = PROCEED. Optimistic corner IR = delta_hi/sd_lo = 0.045/0.10 = 0.45;
     ncp = 0.45 * sqrt(42) = 2.92; max_power should land ~0.85-0.92.
  2. Central corner (0.0325 / 0.14) gives IR ~0.232 -> n_required_central on the order of 120+
     monthly formations, i.e. ~10+ years -- far beyond the 42 available. This is the
     standalone-infeasibility that pre-reg section 7.1 already discloses; it is EXPECTED and is
     not a failure.
  3. A PROCEED here means "not provably infeasible" at the single-sleeve level ONLY. It is not
     authorization, and per pre-reg section 7.1 the 0.80 hurdle binds at the COMBINED-engine
     level, not on Carry standalone.

DO NOT:
  - touch scripts/rfa/gate.py, power.py, report.py, or declaration.py (frozen contract v2)
  - adjust any band to make a number come out better -- that inverts the entire gate
  - read any market data (this task reads none)
```

---

## 5. P2 — Carry substrate certification suite

```
TASK: Build and run the four-arm substrate certification for the Carry sleeve. This certifies
that the futures + spot substrate can produce an honest basis. It computes NO signal, NO IC,
NO returns.

CONTEXT YOU MUST READ FIRST (do not skip):
  docs/reports/CARRY_SUBSTRATE_CERTIFICATION_SPEC.md   -- the whole spec; it is the contract
  docs/reports/CARRY_PHASE0_PRE_REGISTRATION.md        -- sections 2, 3, 3.4 (universe, basis, roll)
  scripts/psb1/contract_arms.py                        -- the discipline you are mirroring
  scripts/psb1/certify_substrate.py                    -- runner shape, report generation
  scripts/psb1/disposition_register.py                 -- how exceptions are committed, not patched
  scripts/csmp/build_universe.py                       -- entity machinery: REUSE, do not rebuild

SUBSTRATE FACTS (verified 2026-07-21 -- trust these over any doc):
  data/market_data/futures_bhavcopy.duckdb
    futures_bhavcopy(underlying, expiry_dt, trade_date, inst_type, open, high, low, close,
                     settle, contracts, val_in_lakh, open_int, chg_in_oi, ingested_at)
      1,470,294 rows | 2016-02-11 -> 2026-07-20 | 376 underlyings
      inst_type: FUTSTK (1,422,979) and FUTIDX (47,315). Carry uses FUTSTK only.
    fo_eligible_intervals -- DO NOT USE. Only covers 2024-09-02 -> 2025-07-18 (235 names).
    stock_futures_continuous -- DO NOT USE. Stale F1 artifact (2022-08-08 -> 2025-07-17),
      built with a return-roll convention Carry does not want. Cert spec section 6 is explicit
      that Carry is a LEVEL signal and needs no roll-adjusted return series.
  data/market_data/equity_bhavcopy.duckdb
    equity_bhavcopy(trade_date, symbol, series, open, high, low, close, prev_close, volume,
                    turnover, deliv_qty, deliv_pct)
    equity_bhavcopy_adjusted (same cols, CA-back-adjusted) | 2010-01-04 -> 2026-07-09
    corporate_actions(symbol, ex_date, action_type, purpose_raw, ratio_or_fv, source,
                      scripcode, raw_json)  -- DIVIDEND 10,771 / BONUS 603 / SPLIT 591
    symbol_entity_intervals(symbol, valid_from, valid_to, entity)
    symbol_isin, symbol_changes, trading_calendar

TWO CONSTRUCTION RULES YOU MUST FOLLOW (they are not obvious, and getting them wrong
fabricates the exact defect this suite exists to catch):

  RULE 1 -- RAW spot, not adjusted spot.
    The basis is a SAME-SESSION ratio (F - S)/S. Use the RAW equity close from
    `equity_bhavcopy` (series = 'EQ'), NOT `equity_bhavcopy_adjusted`. Back-adjustment factors
    are a return-series device; pairing a back-adjusted spot leg against a raw futures price
    fabricates a basis on every name that has ever had a corporate action. Both legs must be
    the same session's raw traded close. Arm C then certifies that both legs repriced together
    on ex-dates. Document this choice explicitly in the report.
    If challenged, the one-line defense is: the basis is a SAME-SESSION ratio, so any
    adjustment factor common to both legs cancels; a back-adjusted spot leg is scaled by
    FUTURE CA factors the raw futures price does not carry, which fabricates a basis on every
    name that has any later corporate action. The deliberate consequence -- state it, so it is
    not read as an oversight -- is that Arm B's entity resolution now carries the
    CA-consistency load the adjusted view would otherwise have provided.

  RULE 2 -- PIT F&O eligibility comes from the feed itself.
    `fo_eligible_intervals` cannot serve (10-month coverage). Derive eligibility as ground
    truth: a name is F&O-listed on date d IFF it has at least one FUTSTK record on d in
    futures_bhavcopy. Build this as a derived PIT membership panel. This is survivorship-free
    by construction -- names appear and vanish on their real listing/delisting dates.

  NEAR-MONTH SELECTOR (pre-reg 3.4) -- compute on the fly, do not persist a continuous series:
    For (underlying, trade_date): candidate expiries are those with expiry_dt >= trade_date.
    Near-month = the minimum such expiry, EXCEPT roll to the next expiry once there are <= 3
    TRADING days remaining to the near expiry. Trading days come from the distinct trade_date
    set in futures_bhavcopy (self-consistent calendar). NOTE the asymmetry and honor it:
    the ROLL rule counts TRADING days; the ANNUALIZATION in pre-reg 3.1 uses CALENDAR days
    (365 / days_to_expiry). Guard days_to_expiry >= 1.

DELIVERABLES:
  scripts/signal_engine/carry/contract_arms.py     -- Arm A-D test library
  scripts/signal_engine/carry/certify_substrate.py -- runner: four arms + PIT guard
  scripts/signal_engine/carry/disposition_register.py -- committed special-CA exceptions
  tests/signal_engine/carry/test_contract_arms.py  -- unit tests per arm, on synthetic panels
                                                      that inject each defect class
  docs/reports/CARRY_SUBSTRATE_CERTIFICATION.md    -- SCRIPT-GENERATED. No hand-edited numbers.

ARMS -- implement exactly as spec section 3. Whole panel, entity grain, ZERO structural
pre-filters. A blanket filter that hides violations is the precise blind spot that hid the
equity CA mis-keys; do not add one.

  Arm A -- Contract identity & roll integrity
    - every FUTSTK record resolves to a valid (underlying_entity, expiry) with days_to_expiry
      computed against the ACTUAL NSE expiry calendar (last-Thursday rule + holiday shifts +
      the 2024-25 expiry-day changes -- verify against the dated calendar, do not assume)
    - no duplicate/phantom expiries; no record whose expiry_dt < trade_date
    - the near-month selection yields EXACTLY ONE active contract per (name, date): no gaps,
      no overlaps at the roll seam
    - roll-continuity invariant: at each roll date the traded contract LEVEL jumps (expected),
      but the computed BASIS must be continuous within a stated tolerance (Prediction 2)

  Arm B -- Two-leg entity alignment
    - for each (name, date), futures underlying and spot symbol must resolve to the SAME
      point-in-time entity via symbol_entity_intervals + ISIN issuer-PREFIX linkage
      (prefix, not full-ISIN -- a face-value change re-issues the ISIN serial and full-ISIN
      matching severs a company at exactly the action it must handle)
    - guard all three known failure modes across two feeds: recycled ticker (time-aware
      resolution required; union-find alone is insufficient), re-ISIN on face-value change,
      and symbol rename adopted on DIFFERENT dates by the two feeds
    - on any date where the two feeds disagree on entity identity, the basis must be
      SUPPRESSED and counted, never silently computed

  Arm C -- Corporate-action consistency across legs

    SPLITS/BONUSES vs DIVIDENDS BEHAVE DIFFERENTLY. The cert spec (still DRAFT) states
    Prediction 3 as one rule for both; that is WRONG and this prompt corrects it. Work the
    algebra yourself before you write the test:
      * Split/bonus ratio k hits BOTH legs on ex-date: S -> S/k and F -> F/k, so the ratio
        (F - S)/S is INVARIANT. Basis continuity is the correct zero-tolerance test here, and
        a jump genuinely means one-sided adjustment.
      * A discrete dividend D drops SPOT ONLY on ex-date (S -> S - D). The future barely moves,
        because it already priced D out; it changes only by ~D*r*tau, second order. So the raw
        annualized basis LEGITIMATELY STEPS UP by approximately D / (S * tau) on ex-dividend
        dates. For a 1% dividend one month from expiry (tau ~ 1/12) that is a ~12% annualized
        step ON CLEAN DATA. Lump-sum high-yield PSU names are larger still.

    Therefore:
    - splits/bonuses: certify the ratio is applied to BOTH legs on the SAME date; assert basis
      continuity within tolerance across the ex-date (Prediction 3a)
    - dividends: DO NOT run the continuity test on the raw basis -- it would false-flag every
      dividend payer, and the resulting "dispositioned" pile would then HIDE a genuine one-sided
      error on a dividend date. Instead test the RESIDUAL after subtracting the predicted step:
      compute the expected jump D / (S * tau) using the per-share amount available in
      corporate_actions.raw_json `Details`, and flag only the part that does not match within a
      stated tolerance (Prediction 3b). Equivalently, run the continuity test on the
      DIVIDEND-ADJUSTED basis. State which form you used and why.
    - dividend PIT-ness: SEE THE LIMITATION BELOW. Certify what is checkable, REPORT what is not
    - special CAs (demerger, scheme, contract reconstitution): dispositioned in the committed
      register, never hand-patched

    KNOWN LIMITATION -- report it, do not paper over it: spec section 3 Arm C asks you to
    certify announcement_date <= formation_date. `corporate_actions` HAS NO ANNOUNCEMENT DATE
    COLUMN (verified: raw_json carries Ex_date, BCRD record date, PAYMENT_DATE, and the
    per-share amount, and nothing else). So dividend PIT-ness is NOT certifiable from this
    store. Your report must state this as an open substrate limitation and quantify its
    exposure: the fraction of (name, formation) cells where a dividend ex-date falls between
    the formation date and the near-month expiry. Do not invent a proxy announcement date.

  Arm D -- Basis fabrication invariant
    - compute the annualized raw_basis panel; flag every |annualized basis| beyond a
      pre-set, economically defensible bound (state the bound and its justification BEFORE
      running; hard-to-borrow names legitimately run rich, so make it generous but finite)
    - every flagged cell is either (a) traced to a real illiquidity/borrow event -> kept and
      tagged, or (b) traced to a data defect -> repaired. NO flagged cell is dropped by a
      blanket filter
    - staleness: F and S for a (name, date) must come from the SAME trading session close.
      Certify no cell mixes sessions (no carry-forward of one leg against a fresh other leg)

  PIT universe guard (spec section 4)
    - certify no name contributes a basis on a date it was not F&O-listed (per RULE 2)
    - the pre-reg section 2 liquidity/ADV screen is NOT applied here -- it is a construction
      choice at formation time, and applying it in certification would mask defects

FALSIFIABLE PREDICTIONS -- write these into the report BEFORE the run, then report actuals:
  1. Cross-sectional resid_carry is near-symmetric around zero each day; tails bounded by the
     Arm D cap. Systematic skew or one-sided fat tails on specific dates flags one-sided CA
     adjustment.
  2. Basis does NOT jump discontinuously on roll dates.
  3a. Basis does NOT jump on ex-SPLIT / ex-BONUS dates (the ratio cancels in (F-S)/S).
  3b. On ex-DIVIDEND dates the basis DOES step up by approximately D/(S*tau) -- that is clean
      data, not a defect. The prediction is that the RESIDUAL after removing that predicted
      step is within tolerance. A name whose ex-dividend basis does NOT step is as suspicious
      as one that steps too far; report both directions.
  If any prediction fails on the raw substrate, REPAIR the defect (validate-then-apply,
  copy-first, one committed runner per repair, mirroring scripts/psb1/repair_*.py). Do not
  explain the numbers away.

DO NOT:
  - compute any rank-IC, forward return, quintile spread, or portfolio -- that is P4 and it is
    gated behind this report
  - read any data dated 2023-01-01 or later beyond what the panel-wide structural arms require;
    this suite is structural, and the sealed window's SIGNAL must stay unread
  - mutate any raw store. Copy-first, always
  - add abstraction layers. Reuse the CSMP entity machinery as-is (CLAUDE.md: no speculative
    generality)

ACCEPTANCE: the report shows each arm's violation count, the three prediction outcomes, the
Arm D bound and its justification, the dividend-PIT limitation with its quantified exposure,
and zero UN-DISPOSITIONED violations. Anything else is a FAIL and the Carry TRAIN read stays
blocked (pre-reg section 9 gate 2).
```

---

## 6. P3 — Fee model + sector master (two independent sub-tasks)

```
TASK 3a: Implement the era-accurate NSE single-stock-futures fee model.

CONTEXT YOU MUST READ FIRST:
  core/execution/equity/delivery_fees.py            -- the discipline you are mirroring exactly
  docs/reports/CARRY_PHASE0_PRE_REGISTRATION.md     -- section 8

DELIVERABLE: core/execution/futures/futures_fees.py
             tests/signal_engine/carry/test_futures_fees.py

  Components, era-dated: brokerage (flat per order / per lot), futures STT (SELL-SIDE ONLY),
  exchange transaction charge, SEBI turnover fee, GST on (brokerage + txn charge), stamp duty
  (BUY-SIDE ONLY).

  Futures STT schedule (sell-side) -- pre-reg section 8 pins these, and you MUST verify each
  tier against the dated NSE/CBDT circular and cite it in a comment. Report any discrepancy
  rather than silently adopting the pinned value:
    0.0100%  through 2023-03-31
    0.0125%  2023-04-01 -> 2024-09-30   (Finance Act 2023, +25%)
    0.0200%  from 2024-10-01            (Oct-2024 derivatives-STT revision)

  Also verify and date the exchange transaction charge and SEBI turnover fee tiers over
  2016-2026 -- both changed within the window. Do not use a single flat rate across 10 years.

  Tests must pin at least one worked round-trip per STT era with hand-computed expected values,
  and assert the sell-side/buy-side asymmetry (STT sell-only, stamp buy-only).

  CONTEXT FOR WHY THIS MATTERS: delivery-equity STT (0.1% PER LEG) killed every PSB cash
  construct. Futures fees are materially lower -- but pre-reg section 8 is explicit that this
  sleeve is NOT assumed fee-safe by construction and must demonstrate net > 0. Build the model
  honestly; do not round in the strategy's favour.

DO NOT: touch core/execution/equity/delivery_fees.py. Do not build a shared fee abstraction
across equity and futures -- two concrete models, no speculative generality.
```

```
TASK 3b: Ingest an NSE industry/sector master for the F&O universe.

WHY: pre-reg section 4 freezes SECTOR neutralization, and no sector field exists anywhere in
the stores (verified: instrument_master, nse_fo_instruments, and all universe_* tables carry
none). The only sector data in the repo is data/market_data/universe_raw/nifty200_current.csv
(Company Name, Industry, Symbol, Series, ISIN Code) -- 200 names, current snapshot.

DELIVERABLE: scripts/signal_engine/carry/ingest_sector_master.py
  - source NSE industry classification covering the FULL F&O universe (the ~363 FUTSTK
    underlyings in futures_bhavcopy), not just NIFTY-200. NSE publishes index-constituent CSVs
    carrying an `Industry` column (e.g. the Nifty Total Market / Nifty 500 constituent lists);
    verify the URL resolves before relying on it, and fall back to the committed
    nifty200_current.csv only for names the wider list misses
  - write to a `sector_master(symbol, industry, source, snapshot_date)` table
  - key by symbol AND resolve to entity via the CSMP entity machinery, so renamed/recycled
    tickers map correctly
  - REPORT COVERAGE: how many of the 363 FUTSTK underlyings map to an industry, and list every
    unmapped name explicitly. Do not silently bucket misses.

MANDATORY DISCLOSURE in your report: this is a CURRENT snapshot, therefore a NON-PIT control.
That is a deliberate approximation -- sector membership is slow-moving and is used only as a
neutralization control, never as the signal -- but it must be recorded, not glossed. State it.

DO NOT decide the UNCLASSIFIED rule yourself (own dummy bucket vs. drop from formation). That
is a pre-registration decision for the operator. Report coverage; let the operator pin the rule.
```

---

## 7. P4 — Signal build + TRAIN read (**HELD — do not issue yet**)

Blocked on all four of: P2 certification PASS · OPEN-1 resolved · OPEN-2 resolved · pre-reg
frozen with SHA-256. When issued it must cover: `build_carry.py` (§3.1–3.4 basis → dividend
adjustment → cross-sectional demean → winsorize ±3SD → z-score), `neutralize.py` (§4 single
cross-sectional OLS on beta + sector dummies), `run_train.py` (§9 TRAIN 2016-03-31 → 2020-12-31,
~58 monthly formations) → `CARRY_TRAIN_REPORT.md`, with the §11 predictions stated first, the
AC₁-corrected t, the realized-IC-SD-vs-declared-band check (SD > 0.18 stops the sleeve — the C2
wide-SD failure), and the net quintile spread under P3a fees.

**HOLDOUT is a separate later prompt.** Pre-reg §9 gate 3 requires that no parameter is touched
between TRAIN and HOLDOUT — bundling them into one prompt invites exactly the tuning the gate
forbids.

---

## 8. Review checkpoints (Claude)

Each returned deliverable is reviewed before the next wave: P1 against `declaration.py`'s
contract and the sign convention; P2 against the spec's four arms and the no-blanket-filter
rule; P3a against the dated circulars; P3b against coverage honesty. Findings go to
`docs/reports/CARRY_*_REVIEW.md`.
