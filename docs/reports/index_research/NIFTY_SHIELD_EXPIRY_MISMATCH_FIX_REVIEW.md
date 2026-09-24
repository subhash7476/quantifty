# Review — NiftyShield chain-poller expiry-mismatch fix

**Reviewer:** Claude
**Implementer:** DeepSeek
**Prompt:** `docs/reports/NIFTY_SHIELD_EXPIRY_MISMATCH_FIX_PROMPT.md`
**Triage:** `docs/reports/NIFTY_SHIELD_EXPIRY_MISMATCH_TRIAGE.md`
**Verdict:** ✅ **ACCEPT** — correct, in scope, independently verified. One LOW hardening follow-up (non-blocking).

---

## What was verified (independently, not from the report)

- **Production diff** = exactly the three prompted edits, nothing more
  (`chain_poller.py`: import `nearest_expiry` @59; `--expiry-days-min` default 2 @458;
  `_fetch` selects `nearest_expiry(date.today(), args.expiry_days_min, args.index).isoformat()`
  @500). No touch to `options_provider.py`, orchestrator, cache schema, or the frozen
  strategy package.
- **Tests present and real:** 4 parametrized fixed-date cases + an end-to-end `main()`
  test that drives the real `_fetch` closure with a stubbed provider (patches `date.today`
  → Monday, `OptionsProvider`, `MarketHours.is_market_open`, `_token_ok`, `_acquire_lock`),
  asserting the tagged expiry is `2026-08-25`, not `2026-08-18`. All patch targets and
  helpers (`UNDERLYING`, `_synthetic_rows`, `_token_ok`) exist.
- **Suites (re-run locally):** `tests/nifty_shield_paper/test_chain_poller.py` + `tests/strategies/`
  → **39 passed**. Frozen strategy green.
- **Wed/Fri byte-identical — verified against the LIVE instrument master** (stronger than the
  arithmetic-only check), using `get_weekly_expiry(as_of_date=…)` vs `nearest_expiry(…,2)`:

  | Date | pre `get_weekly_expiry` | post `nearest_expiry` | |
  |---|---|---|---|
  | Mon 08-17 | 08-18 | 08-25 | DIFFERS (the fix) |
  | Tue 08-18 | 08-18 | 08-25 | DIFFERS (the fix) |
  | Wed 08-19 | 08-25 | 08-25 | IDENTICAL |
  | Fri 08-14 | 08-18 | 08-18 | IDENTICAL |

The fix does exactly what it should: rolls to the ≥2-DTE weekly on Mon/Tue, unchanged Wed–Fri.

## Findings

**LOW-1 (follow-up, non-blocking) — the `min_days` *value* is still duplicated as a literal.**
The fix makes the *algorithm* a single source of truth (`nearest_expiry`), but the poller's
`--expiry-days-min` default is a hardcoded `2`, independent of
`strategies/nifty_shield_v1/config.py` `DEFAULT_CONFIG["expiry_days_min"]` (also 2). If the
strategy config is ever changed to another value, the poller silently reverts to a
divergent expiry — the same failure class this fix closed, one level down. `DEFAULT_CONFIG`
is importable, so the cheap hardening is:

```python
from strategies.nifty_shield_v1.config import DEFAULT_CONFIG
...
parser.add_argument("--expiry-days-min", type=int,
                    default=DEFAULT_CONFIG["expiry_days_min"], ...)
```

Not required for this landing (values match today, behavior is correct); recommend as a
one-line follow-up so the coupling is fully closed.

## Disposition

- **Ready to commit.** No blocking issues.
- **Operator:** restart the poller after market close so the corrected expiry takes effect
  next session; do not restart live mid-window.
- LOW-1 optional — bundle into this commit or defer, reviewer-indifferent.
