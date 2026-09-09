# docs/reports — Index

Organized by research lineage / platform area (2026-09-05 re-org, 426 files).

| Folder | Contents | Count |
|---|---|---|
| `carry/` | CARRY_* — signal engine sleeve, TRAIN/HOLDOUT/SEALED, parity, capacity | 45 |
| `ts_basis/` | TS_BASIS_* incl. DAILY — basis sleeves, sealed, re-auth assessment | 19 |
| `sleeves/` | IVOL_*, LAG_*, SKEW_*, TREND_*, SLEEVE_*, MULTI_FACTOR_* | 21 |
| `psb/` | PSB1_*, PSB2_*, C2_* — screening batteries + C2 phase-0 | 56 |
| `sfb_f1/` | F1_* — stock-futures battery feasibility screen | 16 |
| `index_research/` | CB_N50_*, RS_MOM_*, NIFTY_*, A_* — pair / breadth / intraday | 45 |
| `rfa_gate/` | RFA_*, FLOW_RFA, O1_RFA — feasibility gate + remediations | 8 |
| `substrate_csmp/` | CSMP_* + `csmp_a2_records/` — substrate gates A–E, universe, CA | 35 + records dir |
| `platform/` | MM*, G1_*, LOOPDRIVER_*, RUNNER_*, MARGIN_*, SPAN_*, MASTER_*, PHASE_* | 97 |
| `ops_data/` | OPS_*, EOD_*, CAS_*, EQUITY_MISS, DATA_STORE_MAP, ORCHESTRATOR, UPSTOX map | 18 |
| `strategies/` | NIFTY_SHIELD_*, DAYTYPE_*, OPTIONS_WALL_*, ISD*, MSI_*, MSRP_*, DRA_*, MRLC_*, STAGE_A_*, TRADE_INTELLIGENCE_* | 57 |
| root | README + SALVAGE, REPO_AUDIT, CAPABILITY_REVIEW, PROJECT_REVIEW, CANONICAL_INSTRUMENT_ARCHITECTURE, SIGNAL_ENGINE_DESIGN, DUPLICATION_AUDIT | 8 |

**Policy (2026-07-04, still in force):** this directory is frozen for new *program* work. New programs keep reports beside program docs under `docs/implementation/<program>/reports/`. One-off platform-wide reports may still land here — place under the matching subfolder above.

**Note:** pre-2026-09-05 references using flat paths (`docs/reports/CARRY_...`) now need the subfolder prefix (e.g. `docs/reports/carry/CARRY_...`).

