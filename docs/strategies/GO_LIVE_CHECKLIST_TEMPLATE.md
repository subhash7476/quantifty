# Go-Live Checklist — `<strategy_id>`

**Template version:** 1.0 (MM12.5)
**Stage:** 3 — LIVE CANDIDATE
**Purpose:** Every item provable without a funded account. 100% completion required before Stage 4 grant. Explicitly separates architectural completion (this document) from the funded-account operational prerequisite (Stage 4).

---

## 1. Identity

| Field | Value |
|---|---|
| `strategy_id` | `<strategy_id>` |
| `code_ref` | `<commit hash>` |
| `config_hash` | `<SHA-256>` |
| `STRATEGY_CONTRACT_VERSION` | `1.0` |
| PAPER Validation Report | `<path>` |
| PAPER evidence unexpired (< 60 days) | YES / NO |
| Platform commit | `<commit hash>` |

---

## 2. Checklist items

### a) Broker reconciliation proven live

| Item | Status | Evidence |
|---|---|---|
| First-hand authenticated `short-term-positions` capture (non-empty) | DONE / NOT DONE | `<path to capture log or report>` |
| `get_positions() → rekey_broker_positions_by_token() → to_reconcile_positions()` chain shown working | DONE / NOT DONE | `<path to reconciliation log>` |
| Real broker book reconciled against ledger | DONE / NOT DONE | `<path to reconciliation result>` |
| UNRECONCILABLE_UNMAPPED_POSITION handling verified | DONE / NOT DONE | `<path to evidence>` |

### b) Broker margin reconciliation report

| Item | Status | Evidence |
|---|---|---|
| Broker-quoted margin fetched for representative candidate positions | DONE / NOT DONE | `<path to margin comparison log>` |
| `NseMarginEngine` computed margin for same positions | DONE / NOT DONE | `<path to local margin log>` |
| Divergence characterized and bounded | DONE / NOT DONE | `<path to divergence report>` |
| Reconciliation cadence defined | DONE / NOT DONE | `<cadence>` |

### c) Credential/token lifecycle

| Item | Status | Evidence |
|---|---|---|
| Token issue path documented | DONE / NOT DONE | `<path to runbook>` |
| Token expiry behavior confirmed (refusal / watchdog path, never silent) | DONE / NOT DONE | `<path to test log>` |
| Token renewal path walked once for real | DONE / NOT DONE | `<path to evidence>` |

### d) Process supervision

| Item | Status | Evidence |
|---|---|---|
| Restart policy defined | DONE / NOT DONE | `<path to runbook>` |
| Heartbeat monitored by external process | DONE / NOT DONE | `<path to monitoring config>` |
| Alert path test-fired and receipt confirmed | DONE / NOT DONE | `<path to alert test log>` |

### e) Kill-switch runbook verified

| Item | Status | Evidence |
|---|---|---|
| Manual activation path demonstrated | DONE / NOT DONE | `<path to drill log>` |
| Watchdog staleness trip demonstrated | DONE / NOT DONE | `<path to drill log>` |
| Drawdown gate trip demonstrated | DONE / NOT DONE | `<path to drill log>` |
| Daily-trade-limit trip demonstrated | DONE / NOT DONE | `<path to drill log>` |
| Runbook finalized | DONE / NOT DONE | `<path to runbook>` |

### f) Rollback runbook

| Item | Status | Evidence |
|---|---|---|
| Seven-step rollback procedure walked through on PAPER deployment | DONE / NOT DONE | `<path to walkthrough log>` |
| Runbook finalized | DONE / NOT DONE | `<path to runbook>` |

### g) Capital plan

| Item | Status | Value |
|---|---|---|
| Allocation (Rs) | DONE | `<Rs>` |
| Initial capital cap (Rs) | DONE | `<Rs>` |
| Drawdown gate setting | DONE | `<Rs or %>` |
| Daily trade limit gate setting | DONE | `<count>` |
| Margin budget gate setting | DONE | `<Rs>` |
| Max positions gate setting | DONE | `<count>` |
| Capital plan document | DONE | `<path>` |

---

## 3. Dual sign-off

| Role | Signatory | Decision | Date |
|---|---|---|---|
| Technical Lead (evidence is complete and genuine) | `<name>` | APPROVED / REJECTED | `<YYYY-MM-DD>` |
| Account Owner (capital commitment) | `<name>` | APPROVED / REJECTED | `<YYYY-MM-DD>` |

---

## 4. Stage 4 grant entry reference

- Ledger entry ID: `<E-id>`
- Effective date: `<YYYY-MM-DD>`
- Initial capital cap: `<Rs>`
- Risk-gate settings ledgered: YES / NO
