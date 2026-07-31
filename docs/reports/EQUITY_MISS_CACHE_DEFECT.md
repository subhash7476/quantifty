# Equity Bhavcopy — Permanent Negative Cache Poisoned by Forward Probing

**Found:** 2026-07-31, 19:30 IST
**Component:** `scripts/csmp/ingest_equity_bhavcopy.py`
**Severity:** **HIGH** — silent, unbounded data staleness with a success-reporting pipeline
**Status:** Data remediated; code patched; regression-tested

---

## 1. Summary

A single ingest run on **2026-07-09** probed dates up to five months into the
future, received the inevitable HTTP 404 for dates that had not yet occurred, and
wrote **289 permanent "this date is absent" marker files** covering **every date
from 2026-08-01 to 2026-12-31**.

Those markers short-circuit all future fetches. Equity ingestion for the rest of
the calendar year would have been silently skipped — while the EOD automation
chain reported `success` every single night.

The defect was already live: `equity_bhavcopy` was frozen at **2026-07-29** while
futures, index, and stock-options had all advanced to 2026-07-31.

**It was found by the operator noticing that a Telegram options book listed
yesterday's names** — not by any test, gate, or alert.

---

## 2. Root cause

`fetch()` caches confirmed-absent dates so re-runs are resumable:

```python
if miss_path.exists():
    return None                     # short-circuit, never re-fetches
...
if resp.status_code == 404:
    miss_path.write_bytes(b"")      # permanent, no expiry
    return None
```

The cache is sound for a **closed** date: a 404 for 2019-03-04 means the archive
genuinely lacks it. It is invalid for a date that has not closed, where 404 means
only *"not published yet"* — and nothing ever expires the marker or re-checks.

**A run that probes forward dates therefore permanently poisons them.** No error
is raised, no warning logged; the date simply becomes invisible forever.

### Evidence

| Check | Result |
|---|---|
| `.404` markers for dates ≥ today | **288** (`secfull` 144, `udiff` 143, `foudiff` 1) |
| Range covered | 2026-08-01 → 2026-12-31 |
| Marker mtime for `secfull_20260730.404` | **2026-07-09** — three weeks before the date existed |
| Live HTTP status, 2026-07-30 `secfull` | **200**, 369,680 bytes |
| Live HTTP status, 2026-07-31 `secfull` | **200**, 371,072 bytes |

The data was downloadable the entire time. The ingest never asked.

---

## 3. Why it stayed invisible

Three independent mechanisms had to align, and did:

1. **The negative cache is silent by design.** A cached miss is indistinguishable
   from a genuine holiday in every log line and summary counter. The ingest
   summary printed `Dates absent (404): 2` — technically true of the cache,
   false about the world.
2. **The EOD chain gates on the wrong feed.** `eod_decision.decide()` fires the
   chain when **futures** publishes and never inspects equity freshness. The
   download step's exit code is *deliberately* ignored (a documented design
   choice, since sub-ingests 404 routinely on holidays). So a totally failed
   equity ingest cannot produce anything but `success`.
3. **The staleness surfaced only in derived output.** `equity` feeds the
   futures⋈spot join, so `ts_facts.MAX(formation_date)` tracked the stale equity
   date exactly, and the options book inherited it:

   ```
   equity_bhavcopy   max 2026-07-29
     → ts_facts      MAX(formation_date) 2026-07-29
       → options book target 2026-07-29    ← what Telegram sent
   ```

   The Telegram message did print `old equity: 2026-07-29` — accurate, adjacent
   to three `OK` lines, and easy to read past.

**This is the repo's own documented pitfall recurring in a new form.** CLAUDE.md
already records: *"a bare `except: pass` around a download turns 'we failed' into
'the source doesn't have it' — and that claim then gets written into a governance
report as a fact about the world. 46 downloadable NSE sessions were recorded as
permanent archive gaps this way."* The mechanism differs — here the classification
was correct at the moment it was made and became false with the passage of time —
but the outcome is identical: **downloadable sessions recorded as permanent gaps.**

---

## 4. Remediation

### Data

Markers were separated by a criterion that requires no judgement: **a marker
written on or before the date it declares absent cannot be valid evidence**, since
absence cannot be observed before the date exists. Genuine holiday markers are
written after the fact.

| Class | Count | Action |
|---|---|---|
| Premature (`mtime ≤ marker date`) | **289** | deleted |
| Plausible (`mtime > marker date`) | 4,256 | **kept** |

Re-ingest recovered the two missing sessions:

```
2026-07-30  secfull  2693 rows
2026-07-31  secfull  2696 rows
Rows inserted: 5,389    Dates absent (404): 0    Dates fetch-failed: 0
```

All four feeds now current at 2026-07-31, `ts_facts` rebuilt to formation date
2026-07-31 (208 rows), and the chain returned `success — 3 chain steps ok`.

Deleting a marker is non-destructive: worst case a genuine holiday costs one
HTTP request and the marker is rewritten.

### Code

`_may_cache_miss()` gates both write sites (the equity path in `fetch()` and the
F&O path):

```python
def _may_cache_miss(d: date) -> bool:
    return d < date.today()
```

A 404 for a date that has not closed is now returned as absent for *this run
only* and never persisted. Closed-date caching — the behaviour the cache exists
for — is unchanged.

### Tests — `tests/csmp/test_bhavcopy_miss_cache.py` (7)

Written before the fix and confirmed failing for the stated reason (3 on the
missing guard, 2 on markers actually being written for today/future; the 2
covering correct existing behaviour passed throughout).

- guard rejects future date / today, allows closed date
- `fetch()` writes no marker on 404 for a future date
- `fetch()` writes no marker on 404 for today
- `fetch()` **still** caches a 404 for a closed date
- a cached miss still short-circuits without an HTTP call

`tests/csmp/` 70 passed. `tests/scheduler/` 66 passed.

---

## 5. What is *not* fixed

1. **The EOD chain still cannot fail on a stale equity feed.** `decide()` gates on
   futures alone. The guard above stops this specific cause of silent staleness;
   it does not make the pipeline capable of *reporting* staleness from any other
   cause. A freshness assertion across all four feeds — failing the run, not
   printing `old` in passing — is the durable fix and is **not implemented**.
2. **Whatever ran on 2026-07-09 probed five months of forward dates.** That caller
   was never identified. The guard makes forward probing harmless, so this is no
   longer urgent, but the behaviour is unexplained and may be wasting requests.
3. **Sibling ingests were not audited.** `scripts/sfb/ingest_futures_bhavcopy.py`
   references `.404` markers in its docstring. Only
   `ingest_equity_bhavcopy.py` was inspected and patched; the futures and options
   ingests have not been checked for the same pattern.
4. **The 4,256 retained markers were not individually validated.** They pass the
   mtime test, which makes them plausible, not verified. Any that were written by
   a *transient* failure misclassified as 404 remain — the same class of error,
   older.

---

## 6. Lessons

- **A cache entry whose correctness depends on the time it was written needs an
  expiry or a validity precondition.** "Absent" is not a timeless property of a
  future date.
- **Freshness must be asserted, not printed.** `old equity: 2026-07-29` sat in
  every notification for two days and nothing consumed it. A field no code checks
  is documentation, not a control.
- **Gating a multi-feed pipeline on one feed makes the others optional.** Futures
  was the trigger; equity silently became best-effort.
- **The only detector that worked was a human recognising yesterday's list.**
  Every automated layer reported success. That is the finding to sit with.
