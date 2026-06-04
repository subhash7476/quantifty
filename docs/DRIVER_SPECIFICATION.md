# DRIVER_SPECIFICATION.md

**Status:** PLACEHOLDER — not yet authored.

This document is the designated home for the specification of the **deterministic loop driver** — the highest-priority missing platform pillar (see `docs/PROJECT_STATE.md` → Planned #1, and `docs/ARCHITECTURE_DECISIONS.md` → ADR-003).

It is intentionally a stub. No specification has been written yet; nothing here should be treated as a decision. The driver has **not** been designed or built.

## What this document will eventually contain

(To be authored as a dedicated task — not invented here.)

- The contract of the deterministic event loop extracted from `core/runner.py` (strategy body excluded), per `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md` (item 1).
- How the driver wires the already-extracted `core/execution/watchdog.py` (`RuntimeWatchdog.record_bar` / `check_data_staleness` / `write_heartbeat`) and the telemetry publishing loop.
- The generic signal-source seam (so the platform stays strategy-agnostic — ADR-002).
- Single execution path / single position truth guarantees (ADR-003).

## Source material to base it on

- `docs/reports/RUNNER_DEPENDENCY_ANALYSIS.md` — import-level classification of `core/runner.py`.
- `docs/reports/RUNNER_EXTRACTION_BLUEPRINT.md` — per-capability extraction plan + difficulty + hidden risks.
- `docs/reports/CAPABILITY_REVIEW.md` — the deterministic-runner capability review.
- `docs/PLATFORM_CONSTITUTION.md` — Principle 3 (Deterministic Operation), Principle 5 (No Trading On Stale Data).

> Do not populate this file with a design until the driver work is explicitly scoped. Until then it exists only to hold the structural slot.
