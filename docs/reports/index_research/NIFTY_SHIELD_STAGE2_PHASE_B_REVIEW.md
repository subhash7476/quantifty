# NiftyShield E007 — Stage-2 PAPER **Phase B tooling** review

**Reviewer:** Claude (review-only; DeepSeek implements per the standing role split)
**Date:** 2026-08-08
**Under review:** DeepSeek's Phase B operational package (working-tree, uncommitted)
**Identity (unchanged):** `nifty_shield_v1` @ `89fcdd6` / `c5b722ff…536c` — strategy
package **not touched**, `config_hash` unchanged.

---

## Remediation status (2026-08-08, verified)

DeepSeek remediated **F-B1–F-B4**; re-reviewed and **VERIFIED** against the code
(not the hand-back): 17/17 `test_phase_b_tools.py` pass locally (108.9s);
`config_hash` `c5b722ff…5336c` unchanged; strategy package untouched; default
composition path byte-identical (smoke PASS).

| Finding | Fix | Verification |
|---|---|---|
| F-B1 [HIGH] | Counting predicate = telemetry-clean ∧ recorded ∧ ≥1 closed structure for the session; headline uses counting N, raw+excluded surfaced; RTs gated to counting sessions; SPAN deliberately gates only §7.7 | `closed_by_session` keyed off `audit.structures[.session]`; fixture proves raw 2 RT → counting 1; **`test_assemble_report_fills_skeleton` runs the real synthetic pipeline** and asserts `1 / ≥20` + `1 / ≥30` — the end-to-end guard that journal `session` and package dir name key-align |
| F-B2 [MED] | Frozen markers moved to immutable `PAPER_VALIDATION_REPORT.skeleton.md`; report is generated output with a banner | `test_assemble_idempotent_default_path` — two runs, identical bytes, skeleton retains markers |
| F-B3 [MED] | `run_drill` STOP write→unlink inside `try/finally` (`_safe_unlink`) | Removed on every exit path incl. mid-drill raise |
| F-B4 [MED] | Real-`RuntimeWatchdog` heartbeat test + SPAN pickle round-trip test | Both added; watchdog no longer asserted as a stub string |

**F-B4 operator pre-flight still required before Monday** (one LIVE `--max-bars`
session confirming `span_snapshot.pkl` hash + `heartbeat_ts` + an
`ENTRY_MARGIN engine=NseMarginEngine` row against real marks) — unit coverage
does not substitute for exercising the three live paths together on real data.
F-B5/F-B6 remain as reviewed (LOW / advisory).

**Net: the harness is ACCEPTED and remediated.** The E007 grant still waits on
the real ≥20/≥30 counting window and a separate review of the completed report.

---

## 0. Verdict (original review, pre-remediation)

**ACCEPT the harness as fit-for-purpose** — with two fixes required before the
window's report is assembled, one safety fix + one pre-flight before Monday's
start, and two low notes.

**This review accepts the *tooling*, NOT Phase B and NOT an E007 grant.** Phase B
is forward calendar time: ≥20 counting sessions AND ≥30 round-trips (or the §7.3
escape, ledgered) accrued live through these tools, then the completed PAPER
Validation Report comes back for a *separate* review and the operator's grant.
Nothing here shortcuts that.

### What was verified (evidence, not assertion)
- **11/11** `tests/nifty_shield_paper/test_phase_b_tools.py` pass (ran locally, 52.7s).
- **Phase A byte-identical:** both new seams are additive and guarded —
  `watchdog_factory` (fno_runner) and `recorder`/`provider`/`span_snapshot`
  (paper runner) all default to `None`; watchdog is wired only `if mode is
  Mode.LIVE`. The default composition path is unchanged.
- **F4 audit runs every session:** `finalize_session_evidence` calls
  `audit_window` unconditionally (session.py:112) — matches the operator's
  explicit "every session, not just at report time."
- **Kill-switch (H) premise holds:** handler gate 0 (`handler.py:598`) fires on
  `os.path.exists("STOP")` for the real `PaperBroker`; `is_mock_broker` exempts
  only `MockBrokerAdapter`/`MockBroker`/`unittest.mock.Mock`.
- **Replay ledger check (G) is non-vacuous:** trades are stamped
  `fill.timestamp = clock.now()` (handler.py:446/522), and REPLAY uses
  `ReplayClock` → rows are session-dated, so `_ledger_rows`' `timestamp LIKE
  '{session}%'` filter matches real rows rather than silently returning `[]`.
- **F3 preserved through replay:** `ReplayMarksSource` re-raises
  `MarksSourceUnavailable` (test_replay_marks_re_raises_outage).

---

## 1. Findings

### F-B1 [HIGH] — session/round-trip count over-counts vs the runbook's own "counts toward the window" rule
`assemble_report._fmt` sets `n_sessions = len(session_summaries)` (every package
carrying a `session_summary.json`) and `round_trips = metrics.round_trips` (every
closed structure in the accumulated ledger). Neither is gated on the runbook's
counting rules:

- §3.3 — *a telemetry gap excludes the session* (yet `finalize_session_evidence`
  has already written `session_summary.json` before `run_session` returns 1, so
  the excluded session still counts).
- §3.4 — the structure must close (`STRUCTURE_CLOSE`).
- §4 — a session with no current SPAN snapshot does not count toward §7.7.
- §9 / `--no-record` — a non-recorded session (`replay_inputs: False`) still gets
  counted.

`clean_sessions` is computed in `_fmt` but only reported separately; it never
gates the headline. The filled report renders `**N / ≥20 required**` and
`**N / ≥30 required**` — the exact arithmetic of §8 acceptance gate 1 — and can
read *satisfied* while N includes non-counting sessions. Because deciding the
§7.3 escape after seeing the count is prohibited, an inflated count is not a
cosmetic error; it can manufacture a false "gate met."

**Fix (DeepSeek):** compute the headline count over sessions that are
telemetry-clean **and** structure-closed **and** recorded; decide and document
whether the SPAN-present condition gates the session count or only the §7.7
sub-requirement; apply the same gate to `round_trips` (a closed structure inside
an excluded session must not count). Surface both raw and counting numbers so the
exclusion is auditable.
*Bites at assembly (~2 months out), not at window start.*

### F-B2 [MEDIUM] — assembler overwrites the tracked frozen skeleton in place, one-shot
Default `--report` is the tracked `PAPER_VALIDATION_REPORT.md`; `assemble()` does
`report_path.write_text(skeleton)` back onto that same path. After the first run
the `[FILL]` markers are gone, so a second run raises `RuntimeError: report
marker … found 0 times (expected 1) — the frozen skeleton changed` — a **false
tamper alarm on legitimate re-assembly.** Any evidence correction (re-run a
drill/replay, add a session) then requires `git checkout` of the skeleton first,
which the runbook §7 does not mention. `test_assemble_report_fills_skeleton`
copies the skeleton to `tmp_path` before calling `assemble`, so the real in-place
path is never exercised.

**Fix (DeepSeek):** keep the frozen skeleton as an immutable template (separate
file, or read the committed blob) and write the filled report to a distinct
output path — or document a restore step. Add a test that runs `assemble` twice
against the default path and asserts the second run still succeeds.
*Bites at assembly, not at window start.*

### F-B3 [MEDIUM] — drill can leak a `STOP` file into the operator's CWD
`run_drill` writes `Path.cwd() / "STOP"` and only removes it at the start of
Phase 2; there is **no try/finally.** If anything between the write and the
Phase-2 `unlink` raises (thread join timeout, recovery build error,
`ReplayDivergence`), the `STOP` file persists. The handler checks
`os.path.exists("STOP")` **relative to CWD**, and `session.py` runs from repo
root — so a leaked `STOP` silently kill-switches the next live session. `main()`
has no cleanup; only the pytest test unlinks in a `finally`.

**Fix (DeepSeek):** wrap the write→unlink in `try/finally` inside `run_drill` so
the `STOP` file is always removed, even on failure. (Optionally isolate the
drill's CWD.) *Fix before the mid-window drill is run.*

### F-B4 [MEDIUM] — the three LIVE-only evidence paths are entirely untested
The fixture monkeypatches `_load_span_snapshot → None`, and
`test_build_runner_wires_watchdog_factory` asserts against the literal string
`"watchdog-stub"`. Consequently, across the whole suite: **no real
`RuntimeWatchdog` is constructed, no `span_snapshot.pkl` is written, and no
`ENTRY_MARGIN` row with `engine=NseMarginEngine` is produced.** These are exactly
the §7.7 SPAN+ELM margin evidence and the heartbeat evidence the operator named,
and all three only run in LIVE (every test runs REPLAY).

**Mitigation before Monday (cheap, high-value):** a one-session LIVE pre-flight
with a small `--max-bars` confirming — `span_snapshot.pkl` present with a
non-null hash in `meta.json`; `heartbeat.json` exists and surfaces as
`heartbeat_ts` in `telemetry.json`; at least one `ENTRY_MARGIN` row carries
`engine=NseMarginEngine`. That exercises all three untested live paths for
near-zero cost before real evidence accrues on top of them.

### F-B5 [LOW] — fact-identity check reuses the same mutated `facts.duckdb`
`run_session_replay` reads `recorded_fact` and (after the replay writes the
recomputed fact back into the *same* package `facts.duckdb`) `recomputed_fact`,
both via `ORDER BY session_date DESC LIMIT 1`. If the live fact publisher appends
rather than upserts, two same-session rows exist and `LIMIT 1` is order-ambiguous.
It passes deterministically today; a cleaner design snapshots the recorded fact
into a separate immutable artifact at finalize. Informational.

### F-B6 [LOW] — regression attestation is advisory, not enforced
`assemble --run-tests` records the pytest returncode into `window_evidence.json`
and fills a static instruction string; it never fails assembly on a red suite.
Acceptable given human-in-loop review, but the §6/§8.8 "regression green"
attestation is operator-verified, not machine-gated — state that plainly at
hand-back.

---

## 2. Sequencing (what the operator actually needs)

| When | Items |
|---|---|
| **Before Monday's start** | **F-B3** (drill `STOP` leak — fix), **F-B4** (one LIVE pre-flight session exercising span/heartbeat/`NseMarginEngine`) |
| **Before report assembly (~2 mo)** | **F-B1** (count gate — HIGH), **F-B2** (in-place skeleton overwrite) |
| **At hand-back** | note **F-B6** (regression attestation is advisory); consider **F-B5** |

None of these hold the calendar. The window can begin operating once F-B3 is
fixed and the F-B4 pre-flight is green; F-B1/F-B2 must land before the report is
assembled and handed back.

**This is an ACCEPT of the harness only.** The E007 grant still waits on the real
≥20/≥30 counting window and a separate review of the completed PAPER Validation
Report, per the standing instruction.
