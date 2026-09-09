# Options-Wall — Phase 0 + Phase 1 Review

**Reviewer:** Claude (Opus 4.8)
**Date:** 2026-08-14
**Branch:** `feat/options-wall` @ `ae7c0cd`
**Scope reviewed:** `OPTIONS_WALL_PROJECT_COURSE.md`, `OPTIONS_WALL_PHASE0_1_IMPLEMENTATION_REPORT.md`,
and the five new source files + CLI (1,054 LOC).

---

## Verdict

**ACCEPT with one HIGH fix before Phase 2.** The wiring is sound, the code matches
the documented design, imports/APIs all line up against the real
`OptionsAnalytics` / `OptionsProvider` / `UpstoxMarketData` surfaces, and the parts
that don't need a live token reproduce the report's numbers exactly (Nifty RV
9.44%, BankNifty RV 11.89%). The store round-trips and all three screens run without
error on synthetic chains.

But the headline ranking metric — the D4 "risk-adjusted credit = credit / margin"
that the whole farm list is supposed to be ordered by — **is degenerate as
implemented**: it assigns the identical score to every farm candidate. The farm list
is effectively unranked. Details below.

---

## Verified good

- **APIs match.** `build_structural_snapshot(chain, underlying, ltp, expiry)`,
  `gex.regime` strings (`"Positive GEX (Stable)"` / `"Negative GEX (Volatile)"`),
  `gex.zero_gamma_level`, `gex.gamma_by_strike`, `oi_analysis.support_strike` /
  `resistance_strike`, `_fetch_from_upstox() -> (rows, underlying)`,
  `fetch_quotes_batch() -> {"quotes": {key: {best_bid, best_ask, ...}}}` — all used
  correctly.
- **Realized-vol fix is real and correct.** Annualization by
  `sqrt(252 × 375)` with intra-session-only returns; reproduced live off local 1m
  candles: Nifty 9.44%, BankNifty 11.89% — matches the report.
- **Store is genuinely append-only + multi-symbol**, schema mirrors
  `option_chain_snapshot`, `latest_snapshot` correctly selects `MAX(snapshot_timestamp)`
  per (underlying, expiry). Round-trips 18/18 synthetic rows.
- **Regime gating works.** Farm screen is hard-gated `off` unless
  `"Positive" in regime` — the D5 "never farm into negative GEX" guard holds in code.
- **Deep-ITM `iv=0.0` and null-gamma handling** is defensive throughout
  (`if ... and r.iv`, `calculate_gex` skips null/zero gamma).

---

## Findings

### HIGH-1 — The credit/margin ranking is degenerate; the farm list is not actually ranked
`chain_scanner.py:263` `_margin_proxy(credit) = max(credit * 0.25, 1.0)`.

For any farm row with `credit > 4`, `score = credit / margin_proxy =
credit / (0.25·credit) = 4.0` **exactly, for every candidate**. Confirmed empirically:
two farm rows with credits 200.0 and 210.0 both scored `4.000`. Since `margin_proxy`
is a pure linear function of `credit`, the ratio carries no information — the entire
D4 "risk-adjusted credit" ordering collapses to a constant, and the final
`sorted(key=score)` degenerates to insertion order (strike-ascending), not edge.

Compounding it: **the documented secondary sort is also missing.** Course §5(a) says
"Rank: `credit / margin`, then **IV−RV gap desc**." The IV−RV gap is stored on each
row (`iv_minus_rv`) but never used as a tiebreaker. So even the fallback ordering the
design promised isn't there.

This is not the same as open-question #4 (real SPAN margin unavailable). Even with a
crude proxy, the proxy must not be proportional to credit or it ranks nothing. Two
cheap fixes, either acceptable pre-SPAN:
- Rank farm rows by `iv_minus_rv` desc (the doc's own "actual edge") until a real
  margin is wired, and stop calling it credit/margin; **or**
- Make the proxy a structure-aware notional (e.g. strike-width × lot × count for the
  fly/strangle), which is not proportional to credit.

Whatever the choice, the report/course should stop describing the farm list as
"ranked by credit/margin" until the metric discriminates.

### MEDIUM-1 — `short_strangle` structure is unreachable whenever a pin exists
`_farmable_strikes` (`:231`): if `pin is not None` it returns **only** near-pin
strikes and never falls through to the `[Put Wall, Call Wall]` box. `pin` is
`argmax(gamma_by_strike)`, which is non-`None` whenever any gamma exists — i.e.
almost always. In the loop, those strikes are near-pin by construction, so
`near_pin` is always `True` → `structure` is always `iron_fly`. The
`short_strangle` branch and the `[PW, CW]` box path (Course §5(a), D4) are dead code
in the common case. Either intended (pin-priority) — then document it and drop the
box language — or a logic gap: the box should be scanned in addition to / when pin
conviction is low.

### MEDIUM-2 — No unit tests for 1,054 new lines
Zero tests added for `chain_scanner`, `realized_vol`, or `options_wall_store`. The
repo convention de-emphasizes coverage for research instruments, but HIGH-1 is
exactly the class of bug a three-line test (`score` differs across two credits)
would have caught pre-commit. Suggest a minimal `tests/options_wall/` with: score
discrimination, regime gating on/off, store append→latest round-trip, and RV
annualization factor.

### LOW-1 — IV−RV gate is strike-invariant and recomputed per strike
In `_farm_screen`, `atm_iv` and therefore `gap` do not depend on `strike`, yet
they're recomputed inside the loop (`:120–122`). Functionally every farmable strike
shares one pass/fail on the gap. Hoist the gap check above the loop (early-return
`[]` if it fails) — clearer and cheaper. (If per-strike IV was intended for the
gate, that's a design change, not a hoist.)

### LOW-2 — Engine reaches into a provider private method
`engine.py:41` calls `provider._fetch_from_upstox(...)` across a module boundary.
Pragmatic for now, but a public fetch entry point would be cleaner and would survive
a provider refactor.

### LOW-3 — Double-writer / lock exposure is real, not just theoretical
The course flags that once a wall poller runs, Nifty is polled by both writers
(deferred to Phase 2). Worth noting now: `append_snapshot` opens the wall DB
read-write; DuckDB is single-writer, so a future poller + the engine's fetch-append
path will contend on the same file. Plan the Phase 2 poller as the *sole* writer to
`wall_chain_snapshots.duckdb`.

---

## Non-blocking notes

- RV lookback silently includes today's partial session and a fixed 5 files;
  fine for a discovery instrument and covered by open-question #1.
- Non-credit screens (imperfection, laggard) all score `-1.0` and are therefore
  unordered among themselves — acceptable since they're informational, but the
  course §2 wording ("each screen … ranked on risk-adjusted credit") overstates it.
- `_credit_at_strike` treats `ltp == 0.0` as missing (falsy `and r.ltp`); correct
  for options (0 LTP = no trade), just worth being explicit about.

---

## Recommendation

Fix HIGH-1 (make the ranking discriminate, or rename + rank on IV−RV) before Phase 2
builds persistence on top of a farm list that doesn't actually rank. MEDIUM-1 is a
one-line decision (keep box path or delete it from the doc). Everything else can ride
into Phase 2. Phase 0 wiring and the RV correction are solid and can stand.
