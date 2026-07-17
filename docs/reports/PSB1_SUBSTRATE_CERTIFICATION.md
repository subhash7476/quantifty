# PSB-1 Substrate Certification Report (Prompt 5-C — four-arm contract test)

**Script-generated** — `scripts/psb1/certify_substrate.py`. Code commit `0d155b9`.
Real store, read-only. Store stamps: rows **7,030,920**, fenced MAX(trade_date) **2022-12-30**, unfenced MAX **2026-07-09**.

Governing analysis: `PSB1_CERTIFICATION_METHODOLOGY.md` (operator-endorsed 2026-07-15). The suite tests the ONE continuity contract via four complementary arms with zero structural filters; the sole permitted exclusion is a committed disposition register.

## Certification Summary

| Check | Result | Detail |
|---|:--:|---|
| **Arm A** intra-symbol CA-shape | PASS | 78 residue (78 dispositioned, **0** undocumented); 2720 large_genuine |
| **Arm B** cross-symbol handoff | PASS | 4 splice fabrications (4 dispositioned, **0** undocumented) |
| **Arm C** prev_close identity | PASS | 0 violations |
| **Arm D** factor evidence | PASS | 1116 tested, 16 flagged (16 dispositioned, **0** undocumented) |
| Structural: co-trading | PASS | 0 overlapping entities |
| Structural: double-apply | PASS | 0 double-apply (entity, ex_date) keys |
| Structural: membership | PASS | byte-identical (35000 cells) |
| Structural: row count | PASS | 7,030,920 (expected 7,030,920) |
| Structural: intervals | PASS | 4133 rows, multi-interval symbols: 1 (DTILx2) |
| Structural: DVL->DTIL re-key | PASS | DVL=0 DTIL=1 BONUS |
| Regression: PHILIPCARB 2018-04-19 ret | PASS | +4.9845% |
| Regression: DVL 2021-08-05 ret | PASS | -6.5503% |
| Regression: DTIL 2021-08-05 ret | PASS | -0.2255% |
| Regression: LITL prev_close | PASS | 57.6700 |

## Arm A — Intra-symbol CA-shape

78 CA-shaped moves with no matching factor. Dispositioned: 78. **Undocumented (HALT): 0**.

| Entity | Symbol | Date | Return | Class | Disposition |
|--------|--------|------|-------:|-------|-------------|
| 8KMILES | 8KMILES | 2020-09-07 | -59.3% | CA-shaped-orphan | demerger |
| ABFRL | ABFRL | 2025-05-22 | -66.6% | CA-shaped-orphan | documented_scope_exclusion |
| ABSLBANETF | ABSLBANETF | 2021-11-25 | -90.0% | CA-shaped-orphan | etf_unit_split |
| ABSLNN50ET | ABSLNN50ET | 2021-11-25 | -89.9% | CA-shaped-orphan | etf_unit_split |
| ALPL30IETF | ALPL30IETF | 2024-05-10 | -89.9% | CA-shaped-orphan | etf_unit_split |
| AUTOIETF | AUTOIETF | 2024-03-01 | -89.7% | CA-shaped-orphan | etf_unit_split |
| BANKBEES | BANKBEES | 2019-12-19 | -90.0% | CA-shaped-orphan | etf_unit_split |
| BANKNIFTY1 | BANKNIFTY1 | 2026-02-27 | -90.1% | CA-shaped-orphan | etf_unit_split |
| BORORENEW | BORORENEW | 2020-03-06 | -73.6% | CA-shaped-orphan | demerger |
| BSE500IETF | ICICI500 | 2021-10-28 | -90.1% | CA-shaped-orphan | etf_unit_split |
| BSLNIFTY | BSLNIFTY | 2021-11-25 | -89.9% | CA-shaped-orphan | etf_unit_split |
| BSLSENETFG | BSLSENETFG | 2021-11-25 | -89.9% | CA-shaped-orphan | etf_unit_split |
| CONS | CONS | 2026-02-27 | -90.1% | CA-shaped-orphan | etf_unit_split |
| CREATIVEYE | CREATIVEYE | 2023-08-25 | -51.1% | CA-shaped-orphan | demerger |
| DALMIACEM | DALMIACEM | 2010-09-24 | -70.9% | CA-shaped-orphan | demerger |
| DCM | DCM | 2019-05-30 | -49.0% | CA-shaped-orphan | documented_scope_exclusion |
| DSPQ50ETF | MIDQ50ADD | 2026-07-03 | -90.0% | CA-shaped-orphan | etf_unit_split |
| FMCGIETF | FMCGIETF | 2024-05-10 | -89.9% | CA-shaped-orphan | etf_unit_split |
| FOURSOFT | FOURSOFT | 2013-10-17 | -67.3% | CA-shaped-orphan | documented_scope_exclusion |
| GOLD1 | KOTAKGOLD | 2021-07-22 | -90.0% | CA-shaped-orphan | etf_unit_split |
| GROWWGOLD | GROWWGOLD | 2026-02-06 | -90.1% | CA-shaped-orphan | etf_unit_split |
| GROWWSLVR | GROWWSLVR | 2026-02-06 | -90.5% | CA-shaped-orphan | etf_unit_split |
| GULFPETRO | SAHPETRO | 2013-07-09 | +81.6% | direction-mismatch | evidence_exception |
| HBANKETF | HDFCNIFBAN | 2024-02-02 | -90.0% | CA-shaped-orphan | etf_unit_split |
| HDFCLOWVOL | HDFCLOWVOL | 2023-10-20 | -90.1% | CA-shaped-orphan | etf_unit_split |
| HDFCMID150 | HDFCMID150 | 2023-10-20 | -90.1% | CA-shaped-orphan | etf_unit_split |
| HDFCMOMENT | HDFCMOMENT | 2023-10-20 | -90.2% | CA-shaped-orphan | etf_unit_split |
| HDFCNEXT50 | HDFCNEXT50 | 2023-10-20 | -90.1% | CA-shaped-orphan | etf_unit_split |
| HDFCNIF100 | HDFCNIF100 | 2023-10-20 | -90.0% | CA-shaped-orphan | etf_unit_split |
| HDFCNIFETF | HDFCNIFETF | 2021-02-17 | -90.0% | CA-shaped-orphan | etf_unit_split |
| HDFCPVTBAN | HDFCPVTBAN | 2024-02-02 | -90.1% | CA-shaped-orphan | etf_unit_split |
| HDFCSENETF | HDFCSENETF | 2021-02-17 | -90.1% | CA-shaped-orphan | etf_unit_split |
| HDFCSENETF | HDFCSENSEX | 2024-02-02 | -90.0% | CA-shaped-orphan | etf_unit_split |
| HEALTHADD | HEALTHADD | 2026-07-03 | -89.7% | CA-shaped-orphan | etf_unit_split |
| HERITGFOOD | HERITGFOOD | 2023-01-20 | -46.8% | CA-shaped-orphan | demerger |
| HNGSNGBEES | HNGSNGBEES | 2019-12-19 | -88.6% | CA-shaped-orphan | etf_unit_split |
| ICICIBANKN | ICICIBANKN | 2022-09-01 | -90.1% | CA-shaped-orphan | etf_unit_split |
| ICICIM150 | MIDCAPIETF | 2024-05-10 | -89.9% | CA-shaped-orphan | etf_unit_split |
| ICICIMOM30 | ICICIMOM30 | 2022-08-12 | -89.9% | CA-shaped-orphan | documented_scope_exclusion |
| ICICINXT50 | ICICINXT50 | 2018-11-16 | -89.0% | CA-shaped-orphan | etf_unit_split |
| ICICIQTY30 | QUAL30IETF | 2024-05-10 | -89.9% | CA-shaped-orphan | etf_unit_split |
| ICICITECH | ICICITECH | 2022-09-01 | -90.2% | CA-shaped-orphan | etf_unit_split |
| IDFC | IDFC | 2015-10-01 | -57.2% | CA-shaped-orphan | demerger |
| IIFL | IIFL | 2019-05-30 | -52.2% | CA-shaped-orphan | demerger |
| KAMDHENU | KAMDHENU | 2022-09-06 | -46.6% | CA-shaped-orphan | demerger |
| KESORAMIND | KESORAMIND | 2025-03-10 | -95.3% | CA-shaped-orphan | demerger |
| KOTAKMID50 | MIDCAP | 2026-02-27 | -90.1% | CA-shaped-orphan | etf_unit_split |
| KOTAKNIFTY | KOTAKNIFTY | 2017-07-27 | -90.0% | CA-shaped-orphan | etf_unit_split |
| KWALITY | KWALITY | 2010-06-15 | +45.9% | direction-mismatch | evidence_exception |
| LOWVOLIETF | LOWVOLIETF | 2024-03-01 | -89.9% | CA-shaped-orphan | etf_unit_split |
| MID-DAY | MID-DAY | 2011-01-20 | -78.2% | CA-shaped-orphan | demerger |
| MIDSELIETF | MIDSELIETF | 2024-05-10 | -89.9% | CA-shaped-orphan | etf_unit_split |
| MOLOWVOL | MOLOWVOL | 2022-08-11 | -80.0% | CA-shaped-orphan | etf_unit_split |
| MOMOMENTUM | MOMOMENTUM | 2022-08-11 | -80.0% | CA-shaped-orphan | etf_unit_split |
| MON100 | MON100 | 2021-06-17 | -90.1% | CA-shaped-orphan | etf_unit_split |
| NIF100IETF | NIF100IETF | 2024-05-10 | -89.9% | CA-shaped-orphan | etf_unit_split |
| NIFTYBEES | NIFTYBEES | 2019-12-19 | -89.9% | CA-shaped-orphan | etf_unit_split |
| NIFTYBETA | UTINIFTETF | 2023-09-25 | -90.0% | CA-shaped-orphan | etf_unit_split |
| NV20 | NV20 | 2026-02-27 | -90.1% | CA-shaped-orphan | etf_unit_split |
| NV20IETF | NV20IETF | 2024-03-01 | -89.8% | CA-shaped-orphan | etf_unit_split |
| OCCL | OCCL | 2024-07-01 | -74.1% | CA-shaped-orphan | demerger |
| ORIENTABRA | ORIENTABRA | 2011-11-11 | -66.3% | CA-shaped-orphan | documented_scope_exclusion |
| ORIENTPPR | ORIENTPPR | 2013-03-07 | -80.4% | CA-shaped-orphan | documented_scope_exclusion |
| PIRLIFE | PIRLIFE | 2011-12-23 | -92.4% | CA-shaped-orphan | demerger |
| PSUBNKBEES | PSUBNKBEES | 2019-12-19 | -90.0% | CA-shaped-orphan | etf_unit_split |
| QNIFTY | QNIFTY | 2026-02-13 | -90.1% | CA-shaped-orphan | etf_unit_split |
| QUESS | QUESS | 2025-04-15 | -50.7% | CA-shaped-orphan | documented_scope_exclusion |
| RAYMOND | RAYMOND | 2025-05-14 | -64.8% | CA-shaped-orphan | demerger |
| SABEVENTS | SABEVENTS | 2023-07-10 | -50.0% | CA-shaped-orphan | demerger |
| SHILPI | SHILPI | 2018-02-07 | -49.6% | CA-shaped-orphan | demerger |
| SIEMENS | SIEMENS | 2025-04-07 | -42.9% | CA-shaped-orphan | demerger |
| SINTEX | SINTEX | 2017-05-25 | -75.2% | CA-shaped-orphan | documented_scope_exclusion |
| STAR | STAR | 2013-12-19 | -57.6% | CA-shaped-orphan | demerger |
| SURANAT&P | SURANAT&P | 2010-08-17 | -66.6% | CA-shaped-orphan | documented_scope_exclusion |
| SUVEN | SUVEN | 2020-01-21 | -94.7% | CA-shaped-orphan | demerger |
| TEXINFRA | TEXMACOLTD | 2010-11-01 | -59.4% | CA-shaped-orphan | documented_scope_exclusion |
| TRIVENI | TRIVENI | 2011-05-03 | -60.0% | CA-shaped-orphan | documented_scope_exclusion |
| WEIZMANIND | WEIZMANIND | 2010-12-08 | -66.9% | CA-shaped-orphan | documented_scope_exclusion |

Large genuine moves (|ret|>=40%, non-CA-shaped, not CA-explained): **2720** — disclosed for operator review, not HALT.

## Arm B — Cross-symbol handoff (shape-free)

**4 splice fabrication(s)** — |adjusted return| >= 20% across a symbol boundary. 4 dispositioned; **0** undocumented (HALT).

| Entity | From | To | Date | Return | Disposition |
|--------|------|----|------|-------:|-------------|
| NEUEON | NTL | NEUEON | 2025-12-23 | +110.2% | relisting_after_suspension: NTL (INE333I01036) -> NEUEON (INE333I01044); FV-only event, no factor; 315 missed sessions |
| CLCIND | SPENTEX | CLCIND | 2026-01-30 | -88.1% | relisting_after_suspension: SPENTEX (INE376C01020) -> CLCIND; factor 100 applied; 1343 missed sessions |
| INDOSOLAR | INDOSOLAR | WAAREEINDO | 2025-06-19 | +65.1% | relisting_after_suspension: INDOSOLAR (INE866K01015) -> WAAREEINDO; factor 100 applied; 1473 missed sessions |
| DELPHIFX | WEIZFOREX | EBIXFOREX | 2020-04-21 | +31.4% | relisting_after_suspension: WEIZFOREX -> EBIXFOREX (via DELPHIFX); ISIN identical, no capital event; 33 missed sessions |

## Arm C — prev_close identity

0 violations. Ratio identity holds for all consecutive sessions; no first-session ex-date is unadjusted.

## Arm D — Factor evidence

1116 factors with adjacent-session evidence tested. 16 flagged (16 dispositioned, **0** undocumented).

| Symbol | Ex-date | Factor | Failure | Disposition |
|--------|---------|-------:|---------|-------------|
| AHLEAST | 2022-10-06 | 0.6667 | wrong_ratio | evidence_exception |
| BIRLAPOWER | 2010-10-20 | 0.8333 | no_reprice | evidence_exception |
| CUPID | 2018-10-11 | 0.8333 | no_reprice | evidence_exception |
| GMBREW | 2018-05-21 | 0.8000 | no_reprice | evidence_exception |
| IGARASHI | 2018-09-27 | 0.8899 | no_reprice | evidence_exception |
| KWALITY | 2010-06-15 | 0.5833 | wrong_ratio | evidence_exception |
| MENONBE | 2016-08-30 | 0.8333 | no_reprice | evidence_exception |
| OMAXE | 2013-11-11 | 0.7959 | no_reprice | evidence_exception |
| OSWALSEEDS | 2024-02-02 | 0.8333 | no_reprice | evidence_exception |
| PRADIP | 2013-02-12 | 0.8333 | no_reprice | evidence_exception |
| RADIOCITY | 2020-03-12 | 0.8000 | no_reprice | evidence_exception |
| RAIREKMOH | 2015-03-16 | 0.8571 | no_reprice | evidence_exception |
| SADHNANIQ | 2023-07-05 | 0.8182 | no_reprice | evidence_exception |
| SAHPETRO | 2013-07-09 | 0.4524 | wrong_ratio | evidence_exception |
| STAMPEDE | 2017-01-10 | 0.8000 | no_reprice | evidence_exception |
| TTML | 2013-08-07 | 0.8824 | no_reprice | evidence_exception |

## Disposition Register

The sole permitted exclusion. Sources: 46 ETF unit splits, 18 demergers, ca_scope_exclusions, ca_evidence_exceptions.

## Task 2 — Historical Completeness Proof

Each past defect re-appears in the named arm at its pre-repair commit:

| # | Defect | Arm | Commit | Re-appeared? | Detail |
|---|---|---|---|:--:|---|
| 4a | DTIL missing factor | A | `07572e4` | **YES** | DTIL in large_genuine: ret=-0.3348 (factor 2/3 > 0.5, not CA-shaped; surfaced per methodology) |
| 4b | DVL spurious factor | D | `07572e4` | **YES** | DVL violations: 1 (f=0.6667, no_reprice+wrong_ratio) |
| 5 | F-7 LITL prev_close | C | `af55c64` | **YES** | LITL violations: 1, adj_prev_close=576.7 (expected ~576.70) |
| 6 | PHILIPCARB orphan factor | A | `4ef4dfb` | **YES** | PHILIPCARB violations: 1 (ret=-0.7900, cls=CA-shaped-orphan) |
| 7 | ISIN-merge splices | B | `7c42a0c` | **YES** | 547 splice fabrications re-appeared, worst: PATANJALI RUCHISOYA->PATANJALI ret=+30923.9% |
| 8 | rename-path splices | B | `d408a68` | **YES** | 4 splices: ['CLCIND', 'DELPHIFX', 'INDOSOLAR', 'NEUEON'] |

## Task 4 — Fragmentation (4 unbridged capital events)

Fragmenting INDOSOLAR/WAAREEINDO, SUJANATWR/NTL/NEUEON, SPENTEX/CLCIND, EBIXFOREX/WEIZFOREX: PASS — Arm B splices: [] (expect []); membership identical; rows=7,030,920

## Old invariant -> arm mapping

| Old | Absorbed by | Notes |
|-----|-------------|-------|
| I-1 adj_close continuity | Arms A+B (+ Arm D) | Arm D adds the evidence quadrant |
| I-2 prev_close column | Arm C | |
| I-5 first-session | Arm C pred. 2 | |
| I-8 gate-(b) 20-symbol | Arm C | entity grain, ALL entities, no sample |
| I-3 co-trading | KEPT (guard) | precondition for arms |
| I-4 double-apply | KEPT (guard) | precondition for arms |
| I-6/I-7/I-9/I-10 | KEPT (guards) | |

## New executable files

- `scripts/psb1/contract_arms.py` — the four-arm contract suite
- `scripts/psb1/disposition_register.py` — the committed disposition register
- `scripts/psb1/historical_backtest.py` — the Task 2 completeness proof


**SUBSTRATE CERTIFIED — the four-arm contract holds.**

