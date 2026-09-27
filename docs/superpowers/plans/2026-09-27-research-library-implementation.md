# Research Library → Repo: Implementation Plan

**Date:** 2026-09-27
**Branch:** `research/research-library-plan` (from `origin/main` e71c1e9, plus the triage/index commit)
**Inputs:**
- `docs/reports/external/RESEARCH_LIBRARY_TRIAGE_2026-09-26.md` (cited below as T§n)
- `docs/reports/external/RESEARCH_LIBRARY_PAPER_INDEX_2026-09-26.md`

**Status:** operator decisions 2026-09-27: **W2, W3 and W6 APPROVED.** Everything else is still pending, and nothing else is built until approved item by item.

**Standing constraints:**
- no NiftyShield hashed-file change;
- no Nifty index-options backtest over 2016-02-11 → 2022-12-31;
- no dynamic hedge;
- the TS combo book is never re-tuned;
- no closed construct is reopened.

---

## 0. Corrections to the triage found while planning

1. **N200 regime HMM is CLOSED** (`index_research/N200_REGIME_CLOSURE.md`, 2026-09-09: both variants fail the Brier gate).
   - T§8 treated it as live.
   - Its items drop to **(a) explanatory** (Nystrup–Boyd, Rogers–Zhou as possible reasons for the calibration failure) and are **not planned**.
2. **The basis-family evidence is not on `main`.**
   - `BASIS_FAMILY_POST_MORTEM_2026-09-24.md`, `ts_basis/TS_BASIS_FUTURES_TRANSLATION_REVIEW.md` and the Carry translation all live only on the unpushed `research/funnels-filter` branch (commits a2bed7c, 1348792, 9b932f2).
   - Every citation edit to them (W1) and the TS Basis answer (§3) depend on that branch being merged first.
3. **The per-paper index was biased against stock constructs.**
   - The readers' brief listed cash-equity cross-sections as "closed".
   - Many stock papers were therefore marked NONE for that reason, not on their merits: momentum, reversal, lottery/MAX, stat-arb.
   - §4 re-examines them.

---

## 1. Areas touched

| # | Work item | Files touched | Kind | Effect | Risk / guard |
|---|---|---|---|---|---|
| W1 | Citation / wording edits (T§9) | `index_research/NIFTY_BANKNIFTY_PAIR_RESEARCH.md`, `sleeves/IVOL_SEALED_REPORT.md`, `GEX_FLY_B1_REVIEW.md`, `BASIS_FAMILY_POST_MORTEM` *(after merge)*, `ts_basis/TS_BASIS_REAUTHORIZATION_ASSESSMENT.md` §B; **addendum** (not an in-place edit) for `sleeves/TREND_PHASE0_PRE_REGISTRATION.md` | docs | Explains past outcomes with literature mechanisms. "Not cointegrated" becomes "not detected". | None on code. Frozen pre-regs get an addendum, so no digest moves. |
| W2 | **Spot-only bracket study** (T§3.2) | new `scripts/research/nifty_shield_diag/afternoon_variance.py` and report | offline research | Measures the afternoon variance share vs the bracket's assumed 0.40, and the intraday trend term by DayType | Reads 1m `NSE_INDEX\|Nifty 50` 2023+ only. Cut at 15:15 post-CAS; report the eras separately. Changes no rule. |
| W3 | **Next-expiry capture** (T§3.3) | `core/options_wall/poller.py` (l.261 fetches only `get_weekly_expiry`), `core/data/options_wall_store.py` | **live system** | Makes the IV term-structure slope measurable going forward. This is the only item that decays. | See §2. It must go to a **separate table**, because `options_wall_counterfactual/battery.py:74` reads `option_chain_snapshot` with **no expiry filter**, and a second expiry in the same table would silently corrupt it. It roughly doubles fetches per cycle against a store that already holds locks for 3–8 s. It reaches production only after a merge to main and the orchestrator checkout moving to a branch that contains it. |
| W4 | NiftyShield attribution and fixed-structure shadow (T§3.1, §3.4) | new offline `scripts/research/nifty_shield_diag/attribution.py`, `fixed_structure_shadow.py` | offline research | Splits each session's P&L into volatility mispricing, the trend term and the bracket's cost, and credits the DayType/VIX selector against a one-structure book | **Never wired into the runner.** Reads `wall_chain_snapshots/{date}.duckdb` after the fact. Rules pinned in a pre-analysis note before any look. Not read before E008 has enough sessions (roughly 8 years for power 0.80, so telemetry only). |
| W5 | Paper-window evaluation block (T§3.5) | E008 report generator (`scripts/nifty_shield_paper/…` report path; **outside** the `identity.py` hash list, to be confirmed before editing) | report | Skew, kurtosis, CVaR, worst sessions next to Sharpe; states that a crash-free window cannot validate tail risk (Lo 2001: 475 sessions for p = 5%) | Must not touch `strategies/nifty_shield_v1/*`, `core/execution/options/nifty_shield_*`, `fees.py`, `handler.py` or `nifty_shield_paper_runner.py`. |
| W6 | **Straddle `ca_in_hold` split and kinked beta** (T§4) | new `scripts/research/options_seller_edge/ca_filter_split.py` and report; `build_stock_straddles.py` **unchanged** | offline research | Settles whether the dropped cycles are corporate actions or censored crashes, and moves the study off INSUFFICIENT EVIDENCE either way | Accounting on cycles already generated; must not select a new filter. Uses the CA tables from `scripts/csmp/ingest_corporate_actions.py`. |
| W7 | TS combo expectation note (T§6) | new `ts_basis/TS_BASIS_DAILY_FUTURES_EXPECTATION.md` and a b1/b2 script on burned TRAIN/HOLDOUT | offline research | Writes down, **before** forward months arrive, what futures-net P&L can be. Daily futures translation is unmeasured (§3). | The sealed 876-formation window stays unread. The combo book is not touched. |
| W8 | RFA hardening (T§5) | `governance/rfa/declaration.py`, `scripts/rfa/power.py`, `scripts/rfa/gate.py` (`METHODOLOGY_VERSION` 2.0.0 → 2.1.0), tests | governance code | Optional `ic_horizon`/`formation_step` with n_eff deflation, an IC-SD floor of 1/√N, Holm, a trial-ledger doc | New fields **optional**, since frozen declarations are SHA-pinned. **Acceptance:** existing declarations reproduce FLOW 0.6053, RS-MOM 0.337, CB-N50 1.00 and A-INDEX-INTRADAY 0.8720 exactly. |
| W9 | Cost-model sensitivity column (T§7) | `scripts/signal_engine/carry/capacity_analysis.py`, `scripts/signal_engine/ts_basis_daily/run_capacity.py` | report columns | Adds σ·participation^0.6 / square-root impact beside flat κ, which flags thin or volatile names | Report only. No change to the combo book's cost model. |

**Not touched:**
- NiftyShield hashed files;
- the frozen SPAN stack;
- `build_stock_straddles.py`;
- the TS combo book and its facts;
- any `run_sealed.py`;
- the N200 code.

**Order:** W1 → W2 → W3 (decision) → W6 → W7 → W4/W5 (when E008 has sessions) → W8 (with the next declaration) → W9.

---

## 2. W3 in detail — the only live-system change

- **Now:** each cycle fetches the nearest weekly expiry only and appends to `option_chain_snapshot`.
- **Readers:**
  - `options_wall/engine.py` filters on expiry (safe);
  - `nifty_shield/audit_regime_and_structures.py` filters on expiry (safe);
  - `options_seller_edge/cas_pcp_forward.py` groups by expiry (safe);
  - `options_wall_counterfactual/battery.py` does **not** filter (unsafe);
  - `ops/compact_duckdb_stores.py` needs checking.
- **Plan:** one extra fetch per cycle for the next expiry (the first weekly with DTE ≥ 2 and the monthly, per T§3.3's pinned definition), written to a **new table** (`option_chain_snapshot_far`) in the same daily file, or at a slower cadence (e.g. once per minute) to limit locking.
- **Tests:** append and read round-trip; `battery.py` unchanged output on a fixture.
- **Effect on the running system:** none until merged and deployed. The NiftyShield identity doesn't hash the poller (`identity.py` l.25–29), so E008 doesn't restart.

---

## 3. Can TS Basis be redesigned with the papers' findings? — No, and here is why

| Variant | Evidence | Verdict |
|---|---|---|
| TS Basis **monthly** | Futures translation **measured**: futures IC +0.010 (TRAIN) / −0.006 (HOLDOUT). Its pre-written kill rule fired (`TS_BASIS_FUTURES_TRANSLATION_REVIEW.md`, funnels-filter branch). | Dead as a futures construct |
| TS Basis **Daily** / combo | Futures translation **not measured**. Fama–French 1987 predicts the same outcome: basis = expected spot change (b1) + premium (b2), and a futures holder earns only b2. | Unknown; W7 measures b2 on burned data before forward months are read |

- **What the papers say.** A high basis predicts that **spot** rises toward an already-rich futures price. The futures leg earns nothing from that convergence and pays for it. That is the repo's measured −137 bp/month convergence cost.
- **What a "redesign" would be.** Any version that captures the effect trades the **spot** leg:
  - At **daily** cadence it hits delivery STT (0.1% per leg) and the impossibility of shorting cash for more than a day. That is the PSB fee wall.
  - At **monthly** cadence the TS Basis sealed window is spent.
- **Why it isn't a redesign.** Either version is a **new construct**, not a redesign. It needs the operator to lift the 2026-08-01 research-only decision, an RFA declaration and an unread window, and it has nothing to do with the running combo book (never re-tuned).
- **What the library legitimately gives TS Basis:**
  - W7: an expectation before forward data arrives;
  - Clarke–de Silva–Thorley: IC vs transfer-coefficient logging, to tell a dead signal from concentration luck;
  - Lo 2007: timing vs static-drift decomposition;
  - Ready 2002: why the TRAIN-chosen overlays carry about zero forward information.

---

## 4. Do the 370 papers suggest a new stock construct?

**Short answer:** one lead, with three headwinds. No paper describes a stock construct that is both new relative to what this repo has killed and clear of the two walls: fees for cash, and demonstrability plus an unread window.

**The lead: residual ("s-score") reversal on single-stock futures.**
- **Sources:** Avellaneda–Lee 2008 [048] (PCA/sector-residual mean reversion traded daily) and CB-N50's own hand-off (HOLDOUT IC +0.029 on daily constituent reversal, spot target, with a successor L/S constituent book named as the open path).
- **Why it differs from what was killed:**
  - PSB C1/C2 were **cash** reversal (delivery STT).
  - CB-N50 was expressed as **index timing**, which failed.
  - A residual-reversal L/S book on **SSF** pays derivatives fees. Futures STT is 0.02% on the sell side (`core/execution/futures/futures_fees.py`), so the statutory cost is about 3 bp per round trip, plus slippage.
  - A reversal signal is not the basis, so the Carry convergence problem does not apply directly. It must still be measured on futures returns (post-mortem P1).
- **Headwinds** (verified against the summaries and the repo):
  1. **Da–Liu–Schaumburg [102]:** "among residual winners, stocks with options traded show **no** reversal." Every SSF name has listed options, so the short leg of the book is exactly where the literature says reversal disappears.
  2. **Fees at daily turnover.** About 3 bp statutory plus the repo's κ of 5 bp per side is roughly 13 bp per round trip. Back-of-envelope (not an RFA figure): a quintile spread from IC ≈ 0.03 on a cross-sectional σ of about 1.5%/day is on the order of 10–15 bp/day gross. That is **about the same size as the cost at full daily turnover**, so the book would need banding or a slower cadence, which cuts the effect.
  3. **Prior exposure.**
     - Reversal on these names is burned in TRAIN and HOLDOUT (CB-N50 2016–22, PSB C1/C2 2012–22).
     - The SSF 2023+ window has already been read three times on the same universe (post-mortem P8), though with different signals.
     - Whether that window counts as unread for a reversal construct is an **operator decision**.
- **Cheapest honest next step:** an RFA declaration, which reads no data and costs nothing. `rank_ic` on about 180 SSF names daily, with its effect band anchored on the **shrunk** HOLDOUT IC (+0.029, not +0.059) and haircut again for the options-listed short leg. If ABANDON, the lead is closed at zero cost. **Not done, pending the operator's go-ahead.**

**Other stock papers re-examined, and why they remain no:**

| Paper family | Why not |
|---|---|
| Momentum, 12-1 cross-sectional and industry [110–150] | Monthly cross-section fails demonstrability (about 350 formations needed vs about 130 held; F1, PSB-2 C4). Cadence does not help (RFA). |
| Low-vol / BAB / lottery-MAX [009, 053, 066, 069] | IVOL sealed failed. C5 low-vol failed on power. Bali's MAX mechanism is an *explanation* of the IVOL flip, not an unread test. |
| Accruals, asset growth, earnings drift, analyst revision | No fundamentals, announcement or IBES data in the repo. |
| Stock-option signals, filtered writing (Constantinides "good sells") | Skew sleeve failed TRAIN. The stock-option 2023+ window is spent and 2016–22 was the discovery surface. |
| Pairs [037] | The Nifty–BankNifty pair is closed. Stock pairs would be a new construct with the same fee and power arithmetic as reversal above, and a weaker cross-section. |

---

## 5. Decisions needed from the operator

1. Merge `research/funnels-filter` to main? (It unblocks W1 citations and the §3 evidence.)
2. Approve W2 and W6 (offline, cheap, decision-relevant)?
3. W3 next-expiry capture: yes or no (the only decaying item; it touches the live poller)?
4. Write the SSF residual-reversal RFA declaration (§4), or close the lead unexamined?
5. Commit and push this branch?
