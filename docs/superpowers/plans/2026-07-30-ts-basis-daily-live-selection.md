# TS Basis Daily — Live Selection (ATM Anchor + Tradeability Screen) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Select each TS Basis Daily option on live Upstox data — ATM struck on a live futures forward, then screened for live bid/ask spread, OI, and volume — with a clean EOD fallback, instead of selecting entirely from stale EOD bhavcopy.

**Architecture:** Selection stays in the shared `core/analytics/options_selection.py` so the CLI and Flask panel cannot drift. A new pure screen (two small functions) is unit-tested in isolation; a two-pass orchestrator resolves live forwards, gathers candidate strikes in a band around each forward, makes one batched quote call, and screens. Live is the default; a `_EOD_ONLY` sentinel and any feed failure fall back to today's EOD path, labelled per row.

**Tech Stack:** Python 3.10+, DuckDB (read-only), Upstox V2 market-quote REST, pytest with in-memory DuckDB + `monkeypatch` (existing test conventions in `tests/analytics/test_options_selection.py`).

## Global Constraints

- Spec of record: `docs/superpowers/specs/2026-07-30-ts-basis-daily-live-atm-anchor-design.md`.
- Thresholds are module constants: `MAX_SPREAD_PCT = 0.05`, `STRIKE_BAND = 3`, `MIN_OI = 100` (reuse existing), `MIN_VOLUME` gate = live volume ≥ the contract's `lot_size` (one lot; fall back to 1 when lot unknown).
- Anchor fallback order per name: live future LTP → EOD future close → synthetic PCP forward. Row field `anchor_source ∈ {"live","eod_future","synthetic"}`.
- Screen verdict per row: `screen ∈ {"pass","snapped","no_tradeable_strike","skipped"}`. `no_tradeable_strike` rows are **kept and flagged**, never dropped. Absent/failed live feed → `screen="skipped"` and the EOD OI-snap path is used; a missing feed never flags/drops a name.
- No new `try/except` in the selection module — the adapter already returns `{}` on failure and never raises; fallback is a dict miss.
- Reuse the existing EQ `tradingsymbol` → `name` mapping for both option and future key resolution (`instrument_type='FUT' AND name=? AND expiry=? AND instrument_key LIKE 'NSE_FO%'`).
- `core/brokers/upstox_market_data.py` gains `best_bid`/`best_ask` from the payload `depth`; nothing else in the adapter changes.
- Follow the repo rule: no docstrings/comments on code you did not change; no speculative abstractions.
- Commit after every task. Co-author trailer: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Run tests with the repo's interpreter from the worktree root, e.g. `python -m pytest tests/analytics/test_options_selection.py -v`.

---

### Task 1: Adapter — expose best_bid / best_ask from depth

**Files:**
- Modify: `core/brokers/upstox_market_data.py` (inside `fetch_quotes_batch`, the per-key quote dict ~lines 120-137)
- Test: `tests/analytics/test_options_selection.py` (add tests near the existing `_quote_payload` helper)

**Interfaces:**
- Consumes: nothing new.
- Produces: `UpstoxMarketData().fetch_quotes_batch(keys)["quotes"][key]` now also carries `best_bid: float|None`, `best_ask: float|None` (from `depth.buy[0].price` / `depth.sell[0].price`). Existing keys (`ltp, net_change, prev_close, change_pct, volume, oi, feed_ts`) are unchanged.

- [ ] **Step 1: Write the failing tests**

Add to `tests/analytics/test_options_selection.py`. First a payload helper that can carry depth, then two tests:

```python
def _quote_payload_with_depth(last_price, net_change, ohlc_close,
                              bid=None, ask=None, key="NSE_FO|111111"):
    depth = {}
    if bid is not None or ask is not None:
        depth = {"buy": [{"price": bid}] if bid is not None else [],
                 "sell": [{"price": ask}] if ask is not None else []}
    return {"data": {"NSE_FO:XYZ": {
        "instrument_token": key, "last_price": last_price, "net_change": net_change,
        "ohlc": {"open": 1.0, "high": 2.0, "low": 0.5, "close": ohlc_close},
        "volume": 1000, "oi": 2000.0, "depth": depth,
        "timestamp": "2026-07-28T13:04:54.072+05:30",
    }}}


def test_quote_exposes_best_bid_and_ask_from_depth(monkeypatch):
    monkeypatch.setattr(
        "core.brokers.upstox_market_data.requests.get",
        lambda *a, **k: _FakeResp(_quote_payload_with_depth(
            last_price=8.0, net_change=0.0, ohlc_close=8.0, bid=7.9, ask=8.1)),
    )
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")
    q = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])["quotes"]["NSE_FO|111111"]
    assert q["best_bid"] == pytest.approx(7.9)
    assert q["best_ask"] == pytest.approx(8.1)


def test_quote_bid_ask_are_none_when_depth_absent(monkeypatch):
    monkeypatch.setattr(
        "core.brokers.upstox_market_data.requests.get",
        lambda *a, **k: _FakeResp(_quote_payload_with_depth(
            last_price=8.0, net_change=0.0, ohlc_close=8.0)),  # no depth
    )
    monkeypatch.setattr("core.auth.credentials.credentials.get", lambda *a, **k: "tok")
    q = UpstoxMarketData().fetch_quotes_batch(["NSE_FO|111111"])["quotes"]["NSE_FO|111111"]
    assert q["best_bid"] is None
    assert q["best_ask"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/analytics/test_options_selection.py::test_quote_exposes_best_bid_and_ask_from_depth tests/analytics/test_options_selection.py::test_quote_bid_ask_are_none_when_depth_absent -v`
Expected: FAIL with `KeyError: 'best_bid'`.

- [ ] **Step 3: Implement the depth parse**

In `core/brokers/upstox_market_data.py`, inside the `for key in instrument_keys:` loop of `fetch_quotes_batch`, before the `quotes[key] = {...}` dict, add:

```python
            depth = e.get("depth") or {}
            buy = depth.get("buy") or []
            sell = depth.get("sell") or []
            best_bid = buy[0].get("price") if buy and isinstance(buy[0], dict) else None
            best_ask = sell[0].get("price") if sell and isinstance(sell[0], dict) else None
```

Then add these two entries to the `quotes[key]` dict literal:

```python
                "best_bid": best_bid,
                "best_ask": best_ask,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/analytics/test_options_selection.py -k "best_bid or bid_ask" -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/brokers/upstox_market_data.py tests/analytics/test_options_selection.py
git commit -m "feat: expose best_bid/best_ask from Upstox quote depth"
```

---

### Task 2: Pure tradeability screen (functions + constants)

**Files:**
- Modify: `core/analytics/options_selection.py` (add constants near line 27-28; add two module-level functions)
- Test: `tests/analytics/test_options_selection.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Constants `MAX_SPREAD_PCT = 0.05`, `STRIKE_BAND = 3`, `MIN_VOLUME_FALLBACK = 1`.
  - `screen_candidate(bid, ask, oi, volume, min_oi, min_volume, max_spread_pct) -> tuple[bool, float|None, str|None]` returning `(passes, spread_pct, reason)`.
  - `pick_screened_strike(candidates, forward, min_oi, min_volume, max_spread_pct) -> tuple[dict|None, str|None]` where each candidate is a dict with at least `{"strike","bid","ask","oi","volume"}`; returns `(chosen_candidate, None)` on success or `(None, reason)` when none pass. The chosen candidate is the passing one nearest `forward` (tie-break: tightest spread) and gains a `"spread_pct"` key.

- [ ] **Step 1: Write the failing tests**

```python
from core.analytics.options_selection import (
    MAX_SPREAD_PCT, STRIKE_BAND, screen_candidate, pick_screened_strike,
)


def test_screen_passes_tight_liquid_strike():
    ok, spread, reason = screen_candidate(
        bid=9.9, ask=10.1, oi=5000, volume=500,
        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is True
    assert spread == pytest.approx(0.02, abs=1e-6)   # 0.2/10.0
    assert reason is None


def test_screen_rejects_wide_spread():
    ok, spread, reason = screen_candidate(
        bid=9.0, ask=11.0, oi=5000, volume=500,
        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is False
    assert spread == pytest.approx(0.2, abs=1e-6)     # 2.0/10.0
    assert "spread" in reason


def test_screen_spread_boundary_is_inclusive():
    # spread exactly 5%: bid=9.75 ask=10.25 mid=10 -> 0.5/10 = 0.05
    ok, spread, _ = screen_candidate(
        bid=9.75, ask=10.25, oi=5000, volume=500,
        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is True
    assert spread == pytest.approx(0.05, abs=1e-9)


def test_screen_rejects_low_oi_and_low_volume():
    ok_oi, _, r_oi = screen_candidate(9.9, 10.1, oi=50, volume=500,
                                      min_oi=100, min_volume=50, max_spread_pct=0.05)
    ok_vol, _, r_vol = screen_candidate(9.9, 10.1, oi=5000, volume=10,
                                        min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok_oi is False and "OI" in r_oi
    assert ok_vol is False and "vol" in r_vol


def test_screen_rejects_missing_or_nonpositive_quote():
    ok, spread, reason = screen_candidate(None, None, oi=5000, volume=500,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert ok is False and spread is None and "quote" in reason


def test_pick_chooses_nearest_forward_among_passing():
    cands = [
        {"strike": 100.0, "bid": 9.9,  "ask": 10.1, "oi": 5000, "volume": 500},
        {"strike": 105.0, "bid": 5.95, "ask": 6.05, "oi": 5000, "volume": 500},
    ]
    chosen, reason = pick_screened_strike(cands, forward=104.0,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert reason is None
    assert chosen["strike"] == 105.0
    assert "spread_pct" in chosen


def test_pick_snaps_past_wide_nearest_to_a_tight_neighbour():
    cands = [
        {"strike": 105.0, "bid": 4.0, "ask": 8.0, "oi": 5000, "volume": 500},   # nearest, wide
        {"strike": 100.0, "bid": 9.95, "ask": 10.05, "oi": 5000, "volume": 500},  # tight
    ]
    chosen, reason = pick_screened_strike(cands, forward=104.0,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert reason is None
    assert chosen["strike"] == 100.0


def test_pick_returns_reason_when_none_pass():
    cands = [{"strike": 100.0, "bid": 4.0, "ask": 8.0, "oi": 5000, "volume": 500}]
    chosen, reason = pick_screened_strike(cands, forward=100.0,
                                          min_oi=100, min_volume=50, max_spread_pct=0.05)
    assert chosen is None
    assert "spread" in reason
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/analytics/test_options_selection.py -k "screen or pick_" -v`
Expected: FAIL with `ImportError: cannot import name 'screen_candidate'`.

- [ ] **Step 3: Implement constants + functions**

In `core/analytics/options_selection.py`, after the existing `MIN_OI = 100` / `DEFAULT_MIN_DTE = 7` block add:

```python
MAX_SPREAD_PCT = 0.05
STRIKE_BAND = 3
MIN_VOLUME_FALLBACK = 1


def screen_candidate(bid, ask, oi, volume, min_oi, min_volume, max_spread_pct):
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        return False, None, "no quote"
    mid = (bid + ask) / 2.0
    spread_pct = (ask - bid) / mid
    if oi is None or oi < min_oi:
        return False, spread_pct, f"OI {oi} < {min_oi}"
    if volume is None or volume < min_volume:
        return False, spread_pct, f"vol {volume} < {min_volume}"
    if spread_pct > max_spread_pct:
        return False, spread_pct, f"spread {spread_pct:.1%} > {max_spread_pct:.0%}"
    return True, spread_pct, None


def pick_screened_strike(candidates, forward, min_oi, min_volume, max_spread_pct):
    passing = []
    last_reason = None
    for c in candidates:
        ok, spread_pct, reason = screen_candidate(
            c.get("bid"), c.get("ask"), c.get("oi"), c.get("volume"),
            min_oi, min_volume, max_spread_pct)
        c["spread_pct"] = spread_pct
        if ok:
            passing.append(c)
        else:
            last_reason = reason
    if not passing:
        return None, last_reason or "no candidate passed"
    chosen = min(passing, key=lambda c: (abs(c["strike"] - forward), c["spread_pct"]))
    return chosen, None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/analytics/test_options_selection.py -k "screen or pick_" -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add core/analytics/options_selection.py tests/analytics/test_options_selection.py
git commit -m "feat: pure tradeability screen for option strike selection"
```

---

### Task 3: Live forward resolution + anchor_source

**Files:**
- Modify: `core/analytics/options_selection.py` (add `_future_key`, `_resolve_live_forwards`)
- Test: `tests/analytics/test_options_selection.py`

**Interfaces:**
- Consumes: an `inst` DuckDB connection (schema `instruments(instrument_key, tradingsymbol, name, expiry, strike, instrument_type, lot_size, snapshot_date)`), the `book` as `[(ticker, direction), ...]`, an `expiries` dict `{ticker: date}`, and a `market_data` object exposing `fetch_ltp_batch(keys) -> {key: float}`.
- Produces: `_resolve_live_forwards(inst, snap, book, expiries, market_data) -> {ticker: float}` — a map of live future LTP per ticker, populated only for names whose FUT key resolved AND returned a price. Names absent from the map fall back to EOD downstream. Also `_future_key(inst, snap, ticker, expiry) -> str|None`.

- [ ] **Step 1: Write the failing tests**

Add in-memory instruments + stub market-data helpers (reused by later tasks), then the tests:

```python
def _inst_con(rows, snap=date(2026, 7, 27)):
    """rows: (name, tradingsymbol, expiry_iso, strike, instrument_type, key, lot)."""
    con = duckdb.connect(":memory:")
    con.execute("""
        CREATE TABLE instruments (
            instrument_key VARCHAR, tradingsymbol VARCHAR, name VARCHAR,
            expiry VARCHAR, strike DOUBLE, instrument_type VARCHAR,
            lot_size BIGINT, snapshot_date DATE
        )
    """)
    for name, tsym, exp, strike, itype, key, lot in rows:
        con.execute("INSERT INTO instruments VALUES (?,?,?,?,?,?,?,?)",
                    [key, tsym, name, exp, strike, itype, lot, snap])
    return con, snap


class _StubMD:
    def __init__(self, ltps=None, quotes=None):
        self._ltps = ltps or {}
        self._quotes = quotes or {}

    def fetch_ltp_batch(self, keys):
        return {k: self._ltps[k] for k in keys if k in self._ltps}

    def fetch_quotes_batch(self, keys):
        return {"quotes": {k: self._quotes[k] for k in keys if k in self._quotes},
                "error": None}


def test_resolve_live_forwards_maps_ticker_to_future_ltp():
    from core.analytics.options_selection import _resolve_live_forwards
    con, snap = _inst_con([
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "FUT", "NSE_FO|58419", 3000),
    ])
    md = _StubMD(ltps={"NSE_FO|58419": 251.4})
    fwds = _resolve_live_forwards(
        con, snap, [("WIPRO", "LONG")], {"WIPRO": date(2026, 8, 25)}, md)
    assert fwds == {"WIPRO": 251.4}


def test_resolve_live_forwards_omits_names_with_no_key_or_no_price():
    from core.analytics.options_selection import _resolve_live_forwards
    con, snap = _inst_con([
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0, "FUT", "NSE_FO|58419", 3000),
    ])
    md = _StubMD(ltps={})  # key resolves but no live price
    fwds = _resolve_live_forwards(
        con, snap, [("WIPRO", "LONG"), ("NOSUCH", "SHORT")],
        {"WIPRO": date(2026, 8, 25), "NOSUCH": date(2026, 8, 25)}, md)
    assert fwds == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/analytics/test_options_selection.py -k resolve_live_forwards -v`
Expected: FAIL with `ImportError: cannot import name '_resolve_live_forwards'`.

- [ ] **Step 3: Implement `_future_key` + `_resolve_live_forwards`**

Add to `core/analytics/options_selection.py`:

```python
def _future_key(inst, snap, ticker, expiry):
    name = inst.execute(
        "SELECT name FROM instruments WHERE snapshot_date=? "
        "AND instrument_type='EQ' AND tradingsymbol=? LIMIT 1",
        [snap, ticker],
    ).fetchone()
    if not name:
        return None
    row = inst.execute(
        "SELECT instrument_key FROM instruments WHERE snapshot_date=? AND name=? "
        "AND instrument_type='FUT' AND expiry=? AND instrument_key LIKE 'NSE_FO%' LIMIT 1",
        [snap, name[0], expiry.isoformat()],
    ).fetchone()
    return row[0] if row else None


def _resolve_live_forwards(inst, snap, book, expiries, market_data):
    key_by_ticker = {}
    for ticker, _ in book:
        expiry = expiries.get(ticker)
        if expiry is None:
            continue
        key = _future_key(inst, snap, ticker, expiry)
        if key:
            key_by_ticker[ticker] = key
    ltps = market_data.fetch_ltp_batch(list(key_by_ticker.values()))
    return {t: ltps[k] for t, k in key_by_ticker.items() if k in ltps}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/analytics/test_options_selection.py -k resolve_live_forwards -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add core/analytics/options_selection.py tests/analytics/test_options_selection.py
git commit -m "feat: resolve live futures forward per name for ATM anchor"
```

---

### Task 4: Orchestrator — wire live anchor + screen into the book builder

**Files:**
- Modify: `core/analytics/options_selection.py` (add `_EOD_ONLY`, `_band_candidates`, `_base_row`, `_resolve_instrument`, `_build_contracts`, `_fill_eod`; rewrite `select_book_options` to delegate)
- Test: `tests/analytics/test_options_selection.py`

**Interfaces:**
- Consumes: the pure functions from Task 2, `_resolve_live_forwards` from Task 3, the extended adapter from Task 1, and the existing `pick_expiry` / `select_option`.
- Produces:
  - `select_book_options(book, min_dte=DEFAULT_MIN_DTE, today=None, market_data=None)` — unchanged signature except the new `market_data` param (default `None` → live via `UpstoxMarketData()`; pass `_EOD_ONLY` to force EOD).
  - `_build_contracts(o, f, inst, book, min_dte, today, market_data)` — testable core taking open connections; returns the list of row dicts.
  - Every row dict additionally carries: `anchor_source`, `screen`, `spread_pct`, `live_oi`, `live_volume`, `best_bid`, `best_ask`, `screen_reason` (all default `None`/`"skipped"` on the EOD path).

- [ ] **Step 1: Write the failing tests**

Add a combined in-memory environment helper and three `_build_contracts` tests:

```python
def _full_env(chain_rows, inst_rows, fut_rows=None):
    """Return (o, f, inst, snap) in-memory DBs for _build_contracts.

    chain_rows: (underlying, expiry, strike, otype, settle, oi, contracts, trade_date)
    inst_rows : (name, tradingsymbol, expiry_iso, strike, instrument_type, key, lot)
    fut_rows  : (underlying, expiry, close, trade_date)
    """
    o = duckdb.connect(":memory:")
    o.execute("""CREATE TABLE stock_options_bhavcopy (
        underlying VARCHAR, expiry_dt DATE, strike DOUBLE, option_type VARCHAR,
        settle DOUBLE, open_int BIGINT, contracts BIGINT, trade_date DATE)""")
    for r in chain_rows:
        o.execute("INSERT INTO stock_options_bhavcopy VALUES (?,?,?,?,?,?,?,?)", list(r))

    f = duckdb.connect(":memory:")
    f.execute("""CREATE TABLE futures_bhavcopy (
        underlying VARCHAR, expiry_dt DATE, close DOUBLE, trade_date DATE)""")
    for r in (fut_rows or []):
        f.execute("INSERT INTO futures_bhavcopy VALUES (?,?,?,?)", list(r))

    inst, snap = _inst_con(inst_rows)
    return o, f, inst, snap


EXP = date(2026, 8, 25)


def test_build_live_anchor_centres_on_live_forward_and_passes_screen():
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 260.0, "CE", 2.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 260.0, "CE",  "NSE_FO|260CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    md = _StubMD(
        ltps={"NSE_FO|58419": 251.4},                      # live fwd -> ATM 250
        quotes={"NSE_FO|250CE": {"best_bid": 3.98, "best_ask": 4.02,
                                 "oi": 9000, "volume": 6000},
                "NSE_FO|260CE": {"best_bid": 1.9, "best_ask": 2.1,
                                 "oi": 9000, "volume": 6000},
                "NSE_FO|240CE": {"best_bid": 5.9, "best_ask": 6.1,
                                 "oi": 9000, "volume": 6000}})
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=md)
    r = rows[0]
    assert r["anchor_source"] == "live"
    assert r["forward"] == pytest.approx(251.4)
    assert r["strike"] == 250.0            # nearest to live fwd, screen passes
    assert r["screen"] == "pass"
    assert r["spread_pct"] == pytest.approx(0.01, abs=1e-6)


def test_build_flags_when_no_strike_is_tradeable():
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 250.0, TRADE_DATE)])
    md = _StubMD(ltps={"NSE_FO|58419": 250.0},
                 quotes={"NSE_FO|250CE": {"best_bid": 2.0, "best_ask": 6.0,  # ~100% wide
                                          "oi": 9000, "volume": 6000}})
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=md)
    r = rows[0]
    assert r["screen"] == "no_tradeable_strike"
    assert "spread" in r["screen_reason"]
    assert r["ticker"] == "WIPRO"          # kept, not dropped


def test_build_skips_screen_and_falls_back_when_no_live_feed():
    from core.analytics.options_selection import _build_contracts, _EOD_ONLY
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    rows = _build_contracts(o, f, inst, [("WIPRO", "LONG")],
                            min_dte=7, today=TRADE_DATE, market_data=_EOD_ONLY)
    r = rows[0]
    assert r["screen"] == "skipped"
    assert r["anchor_source"] == "eod_future"
    assert r["forward"] == pytest.approx(241.0)   # EOD future close
    assert r["strike"] == 240.0                    # EOD nearest-to-forward
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/analytics/test_options_selection.py -k build_ -v`
Expected: FAIL with `ImportError: cannot import name '_build_contracts'`.

- [ ] **Step 3: Implement the sentinel, helpers, orchestrator, and re-point `select_book_options`**

Add the sentinel near the constants:

```python
_EOD_ONLY = object()
```

Add these helpers and `_build_contracts` above the current `select_book_options`:

```python
def _band_candidates(o, ticker, opt_type, expiry, odate, forward):
    chain = o.execute(
        "SELECT strike, settle, open_int FROM stock_options_bhavcopy "
        "WHERE underlying=? AND expiry_dt=? AND option_type=? AND trade_date=? "
        "ORDER BY strike",
        [ticker, expiry, opt_type, odate],
    ).fetchall()
    if not chain:
        return []
    strikes = [r[0] for r in chain]
    nearest = min(range(len(strikes)), key=lambda i: abs(strikes[i] - forward))
    lo, hi = max(0, nearest - STRIKE_BAND), min(len(chain), nearest + STRIKE_BAND + 1)
    return chain[lo:hi]


def _base_row(ticker, direction, opt_type):
    return {
        "ticker": ticker, "direction": direction, "opt_type": opt_type,
        "expiry": None, "strike": None, "settle": None, "oi": None,
        "forward": None, "lot_size": None, "instrument_key": None,
        "tradingsymbol": None, "quote_date": None, "snapped": False,
        "nearest_strike": None, "premium_cost": None,
        "anchor_source": None, "screen": "skipped", "spread_pct": None,
        "live_oi": None, "live_volume": None, "best_bid": None, "best_ask": None,
        "screen_reason": None,
    }


def _resolve_instrument(inst, snap, ticker, opt_type, strike, expiry):
    name = inst.execute(
        "SELECT name FROM instruments WHERE snapshot_date=? "
        "AND instrument_type='EQ' AND tradingsymbol=? LIMIT 1",
        [snap, ticker],
    ).fetchone()
    if not name:
        return None, None, None
    r = inst.execute(
        "SELECT instrument_key, tradingsymbol, lot_size FROM instruments "
        "WHERE snapshot_date=? AND name=? AND instrument_type=? "
        "AND strike=? AND expiry=? LIMIT 1",
        [snap, name[0], opt_type, strike, expiry.isoformat()],
    ).fetchone()
    return (r[0], r[1], r[2]) if r else (None, None, None)


def _fill_eod(o, inst, snap, row, forward):
    expiry = row["expiry"]
    sel = select_option(o, row["ticker"], row["opt_type"], expiry, forward)
    if sel is None:
        return
    key, tsym, lot = _resolve_instrument(
        inst, snap, row["ticker"], row["opt_type"], sel["strike"], expiry)
    row.update({
        "strike": sel["strike"], "settle": sel["settle"], "oi": sel["oi"],
        "forward": sel["forward"], "quote_date": sel["quote_date"],
        "snapped": sel["snapped"], "nearest_strike": sel["nearest_strike"],
        "lot_size": lot, "instrument_key": key, "tradingsymbol": tsym,
        "premium_cost": (sel["settle"] * lot) if (lot and sel["settle"]) else None,
        "screen": "skipped",
    })
    if row["anchor_source"] is None:
        row["anchor_source"] = "synthetic" if forward is None else "eod_future"


def _build_contracts(o, f, inst, book, min_dte, today, market_data):
    snap = inst.execute("SELECT MAX(snapshot_date) FROM instruments").fetchone()[0]
    live = market_data is not _EOD_ONLY

    expiries = {t: pick_expiry(o, t, min_dte, today) for t, _ in book}
    live_fwds = {}
    if live:
        live_fwds = _resolve_live_forwards(inst, snap, book, expiries, market_data)

    # Pass A: per-name context + collect candidate option keys for one batch.
    ctx = []
    all_keys = []
    for ticker, direction in book:
        opt_type = "CE" if direction == "LONG" else "PE"
        expiry = expiries.get(ticker)
        row = _base_row(ticker, direction, opt_type)
        if expiry is None:
            ctx.append((row, None))
            continue
        row["expiry"] = expiry

        eod_fut = f.execute(
            "SELECT close FROM futures_bhavcopy WHERE underlying=? AND expiry_dt=? "
            "ORDER BY trade_date DESC LIMIT 1", [ticker, expiry]).fetchone()
        if ticker in live_fwds:
            forward, row["anchor_source"] = live_fwds[ticker], "live"
        elif eod_fut:
            forward, row["anchor_source"] = eod_fut[0], "eod_future"
        else:
            forward, row["anchor_source"] = None, "synthetic"

        if not live or forward is None:
            ctx.append((row, ("EOD", forward)))
            continue

        odate = o.execute(
            "SELECT MAX(trade_date) FROM stock_options_bhavcopy "
            "WHERE underlying=? AND expiry_dt=? AND option_type=?",
            [ticker, expiry, opt_type]).fetchone()[0]
        band = _band_candidates(o, ticker, opt_type, expiry, odate, forward)
        cands = []
        for strike, settle, _eod_oi in band:
            key, tsym, lot = _resolve_instrument(inst, snap, ticker, opt_type, strike, expiry)
            cands.append({"strike": strike, "settle": settle, "key": key,
                          "tsym": tsym, "lot": lot})
            if key:
                all_keys.append(key)
        ctx.append((row, ("LIVE", forward, expiry, odate, opt_type, cands)))

    quotes = {}
    if all_keys:
        quotes = market_data.fetch_quotes_batch(all_keys).get("quotes", {})

    # Pass B: resolve each name to a final row.
    out = []
    for row, c in ctx:
        if c is None:
            out.append(row); continue
        if c[0] == "EOD":
            _fill_eod(o, inst, snap, row, c[1])
            out.append(row); continue

        _, forward, expiry, odate, opt_type, cands = c
        for cand in cands:
            q = quotes.get(cand["key"]) or {}
            cand["bid"], cand["ask"] = q.get("best_bid"), q.get("best_ask")
            cand["oi"], cand["volume"] = q.get("oi"), q.get("volume")
        if not any(cand.get("key") and quotes.get(cand["key"]) for cand in cands):
            _fill_eod(o, inst, snap, row, forward)   # feed miss -> skip screen
            out.append(row); continue

        strikes = [cand["strike"] for cand in cands]
        nearest = min(strikes, key=lambda s: abs(s - forward))
        lot_lookup = {cand["strike"]: cand["lot"] for cand in cands}
        min_vol = lot_lookup.get(nearest) or MIN_VOLUME_FALLBACK
        chosen, reason = pick_screened_strike(
            cands, forward, MIN_OI, min_vol, MAX_SPREAD_PCT)
        row["forward"] = forward
        if chosen is None:
            row["screen"] = "no_tradeable_strike"
            row["screen_reason"] = reason
            out.append(row); continue

        lot = chosen["lot"]
        row.update({
            "strike": chosen["strike"], "settle": chosen["settle"],
            "oi": chosen["oi"], "quote_date": odate,
            "nearest_strike": nearest, "snapped": chosen["strike"] != nearest,
            "screen": "pass" if chosen["strike"] == nearest else "snapped",
            "spread_pct": chosen["spread_pct"], "live_oi": chosen["oi"],
            "live_volume": chosen["volume"], "best_bid": chosen["bid"],
            "best_ask": chosen["ask"], "lot_size": lot,
            "instrument_key": chosen["key"], "tradingsymbol": chosen["tsym"],
            "premium_cost": (chosen["settle"] * lot) if (lot and chosen["settle"]) else None,
        })
        out.append(row)
    return out
```

Then replace the body of `select_book_options` with a thin opener that delegates:

```python
def select_book_options(book, min_dte: int = DEFAULT_MIN_DTE, today: date | None = None,
                        market_data=None):
    if market_data is None:
        from core.brokers.upstox_market_data import UpstoxMarketData
        market_data = UpstoxMarketData()
    o = duckdb.connect(str(OPT_DB), read_only=True)
    f = duckdb.connect(str(FUT_DB), read_only=True)
    inst = duckdb.connect(str(INST_DB), read_only=True)
    try:
        return _build_contracts(o, f, inst, book, min_dte, today, market_data)
    finally:
        o.close(); f.close(); inst.close()
```

Note: `_fill_eod` passes `forward` into `select_option`; when `forward is None` the existing synthetic-PCP branch inside `select_option` runs, preserving `anchor_source="synthetic"`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/analytics/test_options_selection.py -k build_ -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Run the FULL selection test file (regression on the untouched EOD path)**

Run: `python -m pytest tests/analytics/test_options_selection.py -v`
Expected: PASS — all pre-existing `select_option` / `pick_expiry` / adapter / market-state tests still green, confirming the EOD path is unchanged.

- [ ] **Step 6: Commit**

```bash
git add core/analytics/options_selection.py tests/analytics/test_options_selection.py
git commit -m "feat: live ATM anchor + tradeability screen in book builder, EOD fallback"
```

---

### Task 5: CLI — show anchor source and screen verdict

**Files:**
- Modify: `scripts/ts_basis_daily_options.py` (the print loop and footer, lines ~80-108)
- Test: manual (CLI is a thin reporter; no unit harness — verified by running it)

**Interfaces:**
- Consumes: `select_book_options` rows with the new fields from Task 4.
- Produces: a table with `Src` and `Screen` columns; flagged rows print their reason.

- [ ] **Step 1: Update the header and row format**

In `scripts/ts_basis_daily_options.py`, change the header lines to add two columns:

```python
    print(f"  {'Ticker':<11}{'Dir':<6}{'Opt':<4}{'Expiry':<12}{'Fwd':>9}{'Strike':>8}"
          f"{'Prem':>8}{'OI':>11}{'Lot':>8}{'PremCost':>11}{'Src':>6}{'Screen':>10}")
    print(f"  {'-'*104}")
```

Replace the current per-contract loop body with (adds the flagged case, `Src`, `Screen`):

```python
    for c in contracts:
        if c["screen"] == "no_tradeable_strike":
            print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}"
                  f"  NO TRADEABLE STRIKE  ({c['screen_reason']})")
            continue
        if c["strike"] is None:
            print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}  NO CHAIN")
            continue
        print(f"  {c['ticker']:<11}{c['direction']:<6}{c['opt_type']:<4}"
              f"{str(c['expiry']):<12}{c['forward']:>9.1f}{c['strike']:>8.0f}"
              f"{c['settle']:>8.2f}{c['oi']:>11}{(c['lot_size'] or 0):>8}"
              f"{(c['premium_cost'] or 0):>11,.0f}"
              f"{(c['anchor_source'] or '-'):>6}{(c['screen'] or '-'):>10}")
        if c["snapped"]:
            notes.append(f"  {c['ticker']}: snapped off nearest strike "
                         f"{c['nearest_strike']:.0f} to {c['strike']:.0f}.")
        if c["instrument_key"] is None:
            notes.append(f"  {c['ticker']}: no instrument key resolved (not tradeable via API).")
```

Update the footer legend lines:

```python
    print(f"\n  Fwd = live future LTP when Src=live, else EOD future close.  "
          f"Screen = live spread/OI/volume verdict (skipped = no live feed).")
    print(f"  PremCost = premium x lot (1 lot debit).  Live prices: /ts-basis-daily/")
```

- [ ] **Step 2: Run the CLI (manual verification)**

Run: `python scripts/ts_basis_daily_options.py --top 5`
Expected outside market hours / no token: table prints, `Src` mostly `eod_fu`/`synthe`, `Screen` = `skipped`; no crash. During market hours with a valid token: `Src=live`, `Screen` in `pass`/`snapped`/`no_tradeable_strike`.

Note: this worktree has no data DBs — run from the main checkout `F:\Nifty`, or copy the four DBs in. If the facts DB is missing the script prints its existing `ERROR: missing …` line and exits 1; that is expected, not a failure of this task.

- [ ] **Step 3: Commit**

```bash
git add scripts/ts_basis_daily_options.py
git commit -m "feat: CLI shows anchor source and live screen verdict"
```

---

### Task 6: Flask `/api/options` — expose new fields; template marks freshness

**Files:**
- Modify: `flask_app/blueprints/ts_basis_daily.py` (`api_options`, ~lines 204-232)
- Modify: `flask_app/templates/ts_basis_daily/index.html` (options table + header marker)
- Test: `tests/analytics/test_options_selection.py` (once-per-load stability of `_build_contracts`)

**Interfaces:**
- Consumes: `_build_contracts` rows from Task 4; the existing `_resolve_contracts` cache (unchanged).
- Produces: `/api/options` JSON contracts carrying `anchor_source`, `screen`, `spread_pct`, `live_oi`, `live_volume`, `best_bid`, `best_ask`, `screen_reason`; the template greys `no_tradeable_strike` rows and shows an anchor/screen marker.

- [ ] **Step 1: Write the stability test**

```python
def test_build_is_stable_across_two_calls_same_inputs():
    """The panel caches per formation; re-resolving the same book with the same
    live snapshot must yield the same strike (no per-call churn)."""
    from core.analytics.options_selection import _build_contracts
    chain = [("WIPRO", EXP, 240.0, "CE", 6.0, 5000, 10, TRADE_DATE),
             ("WIPRO", EXP, 250.0, "CE", 4.0, 5000, 10, TRADE_DATE)]
    inst_rows = [
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "EQ",  "NSE_EQ|INE075A01022", 0),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 0.0,   "FUT", "NSE_FO|58419", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 240.0, "CE",  "NSE_FO|240CE", 3000),
        ("WIPRO LTD", "WIPRO", "2026-08-25", 250.0, "CE",  "NSE_FO|250CE", 3000),
    ]
    o, f, inst, snap = _full_env(chain, inst_rows,
                                 fut_rows=[("WIPRO", EXP, 241.0, TRADE_DATE)])
    md = _StubMD(ltps={"NSE_FO|58419": 249.0},
                 quotes={"NSE_FO|250CE": {"best_bid": 3.98, "best_ask": 4.02,
                                          "oi": 9000, "volume": 6000},
                         "NSE_FO|240CE": {"best_bid": 5.98, "best_ask": 6.02,
                                          "oi": 9000, "volume": 6000}})
    r1 = _build_contracts(o, f, inst, [("WIPRO", "LONG")], 7, TRADE_DATE, md)[0]
    r2 = _build_contracts(o, f, inst, [("WIPRO", "LONG")], 7, TRADE_DATE, md)[0]
    assert r1["strike"] == r2["strike"] == 250.0
    assert r1["screen"] == r2["screen"] == "pass"
```

- [ ] **Step 2: Run the stability test**

Run: `python -m pytest tests/analytics/test_options_selection.py -k stable_across_two -v`
Expected: PASS immediately (Task 4 makes `_build_contracts` deterministic). If it FAILS, there is nondeterminism in Task 4 to fix before proceeding.

- [ ] **Step 3: Expose the new fields in `/api/options`**

In `flask_app/blueprints/ts_basis_daily.py`, in `api_options`, replace the per-contract `out.append({...})` dict with:

```python
        out.append({
            "ticker": c["ticker"],
            "direction": c["direction"],
            "opt_type": c["opt_type"],
            "expiry": str(c["expiry"]) if c["expiry"] else None,
            "strike": c["strike"],
            "settle": c["settle"],
            "oi": c["oi"],
            "lot_size": c["lot_size"],
            "instrument_key": c["instrument_key"],
            "tradingsymbol": c["tradingsymbol"],
            "premium_cost": c["premium_cost"],
            "snapped": c["snapped"],
            "anchor_source": c["anchor_source"],
            "screen": c["screen"],
            "screen_reason": c["screen_reason"],
            "spread_pct": c["spread_pct"],
            "best_bid": c["best_bid"],
            "best_ask": c["best_ask"],
        })
```

- [ ] **Step 4: Read the template, then add the marker + grey the flagged rows**

First read `flask_app/templates/ts_basis_daily/index.html` and identify how it renders each option contract (Alpine `x-for`/`x-text` vs a Jinja `{% for %}` loop). Add, per option row: a class that dims flagged rows and a small status cell. Use the idiom the file already uses — do not introduce a new one.

If the row uses Alpine (`x-for="c in ..."`):

```html
<tr :class="{ 'opacity-50': c.screen === 'no_tradeable_strike' }">
  <!-- existing cells … -->
  <td class="text-xs text-gray-400"
      x-text="c.screen === 'no_tradeable_strike' ? ('untradeable: ' + c.screen_reason)
              : (c.anchor_source === 'live' ? 'ATM live' : 'ATM EOD')"></td>
</tr>
```

If the row is server-rendered with Jinja (`{% for c in contracts %}`):

```html
<tr class="{{ 'opacity-50' if c.screen == 'no_tradeable_strike' else '' }}">
  <!-- existing cells … -->
  <td class="text-xs text-gray-400">
    {% if c.screen == 'no_tradeable_strike' %}untradeable: {{ c.screen_reason }}
    {% else %}{{ 'ATM live' if c.anchor_source == 'live' else 'ATM EOD' }}{% endif %}
  </td>
</tr>
```

Do not restructure the template beyond these additions.

- [ ] **Step 5: Run the selection suite + blueprint import check**

Run: `python -m pytest tests/analytics/test_options_selection.py -v`
Expected: PASS (all, including the stability test).

Run: `python -c "import flask_app.blueprints.ts_basis_daily"`
Expected: no import error (blueprint still imports after the dict change).

- [ ] **Step 6: Commit**

```bash
git add flask_app/blueprints/ts_basis_daily.py flask_app/templates/ts_basis_daily/index.html tests/analytics/test_options_selection.py
git commit -m "feat: expose anchor/screen fields on /api/options and mark freshness in panel"
```

---

### Task 7: Full-suite verification + docs

**Files:**
- Modify: `CLAUDE.md` (TS Basis Daily notes — one line on live selection)
- Test: whole selection suite + touched-module imports

**Interfaces:** none new.

- [ ] **Step 1: Run the full options-selection suite**

Run: `python -m pytest tests/analytics/test_options_selection.py -v`
Expected: PASS — all original tests plus the ~16 new ones.

- [ ] **Step 2: Run the broader analytics tests**

Run: `python -m pytest tests/analytics -v`
Expected: PASS (no collateral breakage).

- [ ] **Step 3: Update `CLAUDE.md`**

In the TS Basis Daily / Signal Engine section, add one line noting live selection:

> TS Basis Daily options selection is live-anchored: ATM struck on the live near-month futures LTP with a live bid/ask-spread + OI + volume tradeability screen (`MAX_SPREAD_PCT=5%`, `STRIKE_BAND=±3`, `MIN_OI=100`, volume ≥ 1 lot), falling back to EOD bhavcopy (`anchor_source`/`screen` labelled per contract) when the market is closed or the token is missing. Shared by `scripts/ts_basis_daily_options.py` and the `/ts-basis-daily/` panel via `core/analytics/options_selection.py`.

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: note live-anchored options selection for TS Basis Daily"
```

---

## Self-Review

**Spec coverage:**
- Live ATM anchor (live→EOD→synthetic) → Task 3 + Task 4 (`anchor_source`). ✓
- Live spread + OI + volume screen with thresholds → Task 1 (bid/ask) + Task 2 (pure screen) + Task 4 (wiring). ✓
- Candidate band ±3 → Task 4 `_band_candidates`. ✓
- Nearest-forward pick, snap on failure → Task 2 `pick_screened_strike` + Task 4 (`screen ∈ pass/snapped`). ✓
- Flag-not-drop `no_tradeable_strike` → Task 4 + Task 5 (CLI) + Task 6 (panel grey). ✓
- Skip-not-fail on no feed → Task 4 (`_EOD_ONLY` and feed-miss branch → `_fill_eod`, `screen="skipped"`). ✓
- Once-per-load stability → Task 6 stability test; panel cache already in `_resolve_contracts` (unchanged). ✓
- EOD regression → Task 4 Step 5 (full file green) + `_EOD_ONLY` path. ✓
- Adapter `depth` build-time check → Task 1 test `..._none_when_depth_absent` asserts graceful null (screen degrades, no crash). ✓
- Surfaces (CLI + panel + template) → Tasks 5, 6. ✓
- Greeks out of scope → not implemented. ✓

**Placeholder scan:** No TBD/TODO; every code step carries full code. The one template step deliberately instructs reading the file and matching its existing Alpine-vs-Jinja idiom (a real constraint, with both concrete variants supplied) rather than a placeholder.

**Type consistency:** `screen_candidate` / `pick_screened_strike` signatures match between Task 2 (definition) and Task 4 (use). Row fields (`anchor_source`, `screen`, `spread_pct`, `live_oi`, `live_volume`, `best_bid`, `best_ask`, `screen_reason`) are defined once in `_base_row` (Task 4) and consumed identically in Tasks 5/6. `_StubMD` exposes both `fetch_ltp_batch` and `fetch_quotes_batch`, matching the real adapter surface used by `_resolve_live_forwards` (Task 3) and `_build_contracts` (Task 4). `_inst_con` / `_full_env` seed an `EQ` row per name so `_future_key` and `_resolve_instrument` resolve.
