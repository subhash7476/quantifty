# ISD Phase-1 Substrate Certification Report

Generated: 2026-08-26T13:29:46.996019 · runtime 828.2s · commit `2afaad8`

Sessions certified: **903** (2023-01-02 → 2026-08-24) · canonical capital ₹20,000,000 (Q4)

| Gate | Verdict | Key figures |
|---|---|---|
| G3 | PASS | normalized reader; drift abstracted |
| G2 | PASS | latest file 2026-08-24 |
| G4 | PASS | v1=36 (first-bar artifact=36, unexplained=0) v2=0 v3=0 v4=0 v5 unexplained=0 (ca-adjusted expected=5629); examples=[{'symbol': 'NSE_EQ|INE028A01039', 'timestamp': '2024-06-25 09:15:00', 'o': 273.4, 'h': 275.0, 'l': 273.9, 'c': 274.4}, {'symbol': 'NSE_EQ|INE976G01028', 'timestamp': '2024-06-25 09:15:00', 'o': 259.1, 'h': 261.16, 'l': 259.61, 'c': 260.0}, {'symbol': 'NSE_EQ|INE245A01021', 'timestamp': '2024-06-25 09:15:00', 'o': 436.0, 'h': 437.45, 'l': 436.6, 'c': 437.25}] |
| G1 | PASS | 903/903 sessions; defects=[]; special=['2026-02-01']; ledger entries=282 |
| G5 | PASS | rows=173900; cross-feed agreement=1.0; unresolved=0 |
| G6 | PASS | ticket table @ ₹20,000,000; slippage deciles pooled over 9237259 obs |
| G7a-d | PASS | 100 members; resolution=0.99; tail dropped=4701 |
| G7e | PASS | 2594882 bars compared; aligned within-tol=0.990568 (raw 0.827781); aligned median |Δ|=0.0; basis-offset=17; low-agree days=78 |
| G7f | PASS | 782 CA seams; fabricated=0 |

**Overall: PASS**

Snapshot: `data/isd/ISD_PHASE1_SNAPSHOT.json` (gitignored data tree; digests embedded above).
