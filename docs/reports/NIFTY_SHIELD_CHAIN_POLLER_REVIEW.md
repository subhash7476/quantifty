# NiftyShield Chain Poller — Review + Remediation Directive (R1)

**Reviewer:** Claude. **Implementer:** DeepSeek V4. **Date:** 2026-08-09.
**Verdict: ACCEPTED (R1 remediated + reviewer-verified 2026-08-09).** Original
verdict was CHANGES REQUIRED for one BLOCK finding (R1) — a design flaw
**inherited from the implementation prompt, not introduced by DeepSeek.** R1 was
fixed exactly as prescribed (reader-side bounded retry in
`core/execution/options/nifty_shield_marks.py`); F3 preserved; N1 also fixed.
**Reviewer re-verification (independent, this machine): hardened
`test_concurrent_read_never_raises` 6/6 consecutive passes, full poller file
9/9.** Only tracked-file edit is the R1-sanctioned reader retry; poller + tests
remain new files; `strategies/nifty_shield_v1/` `config_hash` `c5b722ff…536c`
unchanged. The poller is fit for a live PAPER window.

Scope verified by `git status`: three **new untracked** files only, **zero edits
to any tracked file** — so `strategies/nifty_shield_v1/` (`config_hash`
`c5b722ff…536c`) and `ChainSnapshotMarksSource` are genuinely untouched. Real-API
surface verified against the actual objects: `credentials.has_upstox_token`,
`credentials.is_token_expired`, `MarketHours.is_market_open()`,
`OptionsProvider.get_weekly_expiry`, and `_fetch_from_upstox`'s `(rows,
underlying)` return all match. §2.2 (one timestamp/cycle), bootstrap, corrupt
rebuild, atomic-swap retry, Windows-safe PID, loudness, and no-`STOP` are all
correct. **Five of six tests genuinely pass.**

---

## R1 [BLOCK] — the §2.1 guarantee is violated on Windows (flaky, not passing)

**Claim under review:** "concurrent read-while-write → zero `MarksSourceUnavailable`;
6/6 pass."

**Reproduction (this machine, DuckDB 1.4.3, Windows):** the load-bearing test
`test_concurrent_read_never_raises` **fails 2 of 3 runs.** Under a heavier
stressor (40 cycles, 5 ms spacing) the baseline reader raises **every run**
(4, 1, 7 raises across three runs). The reported "pass" is a **timing-dependent
flake** — 6 cycles at 20 ms spacing clears the race often enough to pass ~1/3 of
the time, not a met guarantee.

**Failure:** the reader's `duckdb.connect(read_only=True)` intermittently raises
```
IO Error: Cannot open file "...chain_cache.duckdb": The process cannot access
the file because it is being used by another process.
```
→ `MarksSourceUnavailable`.

**Root cause:** the atomic-swap pattern **reduces but does not eliminate** the
Windows rename-vs-open race. When the poller's `os.replace(tmp → cache)` overlaps
the reader's open of `cache`, Windows returns a sharing violation to *whichever*
side loses — including the reader's open. The prompt's §2.1 assertion that the
reader "effectively never contends… without a reader change" is **empirically
false on Windows.** This is a defect in the prompt's design; DeepSeek implemented
it faithfully.

**Why it is a BLOCK, not a nit:** under F3 a single `MarksSourceUnavailable` is
fatal. `marks()` is called at the 13:00 entry checkpoint and at every exit, so a
random overlap with the 5 s swap **kills a session mid-flight** or refuses
startup. Over a ≥20-session window with multiple `marks()` calls per session, the
expected number of collisions is not negligible — one collision = one lost
session. "Rare" is not "safe" when the failure mode is a fatal, silent-until-it-
strikes session kill.

### Prescribed fix (verified to work) — reader-side bounded retry

Modify `ChainSnapshotMarksSource._connect()` in
`core/execution/options/nifty_shield_marks.py` to retry a **transient** open
failure a small bounded number of times, and raise `MarksSourceUnavailable` only
after the bound (or immediately for a non-transient error). This is legitimate:
`nifty_shield_marks.py` is **E007 execution/composition-root code, not the frozen
strategy package**, and the change **preserves F3** — a persistently unavailable
cache still raises; only a millisecond swap-window contention is ridden through.

Shape (adapt to the existing method; keep `check_available()` delegating to
`_connect()`):

```python
_CONNECT_RETRIES = 5
_CONNECT_RETRY_DELAY_S = 0.05

def _connect(self):
    last = None
    for attempt in range(self._CONNECT_RETRIES):
        try:
            return duckdb.connect(self._db_path, read_only=True)
        except Exception as exc:
            last = exc
            transient = (
                "being used by another process" in str(exc)
                or "Conflicting lock" in str(exc)
                or "Cannot open file" in str(exc)
            )
            if not transient or attempt == self._CONNECT_RETRIES - 1:
                raise MarksSourceUnavailable(
                    f"option-chain cache unavailable at {self._db_path}: {exc}"
                ) from exc
            time.sleep(self._CONNECT_RETRY_DELAY_S)
    raise MarksSourceUnavailable(str(last))       # unreachable; defensive
```

**Evidence this fixes it (reviewer prototype, not committed):** the identical
40-cycle/5 ms stressor with a retrying `_connect` produced **0 raises across 3
runs** (baseline 4/1/7), and an absent-cache `check_available()` **still raised**
(F3 intact).

**Also fix the test so it is a real gate, not a flake:** raise
`test_concurrent_read_never_raises` to a genuine stressor (e.g. ≥30 write cycles
at ≤5 ms spacing) so that, post-fix, it fails deterministically on a regression
and passes deterministically with the retry. As written (6 cycles/20 ms) it is
too weak to protect the guarantee it names.

---

## Non-blocking notes (fix if cheap; not gating)

- **N1 (LOW).** `write_cycle` returns `now` even when `_swap()` fails, and `run()`
  ignores the return. A *persistent* swap failure keeps the last snapshot and logs
  ERROR each cycle (good, loud) but does not increment `_consecutive_failures`,
  because `rows` were non-empty. Consider counting a failed swap toward the
  escalation counter so a chronically unwritable target escalates like a fetch
  outage rather than only per-cycle ERROR lines.
- **N2 (INFO).** The `# unreachable; defensive` tail in the fix is fine to keep;
  the repo's style tolerates a defensive raise on a loop that structurally cannot
  fall through, since the alternative is a silent `None` return into a caller that
  will dereference it.

---

## Re-review gate

Post-fix, the concurrent test must pass **deterministically across ≥5
consecutive runs** on Windows (not 1/3). Provide the run evidence. Everything
else in the acceptance checklist is already met.
