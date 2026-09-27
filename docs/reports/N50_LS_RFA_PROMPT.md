# DeepSeek Implementation Prompt — N50-LS RFA Gate

**Role:** You (DeepSeek V4) implement; Claude reviews the verdict. This task is
the **RFA gate for the N50-LS construct** — it runs *before* any build and **may
return ABANDON**, in which case N50-LS stops here. Do not build anything.

**Read first (in order):**
1. `docs/reports/N50_LS_PRE_REGISTRATION.md` — the frozen construct spec.
2. `governance/rfa/declarations/rs_mom.py` — the **structural template** (a
   `per_trade_pnl` declaration; ABANDONED). Use its field set and provenance
   rigor. Do **not** use `cb_n50.py` as the template — that is `rank_ic`.
3. `scripts/rfa/power.py`, `scripts/rfa/gate.py`, `governance/rfa/declaration.py`
   — the gate mechanics and the input contract (`METHODOLOGY_VERSION` 2.0.0).
4. CLAUDE.md → RFA section (esp. the O1 withdrawal — the crossed-corner failure
   you must not repeat).

---

## Task

Write `governance/rfa/declarations/n50_ls.py`, freeze it, run the gate, and
report. Nothing else. **No signal code, no build, no data read beyond counting
formations for `n_available`.**

### 1. Declaration fields (per_trade_pnl)

```
Declaration(
    name="N50-LS",
    methodology_version="2.0.0",
    metric="per_trade_pnl",
    test_type="two_sided",        # match the pre-reg §2.2. If you believe
                                  # one_sided is better justified (pinned sign),
                                  # FLAG it for review — do not silently change.
    cadence="daily",
    cadence_per_year=252,
    n_available=<VERIFY>,         # see §2
    sharpe_lo=<DERIVE>,           # see §3 — the integrity core
    sharpe_hi=<DERIVE>,
    sharpe_provenance="...",      # the full derivation, see §3
    prior_exposure="...",         # see §4
    window="...",                 # see §4
)
```

### 2. `n_available` — verify, do not assume

`n_available` is the number of **daily book formations in the SEALED window
2023-01-01 → 2026-07-xx** (match CB-N50's sealed end date). This is the count of
trading days on which the N50-LS book would be scorable (≥30 Nifty 50
constituents with usable inputs), NOT a signal or return read. CB-N50 reported
**887** daily formations on the same Nifty 50 daily universe/window — verify this
count against `nifty50_pit_membership.json` (one-month-lagged) + the trading
calendar and reuse it if identical; document the number you used and how you got
it. Counting formations is permitted; reading the book's P&L on the sealed window
is **not**.

### 3. The Sharpe band — derive and defend, freeze BEFORE the gate

This is the whole gate. The optimistic corner (`sharpe_hi`) is what the gate
tests, so it decides PROCEED vs ABANDON. Get it honest.

**Method (Grinold-Kahn, `IR_annual = IC × √BR`):**
- **Anchor on the HOLDOUT IC = +0.029** (`CB_N50_HOLDOUT_RESULTS.json`). **Not**
  the TRAIN +0.059 — that is selection-inflated by the lookback/feature-drop
  choices (the C2 lesson: defend the effect size, don't inherit the largest
  in-sample read). Treat +0.029 as already possibly optimistic.
- State the **effective breadth assumption explicitly**: BR = N_eff × 252, where
  N_eff is the number of *independent* daily bets. Bound it: N_eff = 1 (each day
  one bet → IR ≈ 0.46) is the floor; N_eff ≈ full quintile count with sector/factor
  correlation removed is the ceiling. Sector/factor correlation makes the true
  N_eff far below the raw position count — say so and justify your central value.
- **Literature anchor:** liquid single-name daily cross-sectional L/S
  (reversal + carry/basis) realise annualised Sharpe ~0.5–1.5 gross, lower net of
  the SSF cost/turnover. Cite it the way `rs_mom.py` cites Moskowitz/Asness.
- Set `sharpe_lo` and `sharpe_hi` to span your honest floor and ceiling.

**Hard integrity rules (these are the O1-withdrawal lesson):**
- **Do NOT reverse-engineer the band from the ~1.47 threshold.** For power 0.80
  two-sided at α=0.05, `ncp≈2.8` and `√T≈1.9`, so ~1.47 annualised Sharpe is
  roughly the PROCEED line. You are forbidden to pick `sharpe_hi` because it
  clears — pick it because it is defensible, then let the gate rule.
- The band is **frozen before you run the gate** and **must not be revised after
  seeing the output.** If the honest ceiling does not clear, the verdict is
  **ABANDON**, and you report it as ABANDON — do not touch the band.
- No crossed corner: `per_trade_pnl` takes a single Sharpe band, not separate
  mean/sd — the contract enforces this; do not attempt to smuggle in a second
  free parameter.

### 4. Provenance, prior exposure, window (prose fields)

- `sharpe_provenance`: the full §3 derivation — anchor IC, breadth assumption with
  its justification, literature, and the explicit statement that it is not derived
  from an in-sample book read and not reverse-engineered from the threshold.
- `prior_exposure`: CB-N50 TRAIN/HOLDOUT (same features + universe, ranking IC
  read on 2016-19 and 2020-22); TS-Basis monthly (spent sealed 2026-07-24) and
  TS-Basis Daily (selection-burned TRAIN/HOLDOUT); Carry (residual-basis IC). State
  plainly that **the Nifty 50 long-short book P&L has never been read on any
  window.**
- `window`: TRAIN 2016-02–2019 and HOLDOUT 2020-2022 are prior-exposed (not clean
  gates); SEALED 2023-2026 (~887 daily formations, ~3.5 yr) is the single clean
  one-shot; SSF history cannot predate 2016 so the calendar is fixed.

### 5. Freeze + run + report

1. Freeze `n50_ls.py` exactly as `rs_mom.py`/`cb_n50.py` were: compute the
   SHA-256 over the declaration and record it in the line-1 header comment.
2. Run the gate (`scripts/rfa/run_rfa.py` for N50-LS) → PROCEED or ABANDON.
3. Write `docs/reports/N50_LS_RFA.md` (model on `CB_N50_RFA.md` / `RS_MOM_RFA.md`):
   verdict, max achievable power, `n_required` at optimistic/central/pessimistic,
   `n_available`, `ncp`, the full Sharpe-band derivation, and the SHA.
4. Update the **Status** line of `N50_LS_PRE_REGISTRATION.md` to record the
   verdict (RFA PROCEED or ABANDON) + the declaration SHA.

### 6. Stop conditions

- **ABANDON** → stop. Record the kill in the report. **No build, no signal code,
  sealed window untouched.** This is a valid, cheap outcome — report it plainly.
- **PROCEED** → stop and **hand back for review before any build.** PROCEED means
  "not provably infeasible," not authorisation to build. Claude reviews the
  declaration + verdict; the build phase is a separate authorised step.

---

## Guardrails (do not violate)

- The RFA is **data-free** except counting `n_available` formations. Do not read
  the book's returns/P&L on any window, least of all SEALED.
- Do not write any N50-LS signal, book, or backtest code in this task.
- Do not tune the Sharpe band to the threshold; do not revise it post-gate.
- Do not add N50-LS to CLAUDE.md yet — it is a DRAFT pending this verdict.
- Report back; do not proceed past the verdict.
