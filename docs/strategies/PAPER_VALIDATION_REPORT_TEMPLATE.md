# PAPER Validation Report — `<strategy_id>`

**Template version:** 1.0 (MM12.5)
**Stage:** 2 — PAPER VALIDATED evidence dossier
**Purpose:** Permanent record of the zero-capital behavioral proof through the real composition root.

---

## 1. Identity

| Field | Value |
|---|---|
| `strategy_id` | `<strategy_id>` |
| `code_ref` | `<commit hash>` |
| `config_hash` | `<SHA-256>` |
| `STRATEGY_CONTRACT_VERSION` | `1.0` |
| Platform commit | `<platform commit hash>` |
| Conformance report ref | `<path to Stage 1 conformance report>` |
| Window start | `<YYYY-MM-DD>` |
| Window end | `<YYYY-MM-DD>` |

## 2. Window compliance

| Requirement | Actual | Pass/Fail |
|---|---|---|
| ≥ 20 NSE trading sessions | `<count>` | PASS / FAIL |
| ≥ 30 completed round-trips | `<count>` | PASS / FAIL |
| Acceptance (if shortfall) | `<grantor note, if any>` | ACCEPTED DEVIATION / N/A |

## 3. Guard cleanliness

| Counter | Actual | Required |
|---|---|---|
| `STRATEGY_ERRORS` | 0 | 0 |
| `STRATEGY_QUARANTINE_EVENTS` | 0 | 0 |
| `SIGNAL_CONTRACT_REJECTIONS` | 0 | 0 |

## 4. Risk metrics

| Metric | Value | Declaration limit |
|---|---|---|
| Max drawdown (Rs) | `<Rs>` | `<Rs>` |
| Max drawdown (%) | `<%>` | `<%>` |
| Peak gross exposure (Rs) | `<Rs>` | — |
| Peak margin utilization (Rs) | `<Rs>` | `<Rs>` |
| Signal→fill conversion rate | `<%>` | — |
| Rejections by gate | `<breakdown>` | — |
| Round-trip count | `<count>` | — |
| Win rate | `<%>` | — |
| Average win (R) | `<R>` | — |
| Average loss (R) | `<R>` | — |
| Profit factor | `<ratio>` | — |

## 5. Telemetry archive

| Session date | Bars processed | Signals received | Signals routed | Heartbeats |
|---|---|---|---|---|
| `<YYYY-MM-DD>` | `<n>` | `<n>` | `<n>` | `<count / gap-free>` |

Telemetry continuity assessment: `<PASS / FAIL — any gap excludes the session from the window>`

## 6. Journal audit

| Intent vs. Reality Metric | Value |
|---|---|
| Total signals emitted | `<count>` |
| Total fills received | `<count>` |
| Shadow-state divergence (strategy over-counts) | `<count>` |
| Shadow-state divergence (reverse — platform defect flag) | `<count>` |
| One-directional divergence confirmed (OK) | YES / NO |
| Journal gaps | `<none / described>` |

## 7. Margin evidence

| Position type | Margin gate exercised | NseMarginEngine used | SPAN/ELM figures journaled |
|---|---|---|---|
| `<futures / options>` | YES / NO | YES / NO | YES / NO |

## 8. Kill-switch drill

| Date | Drill type | Observed behavior | Journal record |
|---|---|---|---|
| `<YYYY-MM-DD>` | operator / manual | `<entry signals blocked, journaled, kill-switched-but-running>` | `<journal path / event ref>` |

## 9. Restarts and anomalies

| Date | Type | Cause | Disposition |
|---|---|---|---|
| `<YYYY-MM-DD>` | restart | `<ops / platform / strategy-attributable>` | `<window reset / no reset>` |
| `<YYYY-MM-DD>` | anomaly | `<description>` | `<disposition>` |

## 10. Replay evidence

| Replay session | Corpus ref | Signal stream match | Ledger deterministic fields match | Exclusions |
|---|---|---|---|---|
| `<YYYY-MM-DD>` | `<corpus path>` | PASS / FAIL | PASS / FAIL | `broker_id` UUIDs, journal wall-clock timestamps |

## 11. Grantor review

| Reviewer | Role | Decision | Date |
|---|---|---|---|
| `<name>` | Technical Lead | GRANT / REJECT | `<YYYY-MM-DD>` |
