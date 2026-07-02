# Runbook — `<strategy_id>`

**Template version:** 1.0 (MM12.5)
**Stage:** 3 — LIVE CANDIDATE (kill-switch + rollback)
**Purpose:** Two runbooks required for Stage 3 Go-Live Checklist items (e) and (f).

---

## Part 1: Kill-Switch Runbook

### 1.1 Activation paths

| Path | Trigger | How to activate | Expected behavior |
|---|---|---|---|
| Manual | Operator decision | `<command / UI action>` | Entry signals blocked and journaled; EXITs blocked; loop continues; telemetry/heartbeat alive |
| Watchdog staleness | Feed stall > threshold | Automatic via `RuntimeWatchdog` | `WATCHDOG_STALE_DATA` journaled → `activate_kill_switch()` |
| Drawdown gate | Declared max DD breached | Automatic via `ExecutionHandler` | `DRAWDOWN_BREACH` journaled → `activate_kill_switch()` |
| Daily trade limit | Per-day limit reached | Automatic via `ExecutionHandler` | `DAILY_LIMIT_REACHED` journaled → `activate_kill_switch()` |
| Broker error threshold | N consecutive broker failures | Automatic via `ExecutionHandler` | `BROKER_ERROR` (CRITICAL) → `activate_kill_switch()` |

### 1.2 Observable consequences

| Aspect | Behavior |
|---|---|
| Signal flow | `GuardedSignalSource` still invokes `on_bar` → `LoopDriver` receives `[]` (no signals to route because kill switch blocks ALL) |
| Positions | Open positions are NOT auto-flattened (ADR-019) |
| Telemetry | `RuntimeMetric` counters published; heartbeat continues |
| Journal event | `KILL_SWITCH_ACTIVATED` (edge-triggered, once per activation) |
| Operator alert | Critical alert via alerter |
| Recovery | Restart after cause identified and resolved; investigation report within 5 trading days |

### 1.3 Post-activation verification checklist

- [ ] Confirm `_kill_switched == True` in journal
- [ ] Confirm entry signals blocked in journal
- [ ] Confirm telemetry still publishing
- [ ] Confirm heartbeat still writing
- [ ] Assess open positions via ledger (ADR-001) and cross-check broker book
- [ ] Classify cause as strategy-attributable or external

---

## Part 2: Rollback Runbook (Fixed 7-Step Procedure per §7.9)

### Step 1: Halt intake

- Activate kill switch (blocks everything including EXITs — known posture)
- Confirm quarantine already latched (if strategy-attributable)

### Step 2: Assess positions

- Read positions from the ledger (truth, ADR-001)
- Cross-check against broker book

### Step 3: Disposition positions

- Operator decision: flatten, hold, or reduce
- Execute manually via broker (never automated — ADR-019)
- Record disposition in journal

### Step 4: Stop the process

- Clean shutdown
- Journal shows `STOPPED`

### Step 5: Ledger the demotion/suspension

- Record trigger, timestamp, position disposition
- Entry ID: `<assigned by Strategy Promotion Ledger>`

### Step 6: Investigate

- Report due within 5 trading days
- Classify root cause: strategy-attributable or external
- Attach investigation report to dossier

### Step 7: Re-entry

- **If external cause:** grantor sign-off → resume at prior stage
- **If strategy-attributable:** fix → new identity → Stage 0
- Never restart the process "to see if it recurs" (ADR-019)

---

## Part 3: Incident response contacts

| Role | Contact | Escalation path |
|---|---|---|
| Operator | `<name / channel>` | Immediate |
| Technical Lead | `<name / channel>` | 1 hour |
| Account Owner | `<name / channel>` | 1 hour (for capital decisions) |
