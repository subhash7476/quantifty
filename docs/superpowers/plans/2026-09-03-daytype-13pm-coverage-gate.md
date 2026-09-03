# DayType 13:00 Coverage Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop a single dropped 1-minute bar in 09:15→13:00 from blocking the 13:00 DayType fact, by making the source-acceptance gate match the engine that consumes the frame.

**Architecture:** `DayTypeEngine` triggers the `13pm` checkpoint on wall-clock time (first bar ≥ 13:00, ≥ 100 bars) and is gap-tolerant by design. The Sep-2 fix (`6140b59`) over-tightened `_today_bars` to require 226 contiguous bars. This plan replaces that row-count gate in `scripts/daytype/publish_live_fact.py` with a coverage test — *reaches 13:00 AND ≥ MIN_BARS* — that mirrors the engine exactly. Single-file change plus tests; the Sep-2 ladder, diagnostics, and `fetch_upstox_historical` gate are untouched.

**Tech Stack:** Python 3.10+, pandas, DuckDB, pytest.

## Global Constraints

- Read the file before editing it; follow existing patterns (CLAUDE.md).
- No docstrings/comments on code you did not change; delete unused code completely — no back-compat shims (CLAUDE.md).
- Never fabricate a bar: no interpolation, no synthetic fill. Coverage is judged, not manufactured.
- Determinism preserved: same inputs → same fact. No network I/O added to the publish path.
- `MIN_BARS` is `MIN_BARS_REQUIRED['13pm']` = 100, imported from `scripts/daytype/publish_facts.py` (do not redefine).
- `CHECKPOINT_MIN` = 780 (13:00 IST, minutes from midnight); `SESSION_OPEN_MIN` = 555 (09:15).
- Commit message trailer (this session): `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

## File Structure

- **Modify:** `scripts/daytype/publish_live_fact.py`
  - imports: drop `TARGET_BAR`, add `MIN_BARS`
  - constants: remove `REQUIRED_BARS`
  - `_session_frame`: return session bars up to and including the first bar ≥ 13:00
  - new helper `_reaches_checkpoint(frame)`
  - `_today_bars`: acceptance test becomes `_reaches_checkpoint(frame) and len(frame) >= MIN_BARS`; reject note keeps `_coverage(frame)`
  - update the stale `_today_bars` docstring (drops the "bar index 225 / 226-bar" framing)
- **Modify (tests):** `tests/daytype/test_daytype_facts.py` — three new tests appended after the existing live-publisher tests.

Two existing tests are the regression guard and MUST stay green unchanged:
`test_partial_per_day_store_falls_back_to_live_buffer` and
`test_source_short_of_checkpoint_is_rejected_with_coverage_in_reason`.

---

### Task 1: Replace the 226-row gate with an engine-matching coverage gate

**Files:**
- Modify: `scripts/daytype/publish_live_fact.py:44-46` (imports), `:95-109` (constants + `_session_frame`), `:118-157` (`_today_bars`)
- Test: `tests/daytype/test_daytype_facts.py` (append 3 tests)

**Interfaces:**
- Consumes (unchanged): `_read_candles(path, symbol) -> Optional[pd.DataFrame]`, `_coverage(frame) -> str`, `_note(diag, line)`, `compute_13pm_state`, `vix_at_checkpoint`.
- Produces:
  - `_session_frame(df: pd.DataFrame) -> Optional[pd.DataFrame]` — session bars 09:15 up to and including the first bar at/after 13:00; when none reaches 13:00, the full 09:15-onward frame (for the coverage note); `None` only when `df` is empty / has no `timestamp`.
  - `_reaches_checkpoint(frame: Optional[pd.DataFrame]) -> bool` — True iff the frame's last bar minute ≥ `CHECKPOINT_MIN`.
  - `_today_bars(symbol, today, diag=None) -> tuple[Optional[pd.DataFrame], Optional[str]]` — signature unchanged; acceptance now `_reaches_checkpoint(frame) and len(frame) >= MIN_BARS`.

- [ ] **Step 1: Write the three new failing tests**

Append to `tests/daytype/test_daytype_facts.py`:

```python
@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_interior_gap_frame_still_publishes_13pm(tmp_path, monkeypatch):
    """2026-09-03 13:00 miss: the live buffer held 09:15..13:00 minus one interior
    minute (12:53) — 225 of 226 bars. The Sep-2 len>=226 gate rejected it, though
    the wall-clock engine processes it fine. A single dropped bar must not block
    the fact."""
    import scripts.daytype.publish_live_fact as live

    d = date(2023, 1, 2)

    def drop_1253(df):
        m = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
        return df[m != (12 * 60 + 53)].reset_index(drop=True)

    full = {
        pf.NF_SYMBOL: drop_1253(_craft_session_bars(seed=1, base=24000.0)),
        pf.BN_SYMBOL: drop_1253(_craft_session_bars(seed=2, base=52000.0)),
        pf.VIX_SYMBOL: drop_1253(_craft_session_bars(seed=3, base=14.0)),
    }
    assert len(full[pf.NF_SYMBOL]) == 225        # one interior bar dropped

    candle_dir = tmp_path / "candles_1m"
    candle_dir.mkdir()
    buf = tmp_path / "candles_today.duckdb"
    _write_candle_db(buf, full)
    monkeypatch.setattr(live, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(pf, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(live, "LIVE_BUFFER", buf)

    res = live.publish_live(tmp_path / "live.duckdb", today=d)
    assert res["ready"] is True, res.get("reason")


@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_missing_exact_1300_bar_fires_on_next_bar(tmp_path, monkeypatch):
    """If the 13:00 bar itself is the dropped minute but 13:01 has arrived, the
    feed has passed the checkpoint and the engine fires on the >=13:00 bar. The
    fact must publish without any backfill."""
    import scripts.daytype.publish_live_fact as live

    d = date(2023, 1, 2)

    def to_1301_drop_1300(seed, base):
        df = _craft_session_bars(seed=seed, base=base, min_count=227)  # 09:15..13:01
        m = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
        return df[m != (13 * 60)].reset_index(drop=True)              # drop 13:00

    full = {
        pf.NF_SYMBOL: to_1301_drop_1300(1, 24000.0),
        pf.BN_SYMBOL: to_1301_drop_1300(2, 52000.0),
        pf.VIX_SYMBOL: to_1301_drop_1300(3, 14.0),
    }
    candle_dir = tmp_path / "candles_1m"
    candle_dir.mkdir()
    buf = tmp_path / "candles_today.duckdb"
    _write_candle_db(buf, full)
    monkeypatch.setattr(live, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(pf, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(live, "LIVE_BUFFER", buf)

    res = live.publish_live(tmp_path / "live.duckdb", today=d)
    assert res["ready"] is True, res.get("reason")


@pytest.mark.skipif(not _model_present(), reason="models/daytype not present")
def test_reaches_checkpoint_but_below_min_bars_is_rejected(tmp_path, monkeypatch):
    """Guard: the loosened gate must still reject a frame with too few bars.
    Reaching 13:00 is necessary but not sufficient — the engine needs
    >= MIN_BARS (100). A ~90-bar frame that includes the 13:00 bar is rejected,
    and the reason reports its coverage."""
    import scripts.daytype.publish_live_fact as live

    d = date(2023, 1, 2)

    def sparse(df):                               # 90 bars: first 89 + the 13:00 bar
        return pd.concat([df.head(89), df.tail(1)]).reset_index(drop=True)

    thin = {
        pf.NF_SYMBOL: sparse(_craft_session_bars(seed=1, base=24000.0)),
        pf.BN_SYMBOL: sparse(_craft_session_bars(seed=2, base=52000.0)),
        pf.VIX_SYMBOL: sparse(_craft_session_bars(seed=3, base=14.0)),
    }
    candle_dir = tmp_path / "candles_1m"
    candle_dir.mkdir()
    buf = tmp_path / "candles_today.duckdb"
    _write_candle_db(buf, thin)
    monkeypatch.setattr(live, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(pf, "CANDLE_DIR_1M", candle_dir)
    monkeypatch.setattr(live, "LIVE_BUFFER", buf)

    res = live.publish_live(tmp_path / "live.duckdb", today=d)
    assert res["ready"] is False
    assert "90" in res["reason"]
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `python -m pytest tests/daytype/test_daytype_facts.py -k "interior_gap or missing_exact_1300 or below_min_bars" -v`
Expected: `test_interior_gap_frame_still_publishes_13pm` and `test_missing_exact_1300_bar_fires_on_next_bar` FAIL (`res["ready"]` is False under the old 226 gate). `test_reaches_checkpoint_but_below_min_bars_is_rejected` may already PASS (guard). If `models/daytype` is absent all three skip — in that case run the manual e2e (Step 8) as the acceptance signal instead.

- [ ] **Step 3: Update the imports**

In `scripts/daytype/publish_live_fact.py`, change the `publish_facts` import block (currently lines 44-47):

```python
from scripts.daytype.publish_facts import (  # noqa: E402
    CANDLE_DIR_1M, CHECKPOINT, MIN_BARS, TRAINED_ON,
    commit_ref, model_hash, regime_fact_version,
)
```

(Drop `TARGET_BAR`, add `MIN_BARS`.)

- [ ] **Step 4: Remove `REQUIRED_BARS` and rewrite `_session_frame`**

Replace lines 95-109 (the constants block + `_session_frame`) with:

```python
SESSION_OPEN_MIN = 555                  # 09:15 IST, in minutes from midnight
CHECKPOINT_MIN = 780                    # 13:00 IST


def _session_frame(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Session bars from 09:15 up to and including the first bar at/after 13:00.

    No coverage judgement here — the caller decides acceptance from the returned
    frame (its last bar's minute vs the checkpoint, and its length). This mirrors
    the DayTypeEngine, which fires 13pm on the first bar whose wall-clock time is
    >= 13:00, so a single dropped interior minute is harmless. When no bar reaches
    13:00 the full 09:15-onward frame is returned so the coverage note reports the
    true count and last minute.
    """
    if df is None or df.empty or "timestamp" not in df.columns:
        return None
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    minute = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    sess = df[minute >= SESSION_OPEN_MIN].sort_values("timestamp").reset_index(drop=True)
    if sess.empty:
        return sess
    sess_min = sess["timestamp"].dt.hour * 60 + sess["timestamp"].dt.minute
    reached = sess.index[sess_min >= CHECKPOINT_MIN]
    if len(reached):
        return sess.iloc[: reached[0] + 1].reset_index(drop=True)
    return sess


def _reaches_checkpoint(frame: Optional[pd.DataFrame]) -> bool:
    """True iff the frame's last bar is at/after 13:00 — the engine's wall-clock
    trigger condition. A frame that stops before 13:00 can never fire 13pm, which
    guards the ``13pm``-stamped-from-a-truncated-window fabrication."""
    if frame is None or frame.empty:
        return False
    last = frame["timestamp"].iloc[-1]
    return last.hour * 60 + last.minute >= CHECKPOINT_MIN
```

- [ ] **Step 5: Rewrite the `_today_bars` acceptance test and its docstring**

In `_today_bars` (currently lines 118-157), replace the docstring body's Sep-2 framing and the accept/reject block. The new docstring:

```python
def _today_bars(symbol: str, today: date,
                diag: Optional[list] = None) -> tuple:
    """Today's session bars from the first source that reaches 13:00.

    Ordered ladder: per-day store, then the live buffer. Returns
    ``(frame, source_label)``.

    A source is accepted iff its session frame REACHES 13:00 (a bar at/after the
    checkpoint exists) AND holds >= MIN_BARS (100) bars — the exact condition the
    DayTypeEngine needs to fire 13pm (wall-clock trigger, gap-tolerant). Interior
    gaps are tolerated: on 2026-09-03 the live buffer held 225 of 226 bars,
    missing only the interior minute 12:53, and the engine processes that fine.

    A source that does not reach 13:00 is REJECTED and the ladder continues (the
    2026-09-02 partial per-day store stopped at 09:57; the 2026-08-31 late start
    at 11:39 never held the morning). Not-ready names every source and its
    coverage in one line.
    """
```

Then replace the accept/reject block (currently lines 150-156) with:

```python
        frame = _session_frame(df)
        n = 0 if frame is None else len(frame)
        if _reaches_checkpoint(frame) and n >= MIN_BARS:
            _note(diag, f"{label}: {_coverage(frame)} -> used")
            return frame, label
        why = ("short of 13:00" if not _reaches_checkpoint(frame)
               else f"only {n} bars < {MIN_BARS}")
        _note(diag, f"{label}: {_coverage(frame)} -- {why}, rejected")
        logger.warning("%s: %s %s for %s (%s); trying next source",
                       symbol, label, why, today, _coverage(frame))
```

- [ ] **Step 6: Run the three new tests to verify they pass**

Run: `python -m pytest tests/daytype/test_daytype_facts.py -k "interior_gap or missing_exact_1300 or below_min_bars" -v`
Expected: all three PASS (or skip if `models/daytype` absent — then rely on Step 8).

- [ ] **Step 7: Run the full daytype + hook + paper suites (regression guard)**

Run: `python -m pytest tests/daytype/test_daytype_facts.py tests/runtime/test_publish_hook_live_dry_run.py tests/nifty_shield_paper/ -v`
Expected: all PASS. In particular `test_partial_per_day_store_falls_back_to_live_buffer` and `test_source_short_of_checkpoint_is_rejected_with_coverage_in_reason` still PASS (the partial 43-bar and 150-bar frames do not reach 13:00 → still rejected; "150" still in the reason via `_coverage`).

- [ ] **Step 8: Manual end-to-end verification against today's live buffer**

Run (scratch DB — does not touch the production facts store):
```bash
python scripts/daytype/publish_live_fact.py --date 2026-09-03 --db "$TEMP/daytype_gate_check.duckdb"
```
Expected: prints `LIVE FACT 2026-09-03: ...` (a published 13pm fact from the live buffer), NOT `NOT READY`. This is the exact computation that failed at 13:00 today (the 225-bar frame missing 12:53). If the market session has rolled and the buffer no longer holds 2026-09-03, this step is informational only — the pytest suite is the binding gate.

- [ ] **Step 9: Commit**

```bash
git add scripts/daytype/publish_live_fact.py tests/daytype/test_daytype_facts.py
git commit -m "$(cat <<'EOF'
fix(daytype): coverage gate matches the engine, not a 226-row count

The Sep-2 fix (6140b59) gated source acceptance on len(frame) >= 226 exact
bars. The DayTypeEngine it feeds triggers 13pm on wall-clock time (first bar
>= 13:00, >= 100 bars) and is explicitly gap-tolerant. On 2026-09-03 the live
buffer held 225 of 226 bars, missing only the interior minute 12:53 -- the
gate rejected an otherwise-usable frame and no 13:00 fact published.

Replace the row-count gate with the engine's real condition: accept a source
iff its session frame reaches 13:00 AND holds >= MIN_BARS (100) bars. Interior
gaps are tolerated; a frame that stops before 13:00 is still rejected (a
stronger guard against a 13pm-stamped truncated window than the row count was).
vix_at_checkpoint uses the same ladder, so it is repaired in one change. The
Sep-2 per-day-store -> live-buffer ladder, the one-line skip diagnostic, and
fetch_upstox_historical's _session_closed gate are untouched.

Tests: interior-gap frame publishes (pinned to the 2026-09-03 miss),
exact-13:00-missing fires on 13:01, below-MIN_BARS still rejected; the two
Sep-2 regression tests stay green.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:** §3 gate change → Steps 3-5. §3 frame construction (first bar ≥13:00 inclusive) → Step 4 `_session_frame`. §3 wrong-fact guard → `_reaches_checkpoint` docstring + Step 5. §3 VIX-for-free → same-ladder, verified by existing `test_vix_at_checkpoint_*` in Step 7. §4 no-change items → untouched (only `publish_live_fact.py` + tests modified). §5 tests 1-3 → Step 1; regression tests 4-5 → existing, guarded in Step 7. §6 acceptance → Steps 7-8. §7 flagged label quirk → out of scope, not in any task (correct).

**Placeholder scan:** none — all steps carry exact code and commands.

**Type consistency:** `_session_frame(df) -> Optional[pd.DataFrame]`, `_reaches_checkpoint(frame) -> bool`, `_today_bars(...) -> tuple` used consistently across Steps 4-5. `MIN_BARS`/`CHECKPOINT_MIN`/`SESSION_OPEN_MIN` names match the imports/constants. `_coverage`/`_note` reused unchanged.
