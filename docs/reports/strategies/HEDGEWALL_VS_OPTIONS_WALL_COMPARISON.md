# Hedgewall vs. Options Wall — Site Walkthrough and Emulation Assessment

**Date:** 2026-09-02
**Source explored:** https://hedgewall.in (landing `#method`, `/guide`, `/read-the-terminal/`, `/terminal/` login wall)
**Ours:** `/options/wall/` — `flask_app/blueprints/options_wall.py`, `templates/options_wall/index.html`, `core/options_wall/*`, `core/analytics/chain_scanner.py`, `core/analytics/options_analytics.py`
**Prior artifact:** `OPTIONS_WALL_FEASIBILITY_REPORT.md` (2026-08-12) inventoried Hedgewall once already. This document supersedes its feature table — Hedgewall has since published a 39-value glossary with formulas and thresholds, which lets us compare construction, not just labels.

---

## 1. What Hedgewall is

A subscription **dealer-positioning terminal** for NIFTY, SENSEX and BANKNIFTY index options. ₹4,999/mo (₹133–166/day), access by request, login-walled terminal (Next.js app; the landing page is illustrative data only). It sells one thing: *"given what is written on the option chain right now, what does the dealer have to do next?"*

It is explicitly **not** a signal service. Every panel carries a "BE HONEST" caveat, the guide's §11 is titled "What this cannot tell you", and the terminal is positioned as context for discretionary traders (testimonials: breakout trader, option seller, prop desk sizing expiry risk off the put wall).

### 1.1 The method (landing `#method`)
Three sentences:
1. **Map the hedging** — gamma density per strike from the full chain, weighted by OI.
2. **Find the levels that hold** — pin, flip, call wall, put wall recomputed every tick.
3. **Know the regime** — sign of net dealer gamma, live.

### 1.2 How it actually works (from `/guide` and `/read-the-terminal/`)

**Dealer-side inference (the load-bearing piece).** The exchange does not publish who is long/short. Hedgewall infers the dealer side *per strike* from a four-case grid of (ΔOI up/down) × (option price up/down):

| | OI up | OI down |
|---|---|---|
| **Price up** | New buyers → dealer short | Sellers closing (buying back) |
| **Price down** | New sellers → dealer long | Buyers closing |

Strikes where neither moved enough are left blank rather than guessed. They also detect the "quiet-day" failure mode where theta makes every option cheaper simultaneously and the price-side test measures the clock — and flag it instead of showing a confident answer. *Every gamma number is built on top of this per-strike reading.*

**Net GEX (₹ crore).** Per-strike gamma × OI × contract multiplier × **spot²**, signed by the inferred dealer side, summed over the expiry. Regime buckets: > +1,000 Cr strongly positive; −100 to +100 Cr *Neutral* (explicitly "gamma is not today's story"); < −1,000 Cr strongly negative.

**Flip.** Interpolated strike where the cumulative net-gamma profile changes sign. Read as *headroom* (spot-to-flip distance); within 0.25% = "regime boundary in play".

**Pin.** Argmax of a gamma-weighted per-strike score (call + put gamma exposure). Never shown alone — always with:
- **Conviction (0–100)**: normalised lead of the top candidate over the candidate distribution. ≥70 LOCKED, 30–69 CONTESTED, <30 DRIFTING ("a label on a flat distribution").
- **Margin**: top score − runner-up score (score points). >25 decisive, 10–25 workable, <10 tie.
- **Runner-up** strike, **GEX at pin** (₹ Cr, "is it heavy?"), **Boost** (expiry-day factor).
- Distance-to-pin banding: <0.1% engaged, 0.1–0.5% nearby, >0.5% "map feature, not a force".

**Concentration (HHI).** Herfindahl index of per-strike shares of total |gamma|; also split HHI-call / HHI-put. Bands 0.25+ COMPRESSED, 0.10–0.25 BALANCED, <0.10 DISPERSED. Plus **Percentile** of today's HHI against stored session history, **Δ1D HHI**, **Δ vs rolling mean**. In their reading order this is a **gate**: "a smeared board ends the read before you look at a single strike."

**Two kinds of wall.** Gamma walls (**Ceiling / Floor** = strike with max call-side / put-side gamma exposure) and OI walls (**Call Wall / Put Wall** = max call / put OI). Shown separately because they often sit at different strikes and mean different things (far-OTM call OI is income-writing, "real but slow").

**Sigma.** ATM IV scaled to time-to-expiry, in index points — the yardstick every distance is divided by. "A level 200 points away when sigma is 612 is not a level."

**OI tab.** Max pain, ATM pin overlaid on the OI ladder, total OI, **day ΔOI vs 09:15**, call/put OI shares, vol/OI turnover, PCR (trend only).

**Forward-looking views (§7 of the basics guide).** Three "what must the dealer do next" panels: the **hedge ladder** (forced futures buy/sell at ±0.5/1.0/1.5% — look for the level where size jumps), the **time view** (charm — same GEX is a stronger force at 0 DTE), and the **fear view** (vanna — what a sudden IV drop does to the regime; "a day that only stays calm at exactly today's option prices is a fragile day").

**IV.** Front vs back ATM IV, term slope, 25Δ skew, plus a rotating strike×expiry surface on the landing page. The **IV tab in the guide is marked "SOON"** — the surface visual exists but the value-level docs do not yet.

**Regime river.** 30-session net dealer gamma river crossing zero, price as a pale thread. **Session replay** of any day. **Alerts** on flip crosses and wall breaks.

**The reading order (their method, verbatim intent):** 1) sign of the day, 2) headroom to flip, 3) concentration gate — *stop if smeared*, 4) edges in sigma units, 5) pin vs max pain agreement, 6) fresh vs leftover board (ΔOI since open, vol/OI), 7) what breaks the read (time, repricing).

---

## 2. What our Options Wall page is

A **scanner**, not a terminal. It reads the newest wall-store chain snapshot, computes the structural snapshot, runs three screens, and shows the ranked "farm list" with a gate strip explaining why the premium-farm screen did or did not fire. Nifty + BankNifty, Tuesday/Wednesday weeklies, one expiry each.

### 2.1 What the page renders (`templates/options_wall/index.html`, 812 lines)
- Index tabs (Nifty / BankNifty), snapshot spot + timestamp, "Scan now" (POST `api/refresh` → background `scan_and_persist`).
- **Regime band**: regime, net gamma, flip, pin, put wall, call wall, ATM IV, RV.
- **Gamma-by-strike SVG ladder** with spot / pin / flip / wall overlays.
- **Premium-farm gate strip**: the five `_farm_screen` conditions with reading vs threshold (regime contains "Positive"; spot within ±0.5% of pin; ATM IV − RV ≥ 2.0 pt; quote spread ≤ 5%; ATM CE+PE credit > 0) and a PASS/BLOCKED verdict.
- **Farm list cards** filterable by screen (`premium_farm` / `imperfection` / `laggard`), sortable, with a slide-in detail panel (checks + 4-leg iron-fly table with bid/ask/mid).
- **Regime river**: last 30 persisted sessions as a table + strip (date, regime, pin, flip, walls, ATM IV, RV).

### 2.2 What the analytics compute (`options_analytics.py`, `chain_scanner.py`)
- GEX = Σ gamma × OI × lot, **CE positive / PE negative by fixed assumption** (no spot² scaling, no per-strike dealer-side inference). Regime = sign only, no neutral band.
- Flip = zero-crossing of cumulative gamma (same idea as theirs).
- Pin = argmax of `gamma_by_strike`; `pin_conviction` = |gamma at pin| / Σ|gamma| (a share, not a lead-over-runner-up).
- Walls = **OI-max** only (`resistance_strike` / `support_strike`). No gamma-side ceiling/floor.
- PCR, max pain, OI buildup patterns (long/short buildup, unwinding, covering).
- Realized vol from 1m bars (their sigma is IV-implied; we compare IV to *realized* — a different and arguably more useful axis for a seller).
- Screens: premium farm (iron fly at ATM), vol outliers vs neighbours, CE/PE IV asymmetry, charm cascade (top-5 |theta| at DTE ≤ 2), flip-cross laggard.
- Paper executor: one ATM fly per index, TP +50% / SL −2× / regime-flip / time-stop.

### 2.3 Current data state (checked 2026-09-02)
| Store | State |
|---|---|
| `wall_chain_snapshots.duckdb` | 1.69M rows, **2026-08-14 → 2026-08-20 only** (4 sessions, ~2,970 snapshots per index, 99.9% quoted, gamma present on all rows). Poller heartbeat last wrote 08-20 15:30. **Not running.** |
| `wall_scan_results.duckdb` | 101 scan rows (85 vol_outlier, 6 iv_asymmetry, 10 charm_cascade, **0 premium_farm**), 17 regime rows to 08-27, **1 paper trade** (08-17, exited on regime_flip, −₹872 net). |
| `chain_cache.duckdb` | NiftyShield's single-snapshot poller, live today (Nifty only). |

The regime river the page draws therefore has 17 rows across 13 days, and Hedgewall's "percentile vs history" style readings would be meaningless on it — their own caveat ("a short series makes every day look extreme") applies to us more than to them.

---

## 3. Side-by-side

| Capability | Hedgewall | Ours | Gap |
|---|---|---|---|
| Universe | NIFTY, SENSEX, BANKNIFTY; 0DTE and weekly chains separated; multi-expiry | NIFTY, BANKNIFTY; one weekly expiry each | SENSEX needs BSE feed (Upstox supports `BSE_INDEX|SENSEX`); multi-expiry needs `get_available_expiries` wired into the poller |
| Net GEX | gamma×OI×mult×spot², **inferred** dealer side, ₹ Cr, neutral band ±100 Cr | gamma×OI×lot, **assumed** side, raw units, sign-only regime | Formula + inference + units |
| Dealer-side inference | 4-case ΔOI×Δprice grid per strike, blank when ambiguous, theta-drift detector | None (`analyze_oi_changes` has the 4 patterns but they are not fed into GEX sign) | **Biggest analytical gap** — we already have the two inputs and the classifier; they are just not connected |
| Flip | Interpolated zero-crossing, headroom banding | Same construction | Presentation only |
| Pin | Gamma-weighted argmax + conviction (lead over distribution) + margin + runner-up + GEX-at-pin + boost | Argmax + share-of-book | Conviction/margin/runner-up are a few lines each on `gamma_by_strike` |
| Concentration | HHI, HHI-call, HHI-put, percentile vs history, Δ1D, Δ vs mean; used as a **gate** | None | HHI is `Σ share²` over the dict we already hold; history needs a persisted series |
| Walls | Gamma ceiling/floor **and** OI call/put wall, shown separately; wall holding/thinning/rolled across snapshots | OI walls only | Gamma walls = argmax of CE / PE side of `gamma_by_strike`; "rolled" needs snapshot-to-snapshot diff (we have 5s snapshots) |
| Sigma yardstick | ATM IV × √(TTE) in index points; all distances read in sigma | RV vs ATM IV gap (different purpose) | Add sigma; keep IV−RV — ours is the seller's edge metric, theirs is the distance metric |
| OI since open | Day ΔOI vs 09:15 per strike, added/unwound ladder, vol/OI | `oi_baseline` table exists (09:15 capture); **no screen or UI consumes it** | Wiring, not new data |
| Max pain vs pin agreement | Explicit panel | Both computed, not juxtaposed | UI |
| Vanna / charm | Full layers with expiry clock; "fear view" (regime under an IV shock) | Charm cascade screen (theta-ranked, DTE ≤ 2) only; no vanna | Needs a BS second-order Greeks module (Upstox gives 1st order only) |
| Hedge ladder | Forced futures flow at ±0.5/1.0/1.5%, linear at current gamma | None | Σ gamma × OI × mult × Δspot per bucket — cheap given `gamma_by_strike` |
| IV term structure / surface / skew | Front/back ATM IV, term slope, 25Δ skew, 3-D surface | ATM IV only; CE−PE asymmetry | Needs multi-expiry snapshots (provider supports it) |
| Regime river | 30 sessions, live | 30-session table + strip; **17 rows exist** | Data accumulation, not code |
| Session replay | Any session | None — but the append-only store is exactly the substrate for it | Replay reader + scrubber UI |
| Alerts | Flip cross, wall break | None | Poller-side check + Telegram (ops already has a Telegram path) |
| Guide / per-value glossary with thresholds and caveats | 39 values, each with COMPUTED / HOW TO READ / SCALE / CAVEAT | Gate strip explains the 5 farm conditions | Documentation |
| Trade surfacing | **None** — deliberately | Ranked farm list + paper iron-fly executor | We do something they don't; whether it is worth anything is unmeasured (0 farm rows in 13 days) |

**Honest summary of coverage:** we have the same *skeleton* (chain → gamma by strike → flip / pin / walls / regime → 30-session persistence) and one thing they do not (a scanner and paper executor). We are missing the layer that makes their numbers *trustworthy to read*: dealer-side inference, concentration gating, conviction/margin, sigma-scaling, and the forward-looking vanna/charm/ladder views.

---

## 4. Can we emulate it?

**Yes, as an analytics terminal — most of it is arithmetic on data we already collect.** The wall store carries gamma on every row, bid/ask on 99.9%, OI, IV, and 5-second cadence. The blockers are not data access; they are (a) the poller is not running so there is no history, and (b) the analytics are one layer shallower than theirs.

### 4.1 Cheap (hours each, no new data) — **BUILT 2026-09-02**
All six items below are implemented (tests: `tests/analytics/test_dealer_side_gex.py`,
`tests/analytics/test_wall_metrics.py`, plus engine / persistence / poller / store additions;
122 green across the wall suites). Record of what was built: `OPTIONS_WALL_PROJECT_COURSE.md`
Phase 5. Poller restarted the same day; history accrues from 2026-09-02.
1. **Dealer-side inference.** Feed `_identify_pattern(oi_change, price_change_pct)` into `calculate_gex` so the sign per strike comes from the OI×price grid, blank-out ambiguous strikes, and add the theta-drift guard (if >N% of strikes read "price down, OI flat" → mark unreliable). This is their whole moat and we have both inputs.
2. **GEX in ₹ Cr with spot².** One-line formula change plus a display unit. Makes the regime comparable to their ±100 Cr neutral band instead of sign-only.
3. **HHI (total/call/put), pin conviction as lead-over-distribution, margin, runner-up, GEX-at-pin, gamma ceiling/floor.** All functions of `gamma_by_strike`. Add to `session_regime` so the river carries them.
4. **Sigma** = ATM IV × √(TTE/252) × spot; show every level's distance in sigma on the gate strip and ladder.
5. **Hedge ladder** — Σ over strikes of dealer gamma × Δspot at ±0.5/1.0/1.5%.
6. **Wire the 09:15 `oi_baseline`** into an "OI since open" ladder (added/unwound per strike) and vol/OI.

### 4.2 Medium (days)
7. **Multi-expiry snapshots** → front/back ATM IV, term slope, 25Δ skew. Provider already exposes `get_available_expiries`; poller and store need an expiry dimension per cycle.
8. **Vanna / charm** via a Black-Scholes second-order module (we have IV, spot, strike, TTE, rate). Then the "fear view" (recompute net GEX under IV ±X) and the DTE-scaled "time view".
9. **Session replay** — reader over `wall_chain_snapshots` + a time scrubber on the existing page; the store is already append-only for exactly this reason.
10. **Alerts** — poller-side flip-cross / wall-break detection to Telegram.

### 4.3 Not emulatable by code
11. **History.** Their percentile and "Δ vs mean" readings need months of sessions. We have 4 sessions of chain snapshots and 13 of regime rows. The only fix is to **keep the wall poller running every session** — the runbook exists, the heartbeat shows it stopped on 2026-08-20.
12. **SENSEX** — new underlying, new expiry calendar, BSE lot sizes; feasible but it is a new ingest, not an analytics change.

### 4.4 What not to copy
- Hedgewall makes no P&L claim and gates nothing statistically; that is consistent with its product. Our repo's rule (RFA before construct code) still applies to anything that turns these readings into a *strategy*. `DW1_DEALER_WALL_PRE_REGISTRATION.md` v2 already computed that a single-index `per_trade_pnl` construct on these levels projects power ≈ 0.31 → ABANDON. Emulating the **terminal** is unaffected by that; emulating a **trade rule** is not.
- Their conviction / HHI / neutral-band thresholds are "the engine's own" (their words). Copy the *construction*, then set our bands from our own accumulated distribution, not from their illustrative numbers.

---

## 5. Recommendation

Treat the Options Wall page as what it already is — a research instrument — and close the trust gap in the order Hedgewall's own reading-order implies: **sign (inferred, in ₹ Cr) → headroom → concentration gate → levels in sigma → OI-since-open**. Items 1–6 in §4.1 deliver that with no new data and would change what the page *means* far more than any visual. Restart the poller first; nothing history-based can be evaluated until there are sessions on disk.

Vanna/charm, term structure, replay and alerts are real features but second-order; the feasibility report's plan (Vanna/Charm first, 4-week UI build) had the order wrong and this document keeps its 2026-08-12 correction banner in force.
