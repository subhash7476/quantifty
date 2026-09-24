# Implementation Prompt — Fix NiftyShield chain-poller expiry mismatch

**For:** DeepSeek (implementer)
**Reviewer:** Claude (prompt author + review only — do not implement)
**Triage/root-cause:** `docs/reports/NIFTY_SHIELD_EXPIRY_MISMATCH_TRIAGE.md` (read first)
**Platform commit at diagnosis:** `8f2d046`
**Branch:** work on `main` unless the reviewer says otherwise; commit is gated on review.

---

## 1. Problem (one paragraph)

The NiftyShield chain poller caches a **different option expiry** than the strategy
trades. The poller (`scripts/nifty_shield_paper/chain_poller.py:496`) uses
`provider.get_weekly_expiry(index)` — the raw nearest weekly, with **no minimum
days-to-expiry**. The strategy (`strategies/nifty_shield_v1/structures.py:74`,
`nearest_expiry`) uses the canonical `expiry_days_min=2` roll rule
(`strategies/nifty_shield_v1/config.py:39`) and picks the nearest weekly **≥ 2 days
out**. On any session within `expiry_days_min` of the front weekly (Mondays before a
Tue expiry, and Tuesdays), the two diverge: the poller caches an expiry the strategy
never requests, so every structure entry is skipped at the E7-4 real-marks gate
("missing option marks, no synthetic fallback"). NiftyShield cannot enter on ~2 of
every 5 sessions. Observed live 2026-08-17: poller cached `2026-08-18`, strategy
requested `NIFTY25AUG26…` (`2026-08-25`) legs → `ENTRY_SKIPPED`.

## 2. Goal

Make the poller cache the **same expiry the strategy trades**, by driving its expiry
selection off the strategy's own `nearest_expiry` selector (single source of truth),
so the two can never diverge. No behavior change Wed–Fri (front weekly is already
≥ 2 DTE); on Mon/Tue the poller must roll to the ≥ 2-DTE weekly.

## 3. Exact changes — `scripts/nifty_shield_paper/chain_poller.py` ONLY

Do **not** modify the frozen strategy package (`strategies/nifty_shield_v1/`); only
*import* the pure function `nearest_expiry` from it.

**(a) Add the import** with the other `from …` imports near the top of the file
(the block around line 57, after `from core.logging import setup_logger`):

```python
from strategies.nifty_shield_v1.structures import nearest_expiry
```

`date` is already imported (`from datetime import date, datetime`, line 51) — do not
re-import it.

**(b) Add a CLI arg** in `main()`'s parser, immediately after the `--index` argument
(currently ends at line 456):

```python
    parser.add_argument("--expiry-days-min", type=int, default=2,
                        help="min DTE for the cached expiry; MUST match the "
                             "strategy's expiry_days_min (config.py, default 2)")
```

**(c) Change the `_fetch` closure** (currently lines 495–498) from:

```python
        def _fetch() -> Tuple[List[object], str]:
            expiry = provider.get_weekly_expiry(args.index)
            rows, _underlying = provider._fetch_from_upstox(args.index, expiry)
            return rows, expiry
```

to:

```python
        def _fetch() -> Tuple[List[object], str]:
            # Cache the SAME expiry the strategy trades: nearest weekly >=
            # expiry_days_min out (structures.nearest_expiry), NOT the raw front
            # weekly. Otherwise on Mon/Tue the poller caches a <2-DTE expiry the
            # strategy never requests, and every entry E7-4-skips on missing marks
            # (see NIFTY_SHIELD_EXPIRY_MISMATCH_TRIAGE.md).
            expiry = nearest_expiry(
                date.today(), args.expiry_days_min, args.index).isoformat()
            rows, _underlying = provider._fetch_from_upstox(args.index, expiry)
            return rows, expiry
```

Notes:
- `nearest_expiry` returns a `datetime.date`; `.isoformat()` yields `"YYYY-MM-DD"`,
  the same string shape `get_weekly_expiry` returned and `_fetch_from_upstox` expects.
- The orchestrator launches the poller with no extra args
  (`scripts/ops/orchestrator.py` CHILDREN["poller"]), so the `default=2` applies
  automatically — **do not** change the orchestrator.
- `provider.get_weekly_expiry` may now be unused in this file — leave the method in
  `options_provider.py` (other callers/dashboard use it); just stop calling it here.

## 4. Tests — add to `tests/nifty_shield_paper/test_chain_poller.py`

Follow TDD: write these first, watch them fail against the current code, then apply
§3 and watch them pass. Use fixed dates (no `date.today()` in assertions — inject or
monkeypatch). Assert the **expiry-selection rule**, not network behavior.

Required cases (Nifty, `expiry_days_min=2`, weekly=Tuesday):
- **Monday 2026-08-17 → 2026-08-25** (front weekly 08-18 is 1 DTE, excluded).
- **Tuesday 2026-08-18 → 2026-08-25** (expiry day, 0 DTE, rolls forward).
- **Wednesday 2026-08-19 → 2026-08-25** (front weekly is ≥ 2 DTE — unchanged).
- **Friday 2026-08-14 → 2026-08-18** (front weekly is 4 DTE — unchanged; regression
  guard that Wed–Fri behavior is preserved).

Since `_fetch` closes over `provider` and `args`, prefer testing the selection
expression directly: assert
`nearest_expiry(<fixed_date>, 2, "NSE_INDEX|Nifty 50").isoformat() == "<expected>"`
for each case (this is the exact expression the fix uses), plus one test that a
stubbed provider's `_fetch` returns rows tagged with the ≥2-DTE expiry on a Monday.
Do not hit the network; stub `_fetch_from_upstox` as the existing poller tests do.

## 5. Constraints / definition of done

- Only `scripts/nifty_shield_paper/chain_poller.py` and
  `tests/nifty_shield_paper/test_chain_poller.py` change. Frozen strategy untouched.
- `python -m pytest tests/nifty_shield_paper/test_chain_poller.py -q` green,
  including the 4 new date cases.
- No new dependencies, no change to the cache schema or the atomic-swap/heartbeat
  logic, no change to `options_provider.py` or the orchestrator.
- Keep the file's existing style (no docstrings/comments on lines you didn't change).
- Report back: the diff, the test run output, and confirm the Wed/Fri cases are
  byte-identical to pre-fix behavior.

## 6. Do NOT (out of scope for this fix)

- Do **not** switch to `provider.get_expiry_list()` / instrument-master filtering.
  That is a separate holiday-robustness follow-up and would reintroduce potential
  divergence from the strategy's pure `nearest_expiry` arithmetic — the opposite of
  this fix's goal (a single shared selector).
- Do **not** poll multiple expiries.
- Do **not** apply live / restart the running poller. Landing + review only; the
  operator decides when to restart the poller (recommended: after market close).
