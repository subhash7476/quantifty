# MM9.4-S2 Implementation Specification
## SPAN Parameter Sourcing

**Status:** PENDING IMPLEMENTATION
**Preceded by:** MM9.4-S1 — MarginCalculator Protocol & SPAN Substitution Seam (COMPLETE, ADR-007, 728 tests passing)
**Followed by:** MM9.4-S3 — SpanMarginCalculator Implementation
**Date drafted:** 2026-06-28
**Type:** Architecture + specification only. **No production code. No patches. No commits.**

---

## 0. Reading Guide — What S2 Ships vs What S2 Designs

S2 is the **data-foundation** slice. It acquires, validates, versions, archives, and exposes a
read path for SPAN parameter data. It performs **no margin calculation** and touches **no runtime,
gate, execution, or telemetry path**.

| Scope | Content |
|---|---|
| **S2 CODE scope** (what an engineer ships) | An offline fetch/validate/publish/archive job (`scripts/fetch_span_params.py`); the immutable `SpanSnapshot` DTO family (`core/risk/span/`); a `schema_version`-keyed parser; a pure read-path repository (`SpanParameterRepository`); a freshness calendar + a READY/REFUSE readiness verdict + a `build_span_readiness()` injectable callable. **No driver edit. No calculator. No gate wiring.** |
| **S2 DOCUMENT scope** (what this spec designs) | The startup-gate integration sequence (§5) and the S3 consumption contract (§ Design Q9). These are **designed here so S3 has no architectural decisions left** — but S2 wires nothing into the driver. |

This mirrors the established instrument-master precedent exactly: `build_master_readiness()`
(`core/instruments/master_readiness.py:88-104`) returns the injectable readiness callable, while
its *"live invocation … lands with the F&O runtime slice"*. S2 builds the parallel SPAN callable;
the slice that needs SPAN params at startup (S3/S4) wires it. **The producer (fetch job) and the
read path are S2; the consumer (`SpanMarginCalculator`) and the driver wiring are S3/S4.**

**The instrument-master pipeline is the authoritative template** (`scripts/fetch_instrument_master.py`,
`master_freshness.py`, `master_readiness.py`). S2 follows its proven shape — stage → validate →
promote, point-in-time versioning, pure-verdict readiness — and **deviates only where SPAN
genuinely differs** (storage weight, staleness tolerance), each deviation called out explicitly.

**The S2 deliverable, in one sentence:** make a versioned, integrity-verified, immutably-archived
SPAN parameter snapshot acquirable offline and loadable deterministically by date — so that
MM9.4-S3's `SpanMarginCalculator` can receive one already-validated `SpanSnapshot` at construction
with zero coupling to how it was sourced.

---

## 1. SPAN Data Model

### 1.1 Storage-weight decision (read first — it shapes §3 and §4)

**Decision: SPAN parameters are parsed into an immutable in-memory `SpanSnapshot` DTO from an
archived raw file. There is NO DuckDB store and NO database.** This is a *conscious deviation* from
the instrument-master template, not an oversight.

The instrument master uses DuckDB because it is ~66k rows queried per-symbol on every tick
(`fetch_instrument_master.py:18-23`). SPAN risk parameters are orders of magnitude smaller — a
bounded set of per-underlying scan ranges / risk arrays (hundreds of values, not tens of thousands),
read once at calculator construction (S3), never per-tick-queried by symbol. A normalized database
is unjustified weight here and would trip the "no over-engineering" convention (`CLAUDE.md`) and the
explicit S2 non-goal "persistence redesign." The right-sized store is **the immutable raw file on
disk (the integrity anchor) + an in-memory DTO parsed from it once.**

If, at implementation time, the confirmed NSE parameter volume proves large enough to need indexed
query (it is not expected to), DuckDB may be reconsidered — but only justified against measured
volume, never by mirroring the master.

### 1.2 Immutable DTO family

All DTOs are `@dataclass(frozen=True)` (ADR-007 immutability; mirrors `CanonicalInstrument`,
`PortfolioSnapshot`, `ReadinessVerdict`). They live in `core/risk/span/span_snapshot.py`.

```python
@dataclass(frozen=True)
class SpanRiskArray:
    """One underlying's SPAN risk parameters. Field set is the MARGIN-CALC-FACING
    minimum (what S3 consumes), deliberately decoupled from NSE's raw file layout
    (§2.3). Concrete fields are confirmed against NSE's published spec at S3
    implementation time; the names below are the design intent."""
    underlying: str                     # canonical underlying symbol (e.g. "NIFTY")
    price_scan_range: float             # the scanning range (price shift)
    volatility_scan_range: float        # the volatility shift
    scan_points: tuple[float, ...]      # the SPAN scenario risk values (immutable tuple)
    # … additional confirmed-at-S3 fields (short-option minimum, spread charges)


@dataclass(frozen=True)
class SpanSnapshot:
    """ONE immutable point-in-time SPAN parameter set. This is the object S3's
    SpanMarginCalculator receives at construction (Design Q2). Frozen; holds only
    immutable members (tuple of arrays, not list)."""
    version: date                       # version identity = snapshot_date (§3.1)
    exchange: str                       # "NSE" (exchange metadata)
    schema_version: str                 # parser-registry key (§2.3, Design Q6)
    source_url: str                     # provenance (audit)
    fetch_timestamp_ist: datetime       # when acquired, IST (§1.3)
    checksum_sha256: str                # integrity hash of the raw source file (§2.5)
    risk_arrays: tuple[SpanRiskArray, ...]   # the parameters, one per underlying

    def array_for(self, underlying: str) -> Optional[SpanRiskArray]:
        """Pure lookup. Missing underlying → None (S3 decides rejection, §6 F-MISS)."""
        ...
```

### 1.3 Schema, version identifiers, timestamps, exchange metadata

| Concern | Specification |
|---|---|
| **Schema** | The parsed DTO schema (above), versioned by `schema_version` (§2.3). The *raw-file* schema is NSE's and is **not modelled** — the parser registry isolates it from the DTO (Design Q6). |
| **Version identifier** | `SpanSnapshot.version: date` — the NSE publication / trading date the parameters apply to (§3.1). Exactly the `snapshot_date` identity the master uses (`fetch_instrument_master.py:22`). |
| **Timestamps** | `fetch_timestamp_ist` recorded in **IST**, never machine-local — the same finding the master encodes (`fetch_instrument_master.py:217-225`, `ist_snapshot_date`). The version `date` is also IST-derived. |
| **Exchange metadata** | `exchange` ("NSE"), `source_url`, `schema_version`, `checksum_sha256` — the provenance + integrity fields, surfaced in the per-snapshot manifest (§3.3) and the audit record (Design Q5). |

### 1.4 Ownership

| Artifact | Owner | Notes |
|---|---|---|
| Raw archived file + manifest (on disk) | The **fetch job** (producer, S2). | Immutable once published. The integrity anchor + source of truth. |
| `SpanSnapshot` DTO (in memory) | The **consumer that loads it** — `SpanMarginCalculator` at construction (S3). **In S2 there is NO live component holding a snapshot.** | The repository (§4) is a pure read path that *returns* a `SpanSnapshot`; it does not retain one. |
| The readiness **verdict** | The **startup gate** (consumer of `build_span_readiness()`), wired in S3/S4. S2 builds the callable. | "Does a fresh, valid snapshot exist?" — distinct from "load it into memory" (§4.1). |

The ownership split (verdict vs load) is load-bearing and stated explicitly so S3 does not blend
them: **S2 answers "is a valid snapshot available?"; S3 answers "load it and own it."**

---

## 2. Parameter Source

### 2.1 Supported source

**Primary source: NSE-published daily SPAN risk parameter files.** NSE publishes SPAN parameters as
static daily files — the reproducible artifact a deterministic replay requires (§7). This is the
source S1 §5.1 already committed to and ADR-007 boundary rule #3 presupposes ("SPAN parameters
sourced from exchange data are immutable once loaded").

**Rejected for the hot path: the Upstox / broker margin API.** A live margin API returns
time-varying, rate-limited, non-reproducible values and is forbidden inside any margin path by
ADR-007 rule #4 and ADR-003. It is permitted **only** out-of-band (offline reconciliation of our
SPAN estimate vs broker truth — a diagnostics tool, never a source for the session snapshot).

> **Implementation-time confirmation required (do NOT fabricate):** the exact NSE source URL, the
> raw file format/extension, the field layout, and the daily publish cutoff are **external facts**
> that must be confirmed against NSE's published specification at implementation time. This spec
> deliberately does **not** invent them. They are captured as **named constants flagged for
> confirmation** (§9, `fetch_span_params.py`: `SPAN_SOURCE_URL`, `SPAN_SCHEMA_VERSION`,
> `SPAN_REFRESH_CUTOFF`) and isolated from the DTO by the parser registry (§2.3 / Design Q6). The
> spec's correctness does not rest on the guessed layout — only on the *architecture* around it.

### 2.2 Download strategy

Mirrors `run_refresh` (`fetch_instrument_master.py:291-318`): an **offline, scheduled, OS-driven
job** runs once per NSE trading day, before the load any session performs. The CDN/file fetch is
unauthenticated where possible (decoupled from OAuth, like the master). The job is the **only**
component that performs a network download — never the runtime (§7).

### 2.3 File format + parser registry (Design Q6 — future schema changes)

The raw NSE file format is parsed by a **registry of parsers keyed by `schema_version`**
(`core/risk/span/span_parser.py`):

```
parse(raw_bytes, schema_version) → routes to the parser registered for schema_version
                                  → returns tuple[SpanRiskArray, ...]
unsupported schema_version       → raises UnsupportedSpanSchema (→ refuse, §6 F-SCHEMA)
```

This single mechanism answers two requirements at once:
- **Future exchange schema changes (Q6):** a new NSE format ships a new parser under a new
  `schema_version`; old archived snapshots keep parsing under their original key. No snapshot is
  ever silently reinterpreted by a parser it was not produced for.
- **Insulation from the unconfirmed format:** the DTO (§1.2) is the margin-calc-facing minimum; the
  parser absorbs whatever the raw layout is. Confirming the raw layout at S3 time changes only a
  parser body, never the DTO or any consumer.

### 2.4 Validation

Validate-before-publish, identical in shape to the master's `validate_and_publish`
(`fetch_instrument_master.py:242-273`):

1. **Shape guard** — the parsed arrays are well-formed (every traded underlying present; scan ranges
   numeric and non-negative; arrays non-empty). Parallel to `_contract_shape_ok`
   (`fetch_instrument_master.py:228-239`). Failure → refuse to publish; prior snapshot preserved.
2. **Coverage guard** — a `SpanRiskArray` exists for every traded underlying
   (`DEFAULT_UNDERLYINGS = ("NIFTY", "BANKNIFTY")`, mirroring the master). Missing coverage → refuse
   to publish.
3. **Staging → promote** — write to a throwaway staging location, validate there, and **only on
   success** promote to the archive (`fetch_instrument_master.py:258-270`). A bad download never
   replaces the prior good snapshot.

### 2.5 Integrity verification + the reproducibility chain

The integrity chain is explicit and one-directional:

```
raw NSE file  ──(sha256 at fetch)──►  checksum recorded in manifest
     │                                         │
     │ (the integrity anchor + source of truth)│
     ▼                                         ▼
parser[schema_version]  ──(deterministic)──►  SpanSnapshot(version, checksum, …)
```

- The **raw archived file is the source of truth**; its `sha256` is the integrity anchor.
- Parsing is a **deterministic, total function of (raw bytes, schema_version)** — same input →
  byte-identical `SpanSnapshot`.
- On every load (§4), the repository **re-computes the raw file's sha256 and asserts equality**
  against the manifest's `checksum_sha256`. A mismatch → refuse (§6 F-CKSUM). This is what makes
  "same input → same snapshot" *verifiable*, not merely asserted.

### 2.6 Why these choices preserve deterministic replay

Static daily files (not a live API) + immutable archive + deterministic schema-keyed parsing +
checksum verification ⇒ the snapshot for any given `version` date is **bit-reproducible forever**. A
replay loads the *same archived file*, parsed by the *same `schema_version` parser*, verified by the
*same checksum* — and obtains the *same `SpanSnapshot`* the live session used (§7).

---

## 3. Versioning

### 3.1 Version identity

`SpanSnapshot.version: date` = the NSE trading date the parameters apply to, computed in **IST**
(`ist_snapshot_date` pattern, `fetch_instrument_master.py:217-225`). One date ⇒ one canonical
snapshot. This is identical to the instrument-master `snapshot_date` identity, so the two reference
datasets version on the same axis and can be cross-checked by date.

### 3.2 Naming

Archive entries are named by ISO date (`YYYY-MM-DD`), the unambiguous, sortable, IST-derived
identity. No build numbers, no hashes-as-names (the hash is integrity metadata, not identity).

### 3.3 Storage layout + archive policy

```
data/risk/span/
  archive/
    2026-06-26/
      span_raw.<ext>          # the immutable raw NSE file (source of truth)
      manifest.json           # provenance + integrity (the audit record, Design Q5)
    2026-06-27/
      span_raw.<ext>
      manifest.json
    2026-06-28/
      …
```

`manifest.json` (one per snapshot) records, in ISO/IST:

```json
{
  "snapshot_date": "2026-06-28",
  "exchange": "NSE",
  "source_url": "<SPAN_SOURCE_URL — confirm at impl time>",
  "fetch_timestamp_ist": "2026-06-28T08:31:04+05:30",
  "schema_version": "nse-span-v1",
  "sha256": "<64-hex of span_raw.<ext>>",
  "array_count": 2
}
```

**Archive policy:**
- **Append-only, immutable.** A published snapshot directory is never mutated. Re-running the job
  for an already-published date is idempotent (re-stage, re-validate; replace only if the date's
  entry is absent — never silently overwrite a good prior file, consistent with
  `fetch_instrument_master.py:188-199` transactional preservation).
- **Multiple historical snapshots coexist** (Design Q7) — each date is its own directory; nothing is
  pruned by the job. Retention/pruning, if ever needed, is a separate operational policy (out of S2
  scope; non-goal "persistence redesign").

### 3.4 Reproducibility requirements

1. A `version` date maps to exactly one archived raw file + checksum (§3.1, §3.3).
2. Parsing is deterministic and schema-keyed (§2.3, §2.5).
3. Replay selects a snapshot by **hard version equality**, not "latest ≤ as_of" (§ Design Q3/Q8, §7).
4. The session records the loaded `version` (+ checksum, schema_version) in the audit record so the
   exact snapshot is reconstructable (Design Q5).

---

## 4. Loader Architecture

### 4.1 Two distinct operations — do not blend them

| Operation | What it answers | Who, when | S2 deliverable |
|---|---|---|---|
| **Readiness verdict** | "Does a fresh, valid snapshot exist on disk for the expected date?" | The **startup gate**, via `build_span_readiness()`. Wired S3/S4. | The verdict module + injectable callable (§4.3). |
| **Load into memory** | "Parse the snapshot and hold it." | **`SpanMarginCalculator` at construction** (S3), via the repository read path. **No S2 component holds a snapshot.** | The pure read-path repository (§4.2). |

The instrument master encodes exactly this separation: `master_readiness.assess()` produces the
verdict; the `InstrumentResolver` performs reads. S2 reproduces it for SPAN.

### 4.2 The pure read-path repository

`core/risk/span/span_repository.py` — `SpanParameterRepository`:

```
latest_version() -> Optional[date]
    The newest archived snapshot date (None if archive empty).

load(version: date) -> SpanSnapshot
    Read archive/<version>/, verify sha256 (§2.5), parse via schema_version
    registry (§2.3), return the immutable SpanSnapshot. Raises on any failure
    (missing dir, checksum mismatch, unsupported schema) — never returns a
    partial or fallback snapshot (§6, refuse > warn > fallback).
```

The repository is **stateless and side-effect-free** beyond reading files — it returns a value, holds
nothing, mutates nothing (ADR-001: it is downstream of no ledger; it is reference data). It performs
**no network I/O** — it reads only the local archive (§7).

### 4.3 Readiness verdict + injection

`core/risk/span/span_readiness.py`, mirroring `master_readiness.py`:

```
evaluate(latest: Optional[date], expected: date) -> SpanReadinessVerdict   # pure
assess(repository, now=None) -> SpanReadinessVerdict                       # gathers facts
build_span_readiness(*, archive_dir=None, as_of=None) -> Callable[[], SpanReadinessVerdict]
```

`build_span_readiness()` returns the **zero-arg injectable callable** the startup gate consumes —
the exact analogue of `build_master_readiness()` (`master_readiness.py:88-104`). It constructs the
repository once and closes over it. **Evaluation only — it never downloads, refreshes, or repairs**
(the master's Decision 6, carried over).

### 4.4 Dependency injection + ownership of loaded data

- **Composition root injects** (ADR-MM7E-1): the F&O entry script (`scripts/fno_runner.py`, S3/S4)
  constructs the repository, loads the active `SpanSnapshot`, and passes it to
  `SpanMarginCalculator(span_snapshot=…)` — and passes `build_span_readiness()` into the driver's
  startup gate. **S2 does neither wiring; it provides both building blocks.**
- **Ownership of the loaded snapshot:** `SpanMarginCalculator` (S3). It holds the frozen
  `SpanSnapshot` as immutable construction-time configuration (permitted by ADR-007 rule #1 — config
  is allowed, portfolio state is not). Its methods stay stateless w.r.t. positions/prices.

### 4.5 Lifecycle

```
(offline, daily)  fetch job → validate → publish immutable archive/<date>/   [S2 producer]
(startup, once)   composition root: repository.load(active_version) → SpanSnapshot
                  → inject into SpanMarginCalculator (construction)            [S3 consumer]
(startup gate)    build_span_readiness()() → verdict → READY/REFUSE           [S3/S4 wiring]
(session)         snapshot frozen in the calculator; never reloaded           [S3]
(shutdown)        snapshot discarded; next day a new archive entry exists     [—]
```

---

## 5. Startup Gate (Target Design — S2 wires nothing)

S2 **designs** the gate integration so S3/S4 implement it with no decisions left; S2 **edits no
driver code** (non-goals: gate/runtime/execution changes).

### 5.1 Exact target startup sequence

`LoopDriver._run_startup_gate()` runs only on the live derivative path
(`driver.py:348-383`, gated `is_live ∧ has_derivatives ∧ injected checker`). The SPAN readiness step
slots per the audit's binding constraint — **after master readiness and after canonicalization,
before the tick loop** (`MM9_MARGIN_CAPITAL_INFRASTRUCTURE_AUDIT.md` §8):

```
_run_startup_gate():                                    state before tick loop
  1. _check_master_readiness()      FRESH? else refuse          [EXISTS, driver.py:385]
  2. _canonicalize_restored_ledger()  upgrade identity          [EXISTS, driver.py:432]
  3. _check_span_readiness()        READY? else refuse          [TARGET — S3/S4 wires;
                                                                  S2 supplies the callable]
  4. _reconcile_ledger()            broker reconcile             [EXISTS, driver.py:459]
  5. → RUNNING (tick loop)
```

### 5.2 Validation order rationale

- **After `_check_master_readiness` + `_canonicalize_restored_ledger`:** the audit §8 requires any
  margin-data initialization to follow canonicalization, because margin calculation references
  `ci.multiplier` / `ci.asset_class` / `ci.strike` — canonical identity must be verified first. The
  SPAN readiness step honors that ordering even though the *verdict* itself reads only the archive
  (the *use* of the snapshot in the gate, S4, is what needs canonical identity).
- **Before `_reconcile_ledger` / tick loop:** a session that cannot obtain valid SPAN parameters must
  refuse to start (S1 §5.8, ADR-MM7F-1) — never reach RUNNING with no/invalid risk parameters.

### 5.3 Interaction with the instrument master

SPAN readiness is a **sibling** reference-data gate to master readiness — same `READY/REFUSE` shape,
same refuse-to-start consequence, same injectable-callable construction. They are **independent**:
the master describes *what* an instrument is (lot_size, expiry); SPAN describes *the risk parameters*
for the underlying. SPAN readiness does **not** depend on the master's verdict, but is ordered after
it (§5.1) so that by the time any SPAN-using margin calc runs (S4), canonical identity is settled.

### 5.4 Interaction with the Startup Gate (refusal contract)

A SPAN-readiness `REFUSE` routes into the **existing** refusal contract (ADR-MM7F-1, the
`broker_positions` precedent): journal a durable `SPAN_PARAMS_REFUSED` event → `alerter.critical` →
`abort_startup()` → `STOPPED`; the gate returns `False`; `bars_processed == 0`. **No retry in the
gate** (§6). S2 defines this contract; S3/S4 implements the call site.

---

## 6. Failure Modes

Every failure resolves through the **producer-vs-consumer split** that `run_refresh` (job) vs
`_check_*` (gate) already embodies. **Retry lives in the producer (offline job / OS scheduler); the
startup load/gate never retries — it refuses** (ADR-MM7F-1). Warnings are producer-side only (a
failed job logs + preserves the prior snapshot); the startup path is binary READY/REFUSE.

| # | Failure | Detected by | Producer (fetch job) handling | Startup (load/gate) handling |
|---|---|---|---|---|
| F-MISSING | **Missing file** (no archive entry for expected date) | job: download yields nothing; gate: `latest_version()` absent/stale | **Retry**-eligible (job re-run / OS scheduler re-run); prior snapshot preserved; non-zero exit code surfaced (`EXIT_*` pattern). | **Refuse startup.** `SPAN_PARAMS_REFUSED(missing)`. No retry. Operator intervention: run the fetch job. |
| F-CORRUPT | **Corrupt file** (unreadable / undecodable raw bytes) | job parse step; gate `load()` | **Refuse to publish** (shape/parse fails at staging); prior snapshot preserved; **warn** (log) + non-zero exit. **Retry**-eligible next run. | **Refuse startup** if a corrupt file is somehow the active archive entry. No fallback. Operator intervention. |
| F-PARTIAL | **Partial download** (truncated fetch) | job: staging validate; checksum of staged vs expected | Caught at **stage→validate→promote** — a truncated file fails shape/coverage and is **never promoted**; prior snapshot preserved; **retry**-eligible. | Cannot reach startup — a partial file is never published (producer-contained). |
| F-STALE | **Stale version** (`latest < expected`) | gate: `assess()` freshness | Job logs + non-zero exit if it could not publish today's. | **Refuse startup — stale → BLOCK, no grace window.** `SPAN_PARAMS_REFUSED(stale)`. (Deliberate deviation from the master's one-day WARN: risk parameters track volatility; a day-old SPAN set is unsafe — S1 §5.7.) No retry. Operator intervention: run the fetch job. |
| F-CKSUM | **Checksum failure** (raw file sha256 ≠ manifest) | gate: `load()` integrity check (§2.5) | If detected at publish, **refuse to publish**. | **Refuse startup.** `SPAN_PARAMS_REFUSED(checksum)`. A checksum mismatch means tampering/rot — never trust it, never fall back. Operator intervention. |
| F-SCHEMA | **Unsupported schema** (no parser for `schema_version`) | job parse; gate `load()` | **Refuse to publish**; **warn** loudly (an NSE format change needs a new parser, §2.3); **retry will not help** until a parser is added — escalate to **operator/engineer intervention**. | **Refuse startup.** `SPAN_PARAMS_REFUSED(schema)`. No fallback to an old parser. |
| F-EXFMT | **Exchange format change** (NSE alters the file) | job shape guard (parallel to `_contract_shape_ok`) | **Refuse to publish** (shape guard fails); **warn**; prior snapshot preserved; **operator/engineer intervention** to register a new `schema_version` parser. | Producer-contained — the changed file is never published, so startup sees the prior valid snapshot until the parser is updated (then F-STALE governs if too old). |

**Cross-cutting rules:**
- **Refuse > warn > fallback** (ADR-MM7F-1): no failure ever degrades to a flat-rate fallback or an
  old/guessed parameter set. (`MarginTracker` flat-rate is the thing SPAN replaces — never its safety net.)
- **Producer side:** retry + warn + preserve-prior. **Consumer/startup side:** refuse, never retry.
- **Operator intervention** is the terminal recovery for F-MISSING/F-STALE (run the job) and
  F-SCHEMA/F-EXFMT (register a parser) — surfaced via critical alert (ADR-MM7F-1).

---

## 7. Determinism

### 7.1 Why runtime downloads are prohibited

A download in the trade path makes margin a function of *when you asked the network*, not of recorded
state — destroying reproducibility (ADR-003) and violating ADR-007 rule #3/#4. **All acquisition is
the offline job's job** (§2.2). The runtime (and the repository read path) perform **zero network
I/O** (§4.2).

### 7.2 Why runtime refresh is prohibited

The active `SpanSnapshot` is loaded **once at construction (S3) and frozen for the whole session**
(§4.5). No mid-session reload, no intra-day revision pickup (those wait for the next startup). A
parameter set that could change under a running session would make two ticks at the same state
compute different margins — non-deterministic by construction. The frozen snapshot guarantees
**state + snapshot → margin** is a pure function for the session's lifetime (used by S3/S4).

### 7.3 Replay guarantees + snapshot selection (Design Q3)

Replay selects the snapshot by **hard version equality**: the session's audit record carries the
loaded `version` (+ `checksum_sha256`, `schema_version`); replay loads **that exact archived entry**
and **asserts `loaded.version == journaled.version` and `loaded.checksum == journaled.checksum`** —
not "latest ≤ as_of." Equality is what guarantees a replay reconstructs the *identical* parameter set
the live run used, and is the primary guard against loading the wrong version (Design Q8).

### 7.4 Immutable session snapshots

The archive is append-only and immutable (§3.3); the DTO is frozen (§1.2); the load is checksum-
verified (§2.5). The triple — immutable on disk, frozen in memory, integrity-checked at the boundary
— is what makes a SPAN snapshot a deterministic, audit-reconstructable session input.

---

## 8. Testing Strategy

S2 produces a real producer + read path + verdict, so unlike S1 it has genuine behavioural tests.
All deterministic — no network in any test (the fetch download is injected, exactly as
`run_refresh(download=…)` is, `fetch_instrument_master.py:294`).

### 8.1 RED (write first, all failing before the modules exist)

```
R1  test_span_snapshot_is_frozen — SpanSnapshot/SpanRiskArray reject attribute assignment.
R2  test_parser_registry_routes_by_schema_version — known schema parses; unknown raises UnsupportedSpanSchema.
R3  test_repository_load_verifies_checksum — tampered raw file → load() raises (no snapshot returned).
R4  test_span_readiness_stale_is_refuse — latest < expected → REFUSE (NOT a warn/grace).
R5  test_validate_before_publish_preserves_prior — a bad staged snapshot does not replace the prior archive entry.
```

### 8.2 GREEN (minimum to pass each RED)

```
G1  Frozen DTOs (R1).
G2  schema_version-keyed parser registry; UnsupportedSpanSchema on miss (R2).
G3  Repository.load(): read → sha256-verify → parse → SpanSnapshot; raise on any failure (R3).
G4  Freshness (expected_span_date, IST) + evaluate(): latest < expected → REFUSE (R4).
G5  Fetch job stage→validate→promote; refuse-to-publish preserves prior (R5).
```

### 8.3 Integration

```
I1  Synthetic raw file (fixture) → fetch job (injected download) → archive/<date>/{raw,manifest}
    written; manifest fields correct (sha256, schema_version, IST timestamp).
I2  Repository.load(version) on that archive → SpanSnapshot with the expected risk_arrays;
    array_for("NIFTY") returns the array, array_for("UNKNOWN") returns None.
I3  build_span_readiness()() over a fresh archive → READY; over a stale/empty archive → REFUSE.
I4  Replay-equality: load(v) twice yields byte-identical SpanSnapshot; checksum stable
    (determinism / §7.3).
```

### 8.4 Acceptance criteria

| # | Criterion |
|---|---|
| AC1 | `core/risk/span/` exists with frozen `SpanSnapshot` + `SpanRiskArray` (no DuckDB, no DB). |
| AC2 | Parser is a `schema_version`-keyed registry; unsupported schema raises, never falls back. |
| AC3 | `SpanParameterRepository.load(version)` verifies sha256 and parses deterministically; any failure raises (no partial/fallback snapshot). |
| AC4 | Freshness is IST-derived; staleness verdict is **REFUSE** (no WARN grace), consistent with S1 §5.7. |
| AC5 | `build_span_readiness()` returns a zero-arg `Callable[[], SpanReadinessVerdict]`; evaluation-only (no download/refresh). |
| AC6 | `scripts/fetch_span_params.py` stages→validates→promotes; a bad download preserves the prior snapshot; `run_refresh`-style exit codes; `download` injectable. |
| AC7 | Archive is append-only, ISO-date-named, with a per-snapshot `manifest.json` (provenance + sha256). |
| AC8 | NSE source URL / raw format / cutoff are **named constants flagged for confirmation** — not fabricated field layouts. |
| AC9 | **Zero** driver/handler/PortfolioView/telemetry edits (verify by diff). No `SpanMarginCalculator`. No margin calculation anywhere in S2. |
| AC10 | All 728 prior tests pass; new S2 tests green; no test performs a network call. |

### 8.5 Definition of Done

- [ ] `core/risk/span/span_snapshot.py` — frozen `SpanSnapshot` + `SpanRiskArray`, with `version`, `exchange`, `schema_version`, `source_url`, `fetch_timestamp_ist`, `checksum_sha256`, `risk_arrays`.
- [ ] `core/risk/span/span_parser.py` — `schema_version` registry; `UnsupportedSpanSchema`.
- [ ] `core/risk/span/span_repository.py` — `latest_version()`, `load(version)` (checksum-verify + parse).
- [ ] `core/risk/span/span_freshness.py` — `expected_span_date(now)` (IST; `SPAN_REFRESH_CUTOFF` flagged).
- [ ] `core/risk/span/span_readiness.py` — `evaluate`/`assess`/`build_span_readiness`; REFUSE-on-stale.
- [ ] `scripts/fetch_span_params.py` — fetch → parse → shape/coverage validate → stage → promote → archive + manifest; exit codes; injectable `download`; `SPAN_SOURCE_URL`/`SPAN_SCHEMA_VERSION` flagged.
- [ ] `data/risk/span/archive/` layout established (created by the job; not committed).
- [ ] Tests: `tests/risk/span/test_span_snapshot.py`, `test_span_parser.py`, `test_span_repository.py`, `test_span_readiness.py`, `tests/scripts/test_fetch_span_params.py` — all green, no network.
- [ ] Docs synced (§9.3).
- [ ] All 728 prior tests pass; zero runtime/gate/execution/PortfolioView edits.

---

## 9. File-by-File Plan

### 9.1 Production files

| File | Change | Why |
|---|---|---|
| `core/risk/span/__init__.py` | **NEW.** Package marker (parallel to `core/risk/greeks/`). | Establishes the SPAN subpackage in the risk domain (ADR-007 placement). |
| `core/risk/span/span_snapshot.py` | **NEW.** Frozen `SpanSnapshot` + `SpanRiskArray` DTOs (§1.2). | The immutable object S3 consumes; the single data type the loader→calculator boundary speaks (Design Q9). |
| `core/risk/span/span_parser.py` | **NEW.** `schema_version`-keyed parser registry; `UnsupportedSpanSchema` (§2.3). | Isolates the unconfirmed NSE raw format from the DTO; absorbs future format changes (Design Q6). |
| `core/risk/span/span_repository.py` | **NEW.** Pure read path: `latest_version()`, `load(version)` with checksum verify (§4.2). | The read path S3's composition root calls; holds nothing (ownership of the loaded snapshot is S3's). |
| `core/risk/span/span_freshness.py` | **NEW.** `expected_span_date(now)` in IST; `SPAN_REFRESH_CUTOFF` (flagged) (§3.1). | Pure calendar policy; the staleness signal — mirrors `master_freshness.py`. |
| `core/risk/span/span_readiness.py` | **NEW.** `evaluate`/`assess`/`build_span_readiness`; REFUSE-on-stale (§4.3). | The injectable verdict callable the startup gate consumes (S3/S4 wires) — mirrors `master_readiness.py`. |
| `scripts/fetch_span_params.py` | **NEW.** Offline fetch/validate/publish/archive job; exit codes; injectable `download` (§2). | The producer. The only network-touching component. Mirrors `fetch_instrument_master.py`. |

**Not created/modified in S2 (and why):**

| File | Reason |
|---|---|
| `core/risk/span/span_calculator.py` (`SpanMarginCalculator`) | S3 — S2 is data only. |
| `core/runtime/driver.py` | No gate wiring in S2 (non-goal). S2 supplies `build_span_readiness()`; the `_check_span_readiness` step is S3/S4. |
| `core/execution/handler.py`, `portfolio_view.py`, `margin_tracker.py` | No execution/margin/PortfolioView changes (non-goals). |
| `scripts/fno_runner.py` | Composition-root injection of the snapshot + readiness callable is S3/S4. |
| Any DuckDB / persistence schema | No database for SPAN (§1.1); no persistence redesign (non-goal). |

### 9.2 Test files

| File | Purpose |
|---|---|
| `tests/risk/span/test_span_snapshot.py` | Frozen DTOs; `array_for` lookup (R1, I2). |
| `tests/risk/span/test_span_parser.py` | Registry routing; unsupported schema raises (R2, G2). |
| `tests/risk/span/test_span_repository.py` | `load()` checksum verify + parse; failure raises; replay-equality (R3, I2, I4). |
| `tests/risk/span/test_span_readiness.py` | Freshness IST; REFUSE-on-stale; `build_span_readiness` callable (R4, I3). |
| `tests/scripts/test_fetch_span_params.py` | Stage→validate→promote; preserve-prior on bad download; exit codes; injected download (R5, I1). |

### 9.3 Documentation files

| File | Change | Why |
|---|---|---|
| `docs/reports/MM9_IMPLEMENTATION_PLAN.md` | Tick MM9.4-S2; note storage decision (in-memory DTO + archive, not DuckDB) and REFUSE-on-stale. | Keep the roadmap accurate. |
| `docs/PROJECT_STATE.md` | SPAN data foundation present; SPAN margin still BLOCKED/Planned #5 (S3/S4 pending). | KB sync discipline. |
| `docs/CHANGELOG_PLATFORM.md` | "MM9.4-S2 — SPAN parameter sourcing: versioned, checksum-verified, immutably-archived snapshot; offline fetch job; read path + readiness callable; no runtime/gate changes." | Changelog discipline. |
| `docs/SESSION_BOOTSTRAP.md` | "Current Gaps §8": SPAN now has a data foundation; calculation (S3) + buying-power gate (S4) still pending. | Bootstrap accuracy. |
| `docs/ARCHITECTURE_DECISIONS.md` | **Optional** IN-note (not a new ADR): record the in-memory-DTO-over-DuckDB storage decision + REFUSE-on-stale deviation from the master's WARN, if the team wants it durable. (ADR-007 already covers the seam; S2 makes no new architectural decision requiring a full ADR.) | Durable record of the two conscious deviations. |

---

## Additional Design Questions — Explicit Answers

1. **Where exactly are SPAN parameter files stored?**
   `data/risk/span/archive/<YYYY-MM-DD>/` — one directory per snapshot date, each holding the
   immutable raw NSE file (`span_raw.<ext>`) + `manifest.json` (provenance + sha256). **No database**
   (§1.1, §3.3). Parallel to `data/instruments/` but file-archive, not DuckDB, because the data is
   small and read-once.

2. **What immutable object represents one SPAN snapshot?**
   `SpanSnapshot` — a `@dataclass(frozen=True)` carrying `version`, `exchange`, `schema_version`,
   `source_url`, `fetch_timestamp_ist`, `checksum_sha256`, and `risk_arrays: tuple[SpanRiskArray, …]`
   (§1.2). This is the object S3's `SpanMarginCalculator` receives at construction.

3. **How is a snapshot selected during replay?**
   By **hard version equality.** The session journals the loaded `version` + `checksum_sha256`;
   replay loads that exact archive entry and asserts `version` and `checksum` equality — not
   "latest ≤ as_of" (§7.3). This reconstructs the identical parameter set deterministically.

4. **How is the active snapshot injected?**
   At the **composition root** (`scripts/fno_runner.py`, S3/S4) via dependency injection
   (ADR-MM7E-1): `repository.load(active_version)` → `SpanSnapshot` → `SpanMarginCalculator(span_snapshot=…)`;
   and `build_span_readiness()` → injected into the driver startup gate. **S2 supplies the repository
   and the callable; it performs neither injection** (§4.4).

5. **What metadata is recorded for auditability?**
   Per snapshot: `snapshot_date` (version), `exchange`, `source_url`, `fetch_timestamp_ist`,
   `schema_version`, `sha256`, `array_count` — in `manifest.json` (§3.3). At session load: the loaded
   `version` + `checksum` + `schema_version` are journaled so the exact snapshot is reconstructable.

6. **How are future exchange schema changes accommodated?**
   By the **`schema_version`-keyed parser registry** (§2.3). A new NSE format ships a new parser under
   a new `schema_version`; old snapshots keep parsing under their original key; an unsupported schema
   **refuses** (F-SCHEMA) rather than mis-parsing. The DTO stays stable; only a parser body changes.

7. **Can multiple historical SPAN snapshots coexist?**
   **Yes.** The archive is append-only with one directory per date (§3.3); nothing is pruned by the
   job. `latest_version()` finds the newest; `load(version)` reaches any historical entry.

8. **What prevents accidental loading of the wrong version?**
   Three independent guards: (a) **checksum equality** at load (§2.5) — a wrong/tampered file fails;
   (b) **replay version-equality assertion** (§7.3) — replay must load the journaled version exactly;
   (c) the **freshness verdict** (§4.3) — a stale active version REFUSEs at startup (no silent
   old-version use). A wrong version cannot pass all three.

9. **How will MM9.4-S3 consume the loaded snapshot without introducing coupling?**
   S3's `SpanMarginCalculator` receives an already-loaded, already-validated **`SpanSnapshot` DTO via
   constructor injection.** It depends only on the pure `SpanSnapshot` data type in `core/risk/span/`
   — **never** on the fetch job, the archive layout, the parser, or the repository. The
   loader→calculator boundary is a single immutable DTO, exactly as `MarginCalculator`'s consumers
   depend only on the protocol, not on `MarginTracker` (ADR-007). Swapping how snapshots are sourced
   never touches the calculator.

---

## Explicit Non-Goals (S2 must NOT include any of these)

- SPAN calculations · `MarginCalculator` implementation work · `SpanMarginCalculator` (S3)
- buying power (S4) · gate changes · execution changes · runtime telemetry changes
- `PortfolioView` changes · broker integration · optimisation · persistence redesign (no DuckDB/DB)
- MM9.4-S3 work · MM9.4-S4 work · MM10 work
- driver wiring of the readiness step (designed in §5; implemented S3/S4)
- fabricating the NSE raw file layout / source URL / cutoff (constants flagged for confirmation)

---

## Architecture Principles Preserved

| Principle | How S2 preserves it |
|---|---|
| **ADR-001 — Ledger Is Truth** | SPAN parameters are reference data, not ledger state. The repository reads files and returns a value; it holds no portfolio state and mutates no tracker. |
| **ADR-003 — Deterministic Processing** | Static daily files + immutable archive + schema-keyed deterministic parsing + checksum verify + frozen session snapshot ⇒ replay == live (§7). No network in the runtime/read path. |
| **ADR-006 — Sole Orchestrator** | S2 adds no runtime path and no new caller of the handler. The readiness callable is consumed by the existing startup gate (S3/S4), not a parallel process. |
| **ADR-007 — MarginCalculator Seam** | S2 produces the *immutable configuration* ADR-007 rule #1 permits a calculator to hold. The loader→calculator boundary is a DTO, keeping the S3 calculator decoupled from sourcing (Design Q9). No broker API in any S2 path (rule #4). |
| Immutable data | All DTOs `frozen=True`; archive append-only; snapshot frozen for the session. |
| Deterministic replay | Hard version + checksum equality on replay (§7.3). |
| Dependency injection | `build_span_readiness()` + repository-loaded `SpanSnapshot` injected at the composition root (S3/S4); S2 supplies the building blocks (ADR-MM7E-1). |
| Single source of truth | The raw archived file is the integrity anchor + source of truth; the DTO is its deterministic derivation (§2.5). |
| Startup validation | Readiness verdict (READY/REFUSE) + integrity checks gate session start (§5, §6); refuse-to-start on any invalidity (ADR-MM7F-1). |
| Zero runtime network dependency | All acquisition is the offline job; the repository and runtime perform no network I/O (§7.1). |

---

## Appendix A — DTO + Module Surface (Authoritative for S3)

```
core/risk/span/
  span_snapshot.py    SpanSnapshot(frozen), SpanRiskArray(frozen)        ← the S3 consumption boundary
  span_parser.py      parse(raw, schema_version) → tuple[SpanRiskArray]  ; UnsupportedSpanSchema
  span_repository.py  SpanParameterRepository.latest_version()/load(v)   ← pure read path (checksum-verified)
  span_freshness.py   expected_span_date(now) [IST]                      ; SPAN_REFRESH_CUTOFF (confirm)
  span_readiness.py   evaluate/assess/build_span_readiness → verdict     ← injectable, REFUSE-on-stale
scripts/
  fetch_span_params.py  fetch → validate → stage → promote → archive     ← producer, only network touchpoint
```

## Appendix B — Storage Layout (Authoritative)

```
data/risk/span/archive/<YYYY-MM-DD>/
    span_raw.<ext>     # immutable raw NSE file — source of truth + integrity anchor
    manifest.json      # {snapshot_date, exchange, source_url, fetch_timestamp_ist,
                       #  schema_version, sha256, array_count}
```

## Appendix C — Slice Dependencies

```
MM9.4-S1 (COMPLETE: MarginCalculator protocol, ADR-007)
        │
        ▼
MM9.4-S2 (THIS SLICE: SPAN data foundation — fetch job, SpanSnapshot, repository, readiness callable)
        │
        ▼
MM9.4-S3 (SpanMarginCalculator: consumes SpanSnapshot via DI; satisfies the grown protocol)
        │
        ▼
MM9.4-S4 (buying-power gate; composition-root swap MarginTracker → SpanMarginCalculator)
```

S2 must be green before S3 begins: the `SpanSnapshot` DTO and the repository read path must be stable
before the calculator types against them.
