# F1 Phase −1 — Ingestion Review (Lead Review)

*Reviewer: Claude (Lead Quantitative Architect role — review only). Date: 2026-07-19.*
*Scope: `scripts/sfb/ingest_futures_bhavcopy.py` (D1) and its immediate downstream —
`build_continuous_futures.py` (D2), `build_fo_universe.py` (D3),
`certify_futures_substrate.py` (D5), and the emitted `F1_SUBSTRATE_CERTIFICATION.md` (D6).*
*All numbers below are queried live from `data/market_data/futures_bhavcopy.duckdb`, not
read from the D6 report.*

---

## Verdict

The **ingestion code is mechanically sound** — dual-format parsing, copy-first cache,
identity check, and idempotent upsert all work, and the certification arms genuinely pass
(0 violations) on real builder output. The prior REJECT-class failure (vacuous certification
on 2 synthetic days) is gone.

But the claim *"the freeze-block is now purely data acquisition, not code"* **is not correct.**
Two ingestion defects (#2, #3) bite **specifically the re-acquisition you say is all that
remains**, and the certified substrate is unfit for F1's stated purpose (#1). This is code,
too — not just data.

---

## What I verified green (keep)

- **Dual-format parse is correct.** `parse_legacy` (FUTSTK/FUTIDX) and `parse_udiff`
  (STF/IDF) both parse to the same grain; `TtlTrfVal → val_in_lakh` (÷1e5) is right.
- **Contracts-column comparability across the format boundary — CHECKED, holds.** I
  suspected UDiFF `TtlTradgVol` might be traded quantity (shares), not contract count, which
  would poison the D3 liquidity floor. It does not: `val_in_lakh·1e5 / contracts / close ≈
  lot_size (≈250)` on **both** the legacy 2022-08-08 side and the UDiFF 2024-06 side, so both
  columns are number-of-contracts and the D3 comparability comment is accurate.
- **Identity check** (`file_dates != {d}` → discard) correctly rejects mislabeled files.
- **Roll math / cert arms** pass on real output (2,266 splices, 0 seam violations) —
  consistent with the corrective-pass code review (REJECT #2 → CODE green).

---

## Findings (ranked)

### #1 — FATAL-FOR-PURPOSE: the substrate is empty where F1 must be developed, and full only where F1 is forbidden to develop

Live counts from the store:

| Window (pre-reg §8) | Purpose | Rows ingested |
|---|---|--:|
| **TRAIN 2012–2018** | factor sign + bracket-grid `(k_sl,k_tp,n)` selection + regime map — *fit here only* | **0** |
| **HOLDOUT 2019–2022** | single out-of-sample confirmation | **602** (one stray day, 2022-08-08) |
| **SEALED 2023→present** | untouched; spent at most once, only after HOLDOUT confirms | **158,399 (99.6%)** |

The certified panel is **Jun 2024 → Jul 2025** — entirely inside the SEALED window — plus one
orphan HOLDOUT day. Consequently:

- You **cannot** TRAIN-fold-select the ATR bracket grid (pre-reg §5.1/§8) — there is no TRAIN fold.
- You **cannot** run the walk-forward / block-bootstrap that is F1's acceptance gate — no
  out-of-sample HOLDOUT exists (one day is not a fold).
- The only substrate you have is the window the protocol forbids you to develop on.

To be precise about what this is **not**: it is **not sealed-window contamination.** Pre-reg §8
enforces the seal at the *loader* (`MAX(date)` assertion on TRAIN/HOLDOUT) and forbids seeing
*path (High/Low) excursions* to tune brackets (§5.3). Building a forward-adjusted substrate over
sealed data is by design — the pinned `near/next` forward-adjust convention exists precisely so
that later-arriving sealed data does not rewrite train-era adjusted prices. The certification
arms check roll continuity / dupes / liquidity, not F1 signal, and at 0 violations nothing
signal-relevant printed. So the "CERTIFIED" stamp is *true* — it is just certifying the wrong
window. **The substrate isn't dirty; it's empty where it needs to be full.**

Residual watch-item (dormant, not breached): D5 Arm F-A and the coverage block *would* print
sealed-window return magnitudes and underlying/date on any violation. At 0 violations nothing
leaked, but a future non-zero run surfaces sealed structure to the operator's eyes. Keep the D6
report's violation dumps out of any human-read summary once the sealed window carries real weight.

### #2 — HIGH (ingestion): blocked / transient fetches are silently misclassified as "absent (not a trading day)"

`fetch_fo` catches `requests.RequestException` **internally** and returns `(None, None)` when
the last source fails (lines 202–208). `ingest_day` then sees `raw is None` and returns
`(0, None)` → `main` increments **`absent`**. NSE blocks surface as 403 / 503 / connection-reset
— and an exhausted-503 `Retry` raises `RetryError` (a `RequestException`) — so **all** blocked
days funnel into the "absent (404)" bucket. The `-1`/`fetch_failed` branch in `ingest_day` is
effectively **dead code**: `fetch_fo` almost never propagates, so the summary's "Dates
fetch-failed" counter is ~always 0 and its "re-run to retry" warning never fires.

**Why it matters here:** the entire operational problem is NSE-503 blocking. A run from a blocked
IP produces a summary full of "absent" that reads exactly like a run of holidays — the operator
cannot tell "genuinely no trading day" from "I was blocked." This is the single most important
ingestion-specific defect: it makes the ingestion summary untrustworthy under the exact
condition you are trying to diagnose.

*Fix:* distinguish transient/blocked from 404-absent — return a distinct sentinel for
network/HTTP failure vs. genuine 404, count them separately, and do **not** write a `.404` marker
for a blocked fetch (see #3).

### #3 — HIGH (ingestion): `.404` miss-markers never expire → a clean-IP re-run silently skips them

`fetch_fo` writes an empty `.404` marker on HTTP 404 (lines 209–211) and, cache-first, does
`if miss_path.exists(): continue` with **no age check and no distinction between "genuinely no
file" and "404 because I was blocked/rate-limited."** The cache currently holds **1,698 legacy
(`focal_*.404`)** and 423 UDiFF miss-markers.

Most legacy `.404`s are legitimate (`date_range` iterates every calendar day, so weekends and
holidays 404 on both sources — suppression there is correct). The durable defect is that the
cache **cannot tell a block-404 from an absence-404 and never re-checks either.** So the operator's
own unblock plan — *"re-run D1 from an IP NSE does not block"* — **will skip every `.404`'d date**,
including any legacy *trading* day that 404'd only because the prior run was throttled. Legacy
coverage would stay empty even from a clean network, and the failure is silent.

*Fix:* before any clean-IP backfill, purge `.404` markers on **NSE trading days** (cross-ref a
trading calendar; leave weekend/holiday markers). Longer-term, stop writing `.404` for blocked
responses at all (#2), and/or add a marker TTL.

### #4 — MEDIUM (builder, not ingestion): the stray isolated 2022-08-08 day leaks a ~22-month seam into the continuous series

2022-08-08 is a *valid* day, correctly ingested — the defect is in **D2's missing gap-guard**,
not D1. The continuous builder carries that island into `stock_futures_continuous`: **194
underlyings** have a 2022-08-08 row immediately followed by their first 2024 row (e.g. RELIANCE:
`2022-08-08 → 2024-06-05` as consecutive rows). Any return/momentum computation across that seam
treats a ~22-month gap as a single period — a silent, large fabricated return.

It auto-resolves once TRAIN/HOLDOUT data fills the gap, so treat it as a **canary**: the builder
is gap-blind, and the same seam will appear for any suspended / newly-illiquid / recently-listed
name *even with full data*. Add a max-gap guard in D2 (start a fresh continuous segment when the
inter-row gap exceeds N sessions) before F1 consumes the series.

### #5 — MEDIUM (cert): the degeneracy floor is fooled by raw span, not session density or window coverage

The floor I recommended after REJECT #2 did its job — it is *why* the arms have 2,266 subjects
instead of 0. The newly-exposed gap: `certify_futures_substrate.py` computes
`span_days = (max − min).days` and passes on `span_days ≥ 200`. That span is **1,074 days only
because of the single 2022 island**; real contiguous coverage is 260 sessions ≈ 393 days. So the
report stamps **"ADEQUATE"** on a span that is an artifact of one orphan date, and says nothing
about the fact that TRAIN is empty.

*Fix (extend, don't replace):* add (a) a **session-density** check (distinct trade dates vs.
calendar span — reject sparse islands), and (b) an explicit **window-coverage** line (rows in
TRAIN / HOLDOUT / SEALED) so a substrate that is 99.6% sealed cannot read as "adequate for F1."

---

## Bottom line

- **The ingestion code is not done, and "purely data acquisition" is wrong.** #2 and #3 must be
  fixed *before* the clean-IP re-run, or that re-run will (a) report blocked days as holidays and
  (b) skip every previously-404'd legacy date — quietly reproducing the current empty-TRAIN state.
- **The certification is true but certifies the wrong window.** 99.6% of the panel is in the
  SEALED window; TRAIN is empty. F1 cannot be developed on this substrate regardless of how many
  arms pass. This is not a code bug in D5 — it is a fitness-for-purpose gate that D5 does not yet
  assert (#5).
- **No freeze, no scoring, no sealed read.** Unchanged from REJECT #2.

## Recommended sequence before re-running D1

1. Fix #2 (separate blocked/transient from 404-absent; stop marking blocked as `.404`) and #3
   (purge trading-day `.404` markers).
2. Add #5's window-coverage + density lines to D5 so an empty-TRAIN substrate cannot certify.
3. Re-acquire TRAIN 2012–2018 + HOLDOUT 2019–2022 from an unblocked source.
4. Add #4's gap-guard to D2, then rebuild D2/D3 and re-run D5.
5. Only then is the substrate a candidate for the F1 freeze.
