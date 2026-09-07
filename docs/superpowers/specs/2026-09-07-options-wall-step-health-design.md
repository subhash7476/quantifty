# Options-Wall step health — design

**Status:** APPROVED · 2026-09-07

## Problem

On 2026-09-07 the paper executor failed on every cycle from 10:51 to 14:30 with

    Constraint Error: Duplicate key "trade_id: 1" violates primary key constraint

101 times. Nothing surfaced. The poller wraps each step in `except Exception` and logs
`logger.warning`, and `_scan_persist_step` runs independently afterward, so the dashboard
kept rendering a five-condition farm gate — all green, "Farm row emitted this cycle" —
above an executor that could not open a trade. The outage was found by a human noticing
that the trades table had not grown.

The store defect is fixed (`b6106ea`). This spec addresses the reason it went unseen for
three and a half hours.

The repo already names this failure mode: *a freshness value that is printed but never
asserted is documentation, not a control.*

## Scope

All six swallow sites in `core/options_wall/poller.py`, currently identical:

| line | step | what it silently drops today |
|---:|---|---|
| 229 | `quotes` | quote-batch errors from Upstox |
| 245 | `analytics` | structural/GEX build failure |
| 250 | `executor` | **today's outage** — opens and manages |
| 255 | `scan_persist` | the farm list the dashboard renders |
| 259 | `close_request` | **operator manual closes** |
| 265 | `fetch` | chain fetch for one underlying |

`close_request` is the one to note: the same trap would swallow a failed manual exit while
the UI reported the click as accepted.

**Non-goals.** The per-step `try/except` structure stays — one underlying failing must not
stop the others, and today scan-persist and the snapshot store kept working correctly while
the executor was broken. No retries are added. The executor's own logic is untouched.

## Design

### 1. `core/options_wall/health.py` — classification and accumulation, no I/O

Pure and unit-testable.

```python
def classify(exc: BaseException) -> str   # "transient" | "structural"
```

**Transient** — expected, self-correcting, must not alert:

- `duckdb.IOException` whose message contains `used by another process` (34 occurrences in
  today's log; the documented cross-process lock)
- `duckdb.ConnectionException` (the documented same-process connection flip)
- `requests.RequestException` and subclasses (fetch/quotes)

**Structural** — a fault that will not fix itself, must alert:

- everything else, explicitly including `duckdb.ConstraintException`,
  `duckdb.CatalogException`, `KeyError`, `TypeError`, `AttributeError`, `ZeroDivisionError`

Structural is the **default**. Today's log contains `float division by zero` and a
`TypeError` from a stray test lambda — both real defects, both silently discarded. An
unrecognised exception is a defect until proven otherwise.

```python
class StepHealth:
    def record(self, step: str, underlying: str, exc: BaseException | None) -> Verdict
```

Keyed on `(underlying, step)`. Tracks `ok`, `kind`, `error_type`, `error_msg` (first 200
chars), `consecutive`, and `since` — the ISO timestamp of the first failure in the current
run. A success clears the entry and re-arms alerting.

`Verdict` tells the caller three things: the log level to use, whether to alert now, and
the record to serialise.

### 2. Alerting is edge-triggered

101 failures must produce **one** alert, not 101.

- **structural:** alert on the transition from ok to failing (`consecutive == 1`).
- **transient:** alert at `consecutive == ALERT_AT[step]`, default **10** — roughly 50 s at
  the 5 s cycle. Lock contention that persists that long is no longer contention.
- **`close_request` is the exception: `ALERT_AT["close_request"] = 1`.** It alerts on the
  first failure of either kind. A dropped manual exit means the operator believes a position
  is flat when it is not, and one missed 5-second cycle is enough to matter. Every other
  step can afford to wait out a lock; this one cannot.
- Re-arm only after a success. No repeat alert while a fault persists.
- Delivered through the existing `TelegramNotifier.send_message` in
  `core/alerts/telegram_notifier.py`. If the notifier is unconfigured or raises, that
  failure is logged and swallowed — health reporting must never take the poller down.

Message content: underlying, step, error type, first line of the message, `since`.

### 3. Poller integration

The six blocks collapse to one call:

```python
except Exception as exc:
    self._record_step("executor", name, exc)
```

`_record_step` logs at `WARNING` for transient and `ERROR` for structural — so counting
ERROR lines in the log answers "is anything actually broken?", which it could not today.
Each step also records its successes, so the health record distinguishes *ran and
succeeded* from *never ran this cycle*.

### 4. The heartbeat carries it

The poller already writes a heartbeat atomically (tmp file + `os.replace`,
`poller.py:122`). Extend that record with a `steps` block rather than adding a second file:

```json
{
  "status": "DEGRADED",
  "last_heartbeat": "2026-09-07T14:29:14",
  "pid": 23096,
  "rows_by_name": {"NIFTY": 74, "SENSEX": 82},
  "steps": {
    "NIFTY": {
      "executor": {"ok": false, "kind": "structural",
                   "error_type": "ConstraintException",
                   "error_msg": "Duplicate key trade_id: 1 violates primary key...",
                   "consecutive": 101, "since": "2026-09-07T10:51:54"},
      "scan_persist": {"ok": true}
    }
  }
}
```

`status` is `OK` when every step is ok and `DEGRADED` when any step is failing.

**Why the heartbeat file and not a table in the results DB:** the results DB is
single-writer, lock-contended, and read by Flask under a 30 × 0.5 s retry — and it is
precisely the component that broke. Health must not depend on the thing whose failure it
reports. The heartbeat file is already atomic and already written every cycle.

### 5. Surfacing

- **`GET /options-wall/api/health`** in `flask_app/blueprints/options_wall.py`, reading the
  heartbeat JSON. No DB access. Returns the `steps` block plus heartbeat age.
- **Health strip** on the wall page: one row per underlying, a chip per step, red with the
  error type and `since` when failing.
- **Gate banner.** When `executor.ok` is false, the farm-gate card renders a banner above
  it: *Gate passing, executor failing since 10:51 — no trades will open.* This is the exact
  false confidence that cost three hours today, and it is the one piece of UI that must
  exist.
- A heartbeat older than 60 s renders the whole strip grey/unknown rather than green —
  absence of news is not good news.

## Testing

| test | asserts |
|---|---|
| `classify` table | the five exception types actually seen in today's log land in the right bucket; an unknown exception is structural |
| accumulator | failure increments `consecutive` and pins `since`; success clears and re-arms |
| edge-trigger | 101 consecutive structural failures produce exactly 1 alert; success then failure produces a 2nd |
| transient threshold | 9 lock errors produce no alert; the 10th produces 1 |
| `close_request` threshold | a single transient `close_request` failure produces 1 alert immediately |
| poller wiring | a raising executor step records structural **and** `scan_persist` still runs |
| notifier failure | a raising notifier does not propagate out of `_record_step` |
| api | `/api/health` reports DEGRADED with the executor entry; a stale heartbeat reports unknown |

The regression bar: **replay today's failure and have it be visible within one cycle.**

## Resolved decisions

- **`close_request` alerts on the first occurrence** (operator decision, 2026-09-07),
  transient or structural. Expressed as `ALERT_AT["close_request"] = 1` against a default of
  10, so the threshold is data rather than a branch and other steps can be retuned without
  touching the classifier.
- Structural faults alert on the first occurrence for **every** step; the per-step threshold
  applies only to transient ones.
- The spec is otherwise approved as written. Status moves to APPROVED on this revision.
