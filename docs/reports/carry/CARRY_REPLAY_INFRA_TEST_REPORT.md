# Carry — Replay Backtest Infrastructure Test

**Status:** **FAIL — the replay path is not usable as a backtest engine as currently wired.**
**Date:** 2026-07-24. **Branch:** `carry/g1-index-store-repair`. **Windows touched:** TRAIN only
(`2016-03-31 → 2020-12-31`). **SEALED not read.** All probes read-only.

---

## 0. What was asked and what was done

The question was whether a backtest engine needed building. It does **not** — the platform already
has one: `LoopDriver` has native replay mode, and `core/database/providers/daily_bhavcopy.py`
(`DailyBhavcopyProvider`) is a built `MarketDataProvider` for daily-bar replay.

So the work became: **test that infrastructure.** This report records the measurement.

**The headline: the components work individually, and the composition does not.** Wiring them
together today produces a backtest with severe forward-looking bias.

---

## 1. Why this was never caught before

`DailyBhavcopyProvider` has **zero call sites and zero tests** in the repo (verified by grep and by
`tests/**/*daily_bhavcopy*` → no files). It was built for `CARRY_IMPLEMENTATION_BRIDGE.md` §5's
full-path parity gate and then never invoked.

§5 originally required *"run the production path through `LoopDriver` in backtest mode."* §5.2 then
de-risked that down to a cheap "rebalancer-only construction-parity sub-check" — explicitly
deferring "the daily-bar provider + full LoopDriver replay (the largest net-new plumbing)." **The
sub-check was done; the full replay never was.** What is marked GATE D PASS is:

- `parity_check.py` — imports `compute_target_book` directly. No driver.
- `carry_integration_check.py` — calls `CarryRebalancerHook.__call__()` directly on 3 hand-picked
  dates, with the formation date *handed in*. No driver, no bar streaming.

Neither exercises the continuous loop. This is the same failure shape §5.3 already recorded:
*verifying a duplicate of the production code proves nothing about the production loop.*

---

## 2. Component-level results — the provider works

| Check | Result |
|---|---|
| `futures_bhavcopy` FUTSTK span | 2016-02-11 → 2026-07-20, 1,422,979 rows, 363 underlyings |
| `carry_facts` formation dates | 126 total (2016-02-29 → 2026-07-20); **58 in TRAIN** |
| Provider load, 229 TRAIN symbols | 4.1 s — fast enough, not a bottleneck |
| Symbols returning >0 bars | **229 / 229** |
| Near-month close correctness | `ACC` 247 bars in 2017 = full trading year; OHLC values sane |

An early probe returning zero bars was **my probe's error**, not a defect: I sampled the first five
underlyings alphabetically across all 360 names, which are all recent listings (`ABB` enters F&O
only 2022-01-28). Recorded here because the misread could otherwise be repeated.

---

## 3. THE DEFECT — per-symbol cursors have no shared calendar

### 3.1 Mechanism

`LoopDriver._tick()` (`core/runtime/driver.py:656-672`) sweeps every configured symbol and pulls
**one bar per symbol per tick**:

```
for symbol in self._config.symbols:
    bar = self._provider.get_next_bar(symbol)
    if bar is None: continue
    self._clock.set_time(bar.timestamp)          # line 665
    if not rebalance_done and ...:               # line 670
        self._rebalance_hook(bar.timestamp, self._execution)
```

`DailyBhavcopyProvider` keeps an **independent integer cursor per symbol** (`self._indices[sym]`,
`daily_bhavcopy.py:94-100`). It has **no notion of a global trading calendar.** So "one bar per
symbol per tick" means *the Nth bar of each symbol* — and the Nth bar of `ACC` and the Nth bar of
`ICICIGI` are not the same date whenever the two names have different listing histories.

### 3.2 Measurement — real `LoopDriver`, not a replica

This was measured twice, deliberately. A first probe *replicated* the `_tick()` consumption loop —
which is precisely the §5.3 sin this report criticises ("verifying a duplicate of the production
code proves nothing about the production code"). So it was re-run against a **real
`LoopDriver(Mode.REPLAY)`**, constructed with `ReplayClock`, a real `ExecutionHandler` +
`PaperBroker`, the real `DailyBhavcopyProvider` behind a transparent pass-through observer, and an
observing `rebalance_hook`. `driver.run()` was called.

**The real driver reproduces the replica's numbers exactly.** First six ticks:

| tick | hook fired at | bars | earliest bar | LATEST bar | spread |
|--:|---|--:|---|---|--:|
| 1 | 2016-03-31 | 229 | 2016-03-31 | **2020-10-30** | **1674d** |
| 2 | 2016-04-01 | 229 | 2016-04-01 | 2020-11-02 | 1676d |
| 3 | 2016-04-04 | 229 | 2016-04-04 | 2020-11-03 | 1674d |
| 4 | 2016-04-05 | 229 | 2016-04-05 | 2020-11-04 | 1674d |
| 5 | 2016-04-06 | 229 | 2016-04-06 | 2020-11-05 | 1674d |
| 6 | 2016-04-07 | 229 | 2016-04-07 | 2020-11-06 | 1674d |

Every tick hands the driver all 229 symbols with bar dates spanning **more than four and a half
years**. This is observed behavior of the production loop, not an inference from it.

### 3.2.1 Full-window replica sweep

229 TRAIN-eligible symbols, TRAIN window, 1,173 ticks executed:

| Metric | Value |
|---|---|
| Bar-count spread across symbols | **min 42, max 1,173 bars** |
| Within-tick bar-date spread — median | **463 days** |
| Within-tick bar-date spread — max | **1,676 days** |
| Ticks with spread 0 (correctly aligned) | **124 / 1,173 (10.6%)** |

**Only ~11% of ticks feed the engine a coherent single-date cross-section.**

### 3.3 Smoking gun — tick 1 delivers 2020 prices while the clock says 2016

On the **very first tick**, with the rebalance hook firing at **2016-03-31**:

| Symbol | Bar delivered on tick 1 | Days ahead of hook date |
|---|---|--:|
| ICICIGI | **2020-10-30** | **1,674** |
| SBILIFE | 2020-05-04 | 1,495 |
| GODREJPROP | 2020-03-27 | 1,457 |
| BANDHANBNK | 2020-02-28 | 1,429 |
| HDFCLIFE | 2020-02-28 | 1,429 |
| NAUKRI | 2020-02-28 | 1,429 |
| TATACONSUM | 2020-02-27 | 1,428 |
| IDFCFIRSTB | 2019-01-16 | 1,021 |

**34 of 229 symbols deliver a bar more than a year ahead of the hook date on tick 1.**

These are exactly the names that listed late — the provider has no way to know a symbol should be
*absent* early rather than *starting* early, because absence and "cursor at position 0" are the same
state to it.

### 3.4 Consequence

This is disqualifying for a backtest, on three counts:

1. **Forward-looking bias.** A 2020 price is visible to the engine on a 2016 tick. Any mark-to-
   market, fill, or valuation touching those names uses prices from years in the future.
2. **The clock is driven incoherently.** `set_time(bar.timestamp)` is called per bar within a
   single tick, so the deterministic clock jumps forward and back across years inside one
   iteration — breaking the ADR-003 determinism guarantee the driver rests on.
3. **The price cache is poisoned.** The handler's cache is warmed on every bar (`driver.py:673`),
   so it accumulates prices tagged with the wrong dates.

**A net-spread number produced by this path today would be wrong, and wrong in the flattering
direction** — lookahead bias generally inflates measured performance. Had this been run and its
output believed, it would have been a parity "PASS" resting on contaminated prices.

### 3.5 Secondary defect — `get_latest_bar` exposes an unconsumed bar

`daily_bhavcopy.py:107-110`: when a symbol's cursor is at 0, `get_latest_bar` returns `bars[0]` —
a bar that has **not yet been consumed**. Measured: returns a bar dated 2016-03-31 at
`progress=(0, 311)`. That is a peek at unreleased data. Smaller than §3.3 and possibly never hit
depending on call order, but it is the same class of bug and should be fixed in the same pass —
correct behavior is to return `None` before any bar is consumed.

---

## 4. What the hook *would* see (the one piece that is fine)

Hook-visible dates: **1,173 distinct**, spanning 2016-03-31 → 2020-12-31, hitting **58 / 58 TRAIN
formation dates, zero missed.**

This is worth stating precisely so it is not over-credited: it holds because the hook takes its
timestamp from the *first symbol in the sweep that yields a bar*, and that symbol happens to carry a
full 1,173-bar history. It is **not** evidence the loop is sound — it is a property of alphabetical
ordering, and it would break the moment the first-listed symbol had a gap. The formation-date
*detection* logic is fine; the *data* arriving alongside it is not.

---

## 4.5 Scope — this is wider than Carry

Before recommending net-new plumbing, the repo was checked for an existing calendar-aware provider
to reuse. There is none, and the check turned up something larger.

| Provider | Cursor model | Exposure |
|---|---|---|
| `DailyBhavcopyProvider` | `_indices: Dict[str, int]`, positional | **Defective as measured above** |
| `DuckDBMarketDataProvider` (`market_data.py:58,110-121`) | `_indices: Dict[str, int]`, positional — **identical architecture** | **Same latent defect** |
| `live_market.py`, `zmq_market.py` | live feeds, not replay | N/A |

**The defect is in the provider layer's contract, not in `DailyBhavcopyProvider` specifically.**
`DuckDBMarketDataProvider` — the general historical provider used for equity replay — advances by
per-symbol bar index in exactly the same way, so any **multi-symbol** replay through it carries the
same misalignment.

Two mitigating facts, stated so this is not overclaimed:

- **MSI, the only existing replay runner, is single-symbol** (`msi_paper_runner.py:57`,
  `symbols=[traded_symbol]`). With one symbol there is no cross-symbol alignment to break, so MSI's
  results are unaffected and no prior MSI work is called into question.
- On **intraday 1m equity data over a short window**, symbols with identical session coverage keep
  their cursors incidentally aligned; drift appears only where bars are missing. That is a much
  milder exposure than Carry's multi-year listing-history problem — but it is drift that nothing
  currently detects, because no test asserts alignment.

**This has not been measured for `DuckDBMarketDataProvider`** — it is a code-structure finding, and
is flagged for measurement rather than asserted as a live failure.

---

## 5. Recommended fix — make the provider calendar-driven

The defect is in the provider contract, not in `LoopDriver` and not in the Carry construction. **No
construction parameter changes; this is plumbing only** (§8 no-re-optimization guardrail is not
engaged).

Direction: the provider should advance by **trading date**, not by per-symbol bar index.

- Build the union of trading dates across the loaded window once, at load time.
- Hold a single global cursor over that date list.
- `get_next_bar(symbol)` returns the bar for the *current global date* if that symbol traded that
  day, else `None` — so a not-yet-listed name is correctly **absent**, not early.
- Advance the global cursor when the sweep completes a date.
- Fix `get_latest_bar` to return `None` before first consumption (§3.5).

Acceptance test for the fix, to be committed alongside it — the check that would have caught this:

> **Within-tick bar-date spread must be exactly 0 for 100% of ticks**, and the tick count must equal
> the number of trading dates in the window.

This is the missing regression test; today's measurement (median spread 463 days, 10.6% aligned)
is its baseline.

**Alignment is necessary, not sufficient — do not read a green alignment test as a closed gate.**
The §5 gate is that a LoopDriver replay *reproduces the research net spread* (`parity_check.py`'s
+0.0 bp). Fixing alignment only makes the replay **eligible** to attempt that comparison. The
sequence is: fix provider → alignment test green → *then* run the full replay and compare net
spread → only then is §5 closed as originally worded.

---

## 6. Verdict and what is NOT claimed

**FAIL.** The backtest engine exists and does not need to be built. It is **not yet fit to run**:
`DailyBhavcopyProvider` cannot feed `LoopDriver` a coherent daily cross-section, so the §5 full-path
replay gate cannot be closed until the provider is made calendar-driven.

Explicitly **not** claimed here:

- **Nothing about the Carry signal.** The construction, sign, and fee model are untouched and
  unquestioned. This is a data-plumbing defect.
- **Nothing invalidated in prior gates.** `parity_check.py` and `carry_integration_check.py` do not
  route through this provider, so their results stand. What was mis-stated is only **coverage** —
  §5's "production path" gate was closed on a narrower path than §5 specified.
- **No net-spread number was produced**, deliberately. Producing one from this path before the fix
  would be producing a contaminated number.

### 6.1 Bridge-document markers that overstate coverage

`CARRY_IMPLEMENTATION_BRIDGE.md` should be annotated — **not rewritten, and no gate result
reversed** — because two markers read stronger than what was actually run:

- **§5 "Status: PASSED"** is worded as *"the production path reproduces the research net spread."*
  What passed is construction parity via direct import. The **LoopDriver replay named in §5's own
  requirement was never executed** — this report is the first time it has been run at all.
- **§6 step 4** is marked integration-CLOSED on `carry_integration_check.py`, which drives the hook
  directly with formation dates handed in. Sound for what it tests; it is not a driver-loop test.

Neither marker is *false* about what its script measured — both are **narrower in coverage than
their wording implies**. The risk is a go-live decision resting on "the production path is
verified" when the production *loop* has never run a clean bar. Flagging now, before step 5 (LIVE),
is the whole point.

---

## 7. Reproduction

Measurements came from four read-only probes (session scratchpad, not committed — they are
diagnostics, superseded by the §5 acceptance test above once written):

1. Provider smoke — schema, span, load timing.
2. Zero-bar isolation — proved the early null result was probe error, not defect.
3. `_tick()` sweep replication — the §3.2.1 full-window alignment table.
4. Tick-1 lookahead — the §3.3 table.
5. **Real `LoopDriver(Mode.REPLAY)` run** — the §3.2 table. This is the load-bearing one; probes
   3–4 are replicas and are corroborating only.

The durable artifact should be the §5 acceptance test committed under `tests/`, which does not
exist yet.
