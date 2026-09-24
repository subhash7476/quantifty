# PTMS — Gann Stage-1 Screen Report — **NON-CONFIRMATORY**

**Label: NON-CONFIRMATORY (GR-1.4). This screen is never confirmation, validation, or evidence
that a Gann construct works.** *(memo §10 "Description"; exposure label "signal —
non-confirmatory (GR-1.4)")*

Frozen protocol: `docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md`, SHA-256 `27640c87020e48add18f05e7c27a12517fb4648e5724648380874c2af3d1822a`. Register row G-S1 appended
`2026-09-19` before this read. Script: `scripts/ptms/gann/run_screen.py` at commit `9382720022e5ae9a88b9f08dbbd64766f7700705`. Seed 42. B = 1999.

## 1. Protocol and provenance

| Item | Value |
|---|---|
| Frozen protocol | `docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md` |
| SHA-256 | `27640c87020e48add18f05e7c27a12517fb4648e5724648380874c2af3d1822a` |
| Freeze commit | `2f5655b` |
| Script commit | `9382720022e5ae9a88b9f08dbbd64766f7700705` |
| Register row G-S1 appended | `2026-09-19` |
| Size-check record | `docs/reports/ptms/PTMS_GANN_STAGE1_SIZE_CHECK.json` |
| G-7 event list SHA-256 | `2d9c14cbb3cd7f27a317b66750b79a2c13c6f315547dd8427690143f59ae3ada` |
| P-2 CA enumeration commit | `156a2ce` |
| Panel content SHA-256 | `06b375ef9385a8d20c1d41be02d84f32c30755eac16db7dd0c635961de3a35fd` |
| Seed | 42 |
| B | 1999 |
| α (one-sided) | 0.05/3 |

## 2. Blind size check (recorded before unblinding)

| Construct | Rejections / panels | Rate | Limit 2α | Action |
|---|--:|--:|--:|---|
| GF-1 | 3 / 200 | 0.0150 | 0.0333 | screened |
| GF-4T/R8 | 0 / 200 | 0.0000 | 0.0333 | screened |
| GF-10 | 6 / 200 | 0.0300 | 0.0333 | screened |

## 3. Panel and exclusions

### GF-1

| Item | Count |
|---|--:|
| Eligible stock-weeks kept after OPEN-M and G-7 | 48373 |
| Formation dates entering T_c | 609 |
| Dates dropped by the 20-name floor (G-6b) | 0 |
| Observations excluded by OPEN-M | 100 |
| Observations excluded by G-7 (from the 115 G-7 events) | 12899 |

Dates dropped because the per-date IC was undefined (A.3-3a, OPEN-P):

| Leg | Real panel | Surrogate median |
|---|--:|--:|
| primary | 4 | 4.0 |
| placebo family (median over sets) | 1.0 | n/a |

Exclusion-loss share (D-BH); base = PIT-member stock-weeks on D_L, 61572 stock-weeks:

| Limb | Count | Share |
|---|--:|--:|
| state rules | 200 | 0.0032 |
| OPEN-M | 100 | 0.0016 |
| G-7 | 12899 | 0.2095 |
| G-6b floor | 0 | 0.0000 |
| entering | 48373 | 0.7856 |

### GF-4T/R8

| Item | Count |
|---|--:|
| Eligible stock-weeks kept after OPEN-M and G-7 | 60522 |
| Formation dates entering T_c | 606 |
| Dates dropped by the 20-name floor (G-6b) | 1 |
| Observations excluded by OPEN-M | 100 |
| Observations excluded by G-7 (from the 115 G-7 events) | 435 |

Dates dropped because the per-date IC was undefined (A.3-3a, OPEN-P):

| Leg | Real panel | Surrogate median |
|---|--:|--:|
| primary | 5 | 3.0 |
| placebo family (median over sets) | 53.0 | n/a |

Exclusion-loss share (D-BH); base = PIT-member stock-weeks on D_L, 61572 stock-weeks:

| Limb | Count | Share |
|---|--:|--:|
| state rules | 515 | 0.0084 |
| OPEN-M | 100 | 0.0016 |
| G-7 | 435 | 0.0071 |
| G-6b floor | 11 | 0.0002 |
| entering | 60511 | 0.9828 |

### GF-10

| Item | Count |
|---|--:|
| Eligible stock-weeks kept after OPEN-M and G-7 | 20048 |
| Formation dates entering T_c | 320 |
| Dates dropped by the 20-name floor (G-6b) | 13 |
| Observations excluded by OPEN-M | 45 |
| Observations excluded by G-7 (from the 115 G-7 events) | 285 |
| Contrast weeks excluded by OPEN-N | 0 |

Dates dropped because the per-date IC was undefined (A.3-3a, OPEN-P):

| Leg | Real panel | Surrogate median |
|---|--:|--:|
| primary | 272 | 264.0 |
| GF-10 time | 37 | 36.0 |
| GF-10 price | 39 | 37.0 |

Exclusion-loss share (D-BH); base = the A1 set before exclusions, 20378 stock-weeks:

| Limb | Count | Share |
|---|--:|--:|
| OPEN-M | 45 | 0.0022 |
| G-7 | 285 | 0.0140 |
| G-6b floor | 149 | 0.0073 |
| entering | 19899 | 0.9765 |

## 4. Primary results

| Construct | T_c | p_sur | Specificity p | Effect size | 2.5–97.5% surrogate interval |
|---|--:|--:|--:|--:|---|
| GF-1 | -0.0101 | 0.9530 | 0.9624 | -0.0078 | [-0.0114, +0.0069] |
| GF-4T/R8 | +0.0334 | 0.9800 | 0.0184 | -0.0131 | [+0.0339, +0.0581] |
| GF-10 | +0.0473 | 0.2140 | 0.9370 | +0.0097 | [+0.0138, +0.0631] |

**GF-1:**
**Retired from forward testing under this protocol.** *"No evidence, against a surrogate null, of an effect of the optimistic size that confirmation would need."* **Never** "Gann's rule is false"

**GF-4T/R8:**
**Retired from forward testing under this protocol.** *"No evidence, against a surrogate null, of an effect of the optimistic size that confirmation would need."* **Never** "Gann's rule is false"

**GF-10:**
**Retired from forward testing under this protocol.** *"No evidence, against a surrogate null, of an effect of the optimistic size that confirmation would need."* **Never** "Gann's rule is false"

GF-10 specificity leg (G-4): T(time) +0.0086 (51 dates), T(price) +0.1265 (49 dates), Δ = -0.1179, p = 0.9370 over 1999 joint surrogate panels.

## 5. Robustness variants

"Robustness variants and diagnostics are off the pass path. They are reported alongside the primary and can neither rescue a failed primary nor fail a passed one."

| Construct | Variant | T_c | Effect size | p_sur |
|---|---|--:|--:|--:|
| GF-1 | V-K3 | -0.0009 (609 dates) | +0.0014 | — |
| GF-1 | V1-MD | +0.0003 (607 dates) | +0.0026 | — |
| GF-1 | V1-P8 | -0.0061 (609 dates) | -0.0038 | — |
| GF-1 | V1-WK | +0.0030 (554 dates) | +0.0052 | — |
| GF-1 | V1-MO | +0.0095 (407 dates) | +0.0117 | — |
| GF-1 | V1-K3 | -0.0238 (608 dates) | -0.0216 | — |
| GF-1 | V-B5 | -0.0101 (609 dates) | -0.0083 | 0.9580 |
| GF-1 | V-B60 | -0.0101 (609 dates) | -0.0078 | 0.9525 |
| GF-4T/R8 | V-K3 | +0.0429 (607 dates) | -0.0036 | — |
| GF-4T/R8 | V4-WE67 | +0.0393 (606 dates) | -0.0071 | — |
| GF-4T/R8 | V4-WE72 | +0.0354 (606 dates) | -0.0111 | — |
| GF-4T/R8 | V4-AS | +0.0117 (425 dates) | -0.0347 | — |
| GF-4T/R8 | V4-CT | -0.0180 (421 dates) | -0.0644 | — |
| GF-4T/R8 | V-B5 | +0.0334 (606 dates) | -0.0110 | 0.9705 |
| GF-4T/R8 | V-B60 | +0.0334 (606 dates) | -0.0160 | 0.9955 |
| GF-10 | V-K3 | +0.0314 (266 dates) | -0.0062 | — |
| GF-10 | V10-IP | +0.0477 (323 dates) | +0.0101 | — |
| GF-10 | V10-H15 | +0.0430 (425 dates) | +0.0053 | — |
| GF-10 | R_T x 0.75 | +0.0461 (337 dates) | +0.0085 | — |
| GF-10 | R_T x 1.33 | +0.0398 (323 dates) | +0.0022 | — |
| GF-10 | N-DIR bull | +0.0511 (147 dates) | +0.0134 | — |
| GF-10 | N-DIR bear | +0.0199 (48 dates) | -0.0177 | — |
| GF-10 | N-SZ | undefined (0 dates) | undefined | — |
| GF-10 | V-B5 | +0.0473 (320 dates) | +0.0119 | 0.1660 |
| GF-10 | V-B60 | +0.0473 (320 dates) | +0.0045 | 0.3505 |

Effect sizes are against the primary's surrogate distribution (R-A); V-B5 and V-B60 use their own surrogate runs and report p_sur (R-A′).

## 6. Diagnostics

Price-level halves at the per-date median as-traded close on D_L (D-PL, floor 10 per half):

| Construct | Low half T_c | High half T_c | Stock-weeks without an as-traded bar on D_L |
|---|--:|--:|--:|
| GF-1 | -0.0098 (599 dates) | -0.0107 (603 dates) | 0 |
| GF-4T/R8 | +0.0346 (597 dates) | +0.0319 (600 dates) | 0 |
| GF-10 | +0.0567 (172 dates) | +0.0855 (154 dates) | 0 |

GF-1 store-history depth at D_L, in weeks (D-AA):

| Stratum | T_c |
|---|--:|
| < 144 | -0.0045 (139 dates) |
| 144-288 | -0.0159 (144 dates) |
| >= 288 | -0.0124 (326 dates) |

Per-stock φ (D-PS; stocks with ≥ 5 score-1 and ≥ 5 score-0 weeks; descriptive):

| Construct | Qualifying stocks | Outcome constant (left out) | Median φ | IQR | Share φ > 0 |
|---|--:|--:|--:|---|--:|
| GF-1 | 159 | 3 | -0.0103 | [-0.0510, +0.0327] | 0.447 |
| GF-4T/R8 | 167 | 0 | +0.0463 | [+0.0160, +0.0829] | 0.826 |
| GF-10 | 100 | 0 | -0.0241 | [-0.0523, +0.0862] | 0.480 |

## 7. GF-10 disclosures

| # | Disclosure |
|---|---|
| X-1 | **Structural zeros.** The 0 population includes stock-weeks that could not have scored 1: candidates with no earlier same-type move (`12246`) and weeks after the episode's one event (`5402`). A 1 appears once per episode; these zeros can repeat weekly. N-SZ reports T_c without them |
| X-2 | **Mixed anchoring.** Score-1 weeks measure O-R10 from the event timestamp; score-0 weeks measure it from the week-end |
| X-3 | **The contrast's outcome differs from the primary's.** The time-vs-price contrast uses one week-end-anchored outcome for every stock-week |
| X-4 | **An event already past its reference scores 0 by construction.** A decline long enough to overbalance in time may have broken the prior swing low first |
| X-5 | **Bull and bear pooling.** Gann's wording differs between the bull and bear clauses: "first time" and "at least temporarily" appear only in the bear clauses, "reaction" only in the bull price clause. Pooling is a research decision (G-2(b)). The bear "first time" is mirrored into bull by OD-6. N-DIR reports bull-only and bear-only T_c |
| X-6 | **The outcome anchor differs across primaries.** GF-10 anchors to its event; GF-1 and GF-4T/R8 anchor to the formation week-end |
| X-7 | **The 20-name floor is counted on the last-session eligible set** (A1), the narrowest reading |
| X-8 | **The O-R10 prior-penetration rule differs across primaries.** GF-10 scores 0 when its reference was already penetrated before the window (OPEN-12d). GF-1 and GF-4T/R8 score 1 whenever the reference is penetrated inside O_1 … O_5, whatever happened before (RR-6, literal G-2(a)) |

## 8. Limitations

- F-1: "Passing the surrogate leg means the real data differ from a weakly dependent stationary process in the way the statistic detects. Only the conjunction with the placebo leg supports Gann-specific content."
- F-2: "K3 is an explicitly labelled approximation of Gann's discretionary historical detector. Gann's own record departs from the strict rule in ≥ 7 of 61 swings (1912–14; a lower bound, holidays ignored)."
- F-3: "GF-1's calendar-day unit and GF-4T/R8's last-swing anchoring are design choices where Gann does not uniquely specify them."
- F-4: "GF-1 anchors are left-censored at 2011-03-25 or at listing; per-stock left-censoring is disclosed."
- F-5: "GF-10 = Gann-faithful source concept plus explicit operator/research conventions; it is not Gann's exact rule."
- F-6: "Pooling across the Nifty-100 panel is a statistical device for power, not a Gann claim."
- F-7: "The 2011-03-25 → 2022-12-30 window is signal-spent on this surface. This screen spends nothing new and can confirm nothing (GR-1.3)."
- F-8: "Robustness variants and diagnostics are off the pass path. They are reported alongside the primary and can neither rescue a failed primary nor fail a passed one."
- F-9: "A positive result would support Gann-specific content only if the construct beats its placebo or contrast controls as well as the surrogate null on the primary cell. A result driven by a few stocks, or matched under non-Gann scales, fractions or lags, is not Gann-specific."

## Appendix — per-stock φ (D-PS)

### GF-1

| Stock | Score-1 weeks | Score-0 weeks | φ |
|---|--:|--:|--:|
| ABB | 97 | 85 | -0.1580 |
| ABCAPITAL | 19 | 32 | +0.2278 |
| ABIRLANUVO | 107 | 131 | +0.0068 |
| ACC | 275 | 327 | -0.0242 |
| ADANIENSOL | 59 | 86 | +0.0112 |
| ADANIENT | 100 | 117 | -0.0124 |
| ADANIGAS | 7 | 6 | +0.2673 |
| ADANIGREEN | 55 | 63 | -0.0111 |
| ADANIPORTS | 285 | 328 | -0.0601 |
| ALKEM | 20 | 33 | +0.1663 |
| AMBUJACEM | 300 | 311 | +0.0212 |
| ANDHRABANK | 40 | 38 | +0.0265 |
| APOLLOHOSP | 152 | 174 | -0.1006 |
| ASHOKLEY | 169 | 207 | -0.0020 |
| ASIANPAINT | 141 | 177 | -0.0478 |
| AUROPHARMA | 194 | 199 | -0.0783 |
| AXISBANK | 292 | 321 | +0.0520 |
| BAJAJ-AUTO | 280 | 333 | +0.0130 |
| BAJAJAUTO | 177 | 202 | +0.0218 |
| BANDHANBNK | 121 | 101 | +0.0528 |
| BANKBARODA | 286 | 296 | -0.0383 |
| BANKINDIA | 103 | 158 | +0.0139 |
| BEL | 112 | 134 | +0.0185 |
| BERGEPAINT | 80 | 90 | -0.1059 |
| BFLSOFTWAR | 89 | 92 | -0.0665 |
| BHARATFORG | 142 | 169 | -0.0001 |
| BHARTI | 189 | 226 | -0.0458 |
| BHEL | 208 | 234 | -0.0343 |
| BIOCON | 48 | 56 | -0.0445 |
| BPCL | 120 | 188 | -0.0217 |
| BRITANNIA | 92 | 128 | -0.0949 |
| BSES | 95 | 105 | +0.1052 |
| CADILAHC | 163 | 176 | -0.0131 |
| CAIRN | 114 | 179 | +0.0145 |
| CANBK | 99 | 159 | -0.0635 |
| CASTROL | 23 | 25 | -0.0650 |
| CGPOWER | 113 | 121 | +0.0525 |
| CHLORIDIND | 123 | 138 | +0.0054 |
| CHOLADBS | 27 | 38 | -0.1299 |
| CIPLA | 223 | 239 | -0.0115 |
| COALINDIA | 297 | 313 | +0.0250 |
| COLPAL | 173 | 199 | -0.0442 |
| CONCOR | 242 | 279 | +0.0035 |
| CUMMINSIND | 200 | 189 | -0.1074 |
| DABUR | 153 | 197 | -0.0675 |
| DIVISLAB | 219 | 260 | -0.0395 |
| DLF | 260 | 300 | +0.0111 |
| DMART | 128 | 146 | -0.0196 |
| DRREDDY | 305 | 308 | +0.0359 |
| EICHERMOT | 205 | 207 | +0.1092 |
| ETERNAL | 18 | 21 | +0.2511 |
| FEDERALBNK | 120 | 137 | +0.1259 |
| GAIL | 276 | 337 | +0.0214 |
| GICRE | 75 | 81 | +0.0348 |
| GLAND | 35 | 43 | -0.0929 |
| GLAXO | 170 | 196 | +0.0346 |
| GLENMARK | 167 | 199 | +0.0178 |
| GMRAIRPORT | 46 | 59 | -0.1073 |
| GODREJCP | 249 | 286 | -0.0244 |
| GRASIM | 157 | 184 | +0.0010 |
| GSKCONS | 125 | 185 | +0.0663 |
| HAL | 5 | 8 | -0.2282 |
| HCLTECH | 10 | 18 | -0.2067 |
| HDFC | 278 | 335 | -0.0444 |
| HDFCAMC | 93 | 103 | -0.0350 |
| HDFCBANK | 182 | 252 | +0.0368 |
| HDFCLIFE | 110 | 112 | +0.0034 |
| HDIL | 23 | 33 | +0.0503 |
| HEROHONDA | 259 | 255 | -0.0245 |
| HINDALC0 | 290 | 322 | -0.0968 |
| HINDLEVER | 33 | 45 | -0.0348 |
| HINDPETRO | 254 | 320 | -0.0399 |
| I-FLEX | 265 | 257 | +0.0125 |
| IBULHSGFIN | 116 | 158 | +0.1024 |
| ICICIBANK | 280 | 332 | -0.0203 |
| ICICIGI | 105 | 117 | -0.0007 |
| ICICIPRULI | 77 | 81 | -0.0991 |
| IDBI | 56 | 99 | +0.0554 |
| IDEA | 188 | 200 | +0.0735 |
| IDFC | 104 | 113 | +0.0179 |
| IFCI | 20 | 35 | +0.2570 |
| IGL | 45 | 47 | -0.0177 |
| INDHOTEL | 61 | 68 | -0.0213 |
| INDIGO | 169 | 157 | +0.0285 |
| INDUSINDBK | 283 | 330 | +0.0448 |
| INDUSTOWER | 228 | 229 | +0.0471 |
| INFOSYSTCH | 142 | 160 | -0.0368 |
| INGVYSYABK | 17 | 28 | -0.1604 |
| IOB | 24 | 32 | +0.2833 |
| IOC | 188 | 187 | +0.0146 |
| IRCTC | 7 | 6 | +0.0976 |
| JINDALSTEL | 108 | 126 | +0.0975 |
| JPASSOCIAT | 72 | 84 | -0.0586 |
| JSWSTEEL | 277 | 336 | +0.0107 |
| JUBLFOOD | 34 | 44 | -0.1509 |
| KOTAKBANK | 260 | 352 | +0.0438 |
| L&TFH | 65 | 51 | -0.1242 |
| LICHSGFIN | 196 | 221 | -0.0499 |
| LICI | 8 | 12 | +0.0680 |
| LT | 228 | 272 | -0.0124 |
| LTI | 49 | 69 | -0.0673 |
| LUPIN | 283 | 313 | -0.0485 |
| M&M | 59 | 96 | +0.0142 |
| MARUTI | 270 | 343 | -0.0763 |
| MCDOWELL-N | 282 | 304 | -0.0144 |
| MOTHERSON | 174 | 193 | -0.0651 |
| MRF | 70 | 95 | +0.0000 |
| MUTHOOTFIN | 58 | 73 | -0.0262 |
| NAUKRI | 64 | 67 | -0.0593 |
| NHPC | 116 | 118 | -0.0215 |
| NIACL | 37 | 54 | -0.0275 |
| NICOLASPIR | 34 | 35 | -0.0680 |
| NMDC | 232 | 256 | -0.0221 |
| NTPC | 71 | 91 | -0.0103 |
| NYKAA | 19 | 20 | -0.1581 |
| OIL | 131 | 156 | -0.0104 |
| ONGC | 281 | 332 | -0.0082 |
| P&G | 28 | 30 | +0.0599 |
| PAYTM | 21 | 18 | -0.1188 |
| PETRONET | 190 | 250 | +0.0308 |
| PFC | 222 | 248 | +0.0357 |
| PIDILITIND | 162 | 190 | -0.0535 |
| PIIND | 33 | 32 | -0.1320 |
| PNB | 209 | 339 | +0.0166 |
| POWERGRID | 257 | 302 | -0.0002 |
| RANBAXY | 88 | 99 | -0.0836 |
| RCOM | 134 | 151 | +0.0034 |
| RECLTD | 183 | 181 | -0.0022 |
| RELCAPITAL | 35 | 42 | +0.1830 |
| RELIANCE | 216 | 257 | +0.0521 |
| RPOWER | 106 | 127 | +0.0893 |
| SAIL | 235 | 258 | -0.0190 |
| SBICARD | 49 | 77 | -0.0198 |
| SBILIFE | 114 | 133 | -0.0295 |
| SBIN | 296 | 317 | -0.0275 |
| SESAGOA | 274 | 304 | -0.0045 |
| SHREECEM | 15 | 29 | -0.1461 |
| SHRIRAMFIN | 228 | 263 | +0.0643 |
| SIEMENS | 109 | 139 | -0.0459 |
| SRF | 14 | 25 | +0.1852 |
| STER | 34 | 40 | -0.0520 |
| SUNDARMFIN | 13 | 13 | +0.2000 |
| SUNPHARMA | 288 | 324 | -0.0848 |
| SUNTV | 52 | 44 | -0.1580 |
| TATACHEM | 110 | 114 | +0.0452 |
| TATACONSUM | 133 | 141 | -0.0728 |
| TATAMOTORS | 296 | 317 | +0.0138 |
| TATAPOWER | 81 | 93 | +0.0171 |
| TATASTEEL | 170 | 184 | -0.0044 |
| TCS | 25 | 36 | +0.1793 |
| TECHM | 123 | 154 | -0.0496 |
| TITAN | 283 | 330 | +0.0094 |
| UBL | 172 | 193 | +0.0715 |
| ULTRACEMCO | 288 | 325 | -0.0777 |
| UNIONBANK | 114 | 121 | -0.1130 |
| UNIPHOS | 264 | 347 | +0.0443 |
| WIPRO | 52 | 53 | +0.0049 |
| YESBANK | 238 | 282 | -0.0790 |
| ZEEL | 64 | 86 | +0.1035 |

### GF-4T/R8

| Stock | Score-1 weeks | Score-0 weeks | φ |
|---|--:|--:|--:|
| ABB | 153 | 29 | +0.0982 |
| ABBOTINDIA | 30 | 7 | +0.0571 |
| ABIRLANUVO | 199 | 35 | +0.1170 |
| ACC | 542 | 60 | -0.0020 |
| ADANIENSOL | 120 | 25 | +0.1231 |
| ADANIENT | 263 | 44 | +0.1087 |
| ADANIGREEN | 94 | 24 | +0.0257 |
| ADANIPORTS | 531 | 81 | +0.0084 |
| ALKEM | 43 | 10 | +0.2181 |
| AMBUJACEM | 540 | 65 | +0.0069 |
| ANDHRABANK | 69 | 7 | +0.0017 |
| APOLLOHOSP | 280 | 46 | +0.0225 |
| ASHOKLEY | 313 | 63 | +0.0188 |
| ASIANPAINT | 534 | 70 | +0.0432 |
| AUROPHARMA | 355 | 38 | +0.1416 |
| AXISBANK | 541 | 68 | +0.0619 |
| BAJAJ-AUTO | 543 | 68 | +0.0822 |
| BAJAJAUTO | 301 | 78 | -0.0612 |
| BAJAJFINSV | 433 | 75 | +0.0561 |
| BAJAUTOFIN | 312 | 40 | +0.0835 |
| BANDHANBNK | 188 | 34 | -0.1164 |
| BANKBARODA | 518 | 63 | +0.0253 |
| BANKINDIA | 234 | 25 | +0.0331 |
| BEL | 204 | 37 | +0.0418 |
| BERGEPAINT | 156 | 14 | -0.0511 |
| BFLSOFTWAR | 163 | 29 | -0.0148 |
| BHARATFORG | 287 | 20 | +0.1108 |
| BHARTI | 501 | 96 | +0.1094 |
| BHEL | 382 | 57 | +0.0228 |
| BIOCON | 295 | 27 | +0.0206 |
| BOSCHLTD | 472 | 93 | -0.0239 |
| BPCL | 512 | 84 | +0.0940 |
| BRITANNIA | 347 | 38 | +0.0720 |
| BSES | 186 | 11 | +0.1031 |
| CADILAHC | 304 | 35 | +0.0303 |
| CAIRN | 254 | 35 | -0.0026 |
| CANBK | 230 | 26 | -0.1022 |
| CASTROL | 38 | 10 | +0.1035 |
| CGPOWER | 211 | 22 | +0.0252 |
| CHLORIDIND | 235 | 24 | +0.0737 |
| CHOLADBS | 60 | 5 | +0.1855 |
| CIPLA | 514 | 83 | +0.0169 |
| COALINDIA | 539 | 71 | +0.0425 |
| COLPAL | 523 | 72 | +0.0718 |
| CONCOR | 406 | 113 | -0.0489 |
| CUMMINSIND | 317 | 68 | +0.0528 |
| DABUR | 500 | 80 | -0.0058 |
| DIVISLAB | 429 | 50 | -0.0620 |
| DLF | 502 | 56 | +0.0738 |
| DMART | 238 | 36 | +0.0481 |
| DRREDDY | 544 | 67 | +0.0067 |
| EICHERMOT | 366 | 46 | +0.0674 |
| EMAMILTD | 114 | 16 | +0.0385 |
| ETERNAL | 34 | 5 | +0.0892 |
| FEDERALBNK | 222 | 33 | -0.0309 |
| GAIL | 530 | 78 | +0.0463 |
| GICRE | 125 | 31 | +0.1502 |
| GLAND | 67 | 11 | +0.0942 |
| GLAXO | 259 | 103 | -0.0323 |
| GLENMARK | 312 | 43 | +0.0963 |
| GMRAIRPORT | 87 | 13 | +0.0887 |
| GODREJCP | 487 | 48 | +0.0173 |
| GRASIM | 484 | 67 | +0.0342 |
| GSKCONS | 255 | 55 | -0.0813 |
| HAVELLS | 292 | 27 | +0.1055 |
| HCLTECH | 532 | 72 | +0.0848 |
| HDFC | 563 | 45 | +0.0575 |
| HDFCAMC | 172 | 24 | +0.0291 |
| HDFCBANK | 514 | 78 | -0.0146 |
| HDFCLIFE | 199 | 23 | +0.0846 |
| HEROHONDA | 535 | 63 | +0.0708 |
| HINDALC0 | 522 | 89 | +0.0234 |
| HINDLEVER | 517 | 78 | +0.0794 |
| HINDPETRO | 507 | 60 | +0.0176 |
| HINDZINC | 217 | 34 | +0.0150 |
| I-FLEX | 424 | 97 | +0.0365 |
| IBULHSGFIN | 239 | 35 | +0.0370 |
| ICICIBANK | 543 | 61 | +0.0279 |
| ICICIGI | 183 | 39 | +0.0104 |
| ICICIPRULI | 240 | 37 | +0.0463 |
| IDBI | 142 | 9 | +0.0203 |
| IDEA | 380 | 71 | +0.0889 |
| IDFC | 197 | 19 | -0.0453 |
| IFCI | 48 | 6 | +0.0693 |
| IGL | 84 | 8 | +0.1469 |
| INDHOTEL | 107 | 18 | +0.0008 |
| INDIGO | 294 | 32 | +0.0704 |
| INDUSINDBK | 537 | 72 | -0.0495 |
| INDUSTOWER | 378 | 79 | -0.0017 |
| INFOSYSTCH | 543 | 56 | +0.0137 |
| INGVYSYABK | 40 | 5 | -0.1768 |
| IOB | 47 | 5 | +0.1178 |
| IOC | 305 | 70 | +0.1476 |
| ITC | 517 | 83 | -0.0235 |
| JINDALSTEL | 204 | 28 | +0.0786 |
| JPASSOCIAT | 144 | 10 | +0.0365 |
| JSWSTEEL | 533 | 78 | +0.0702 |
| JUBLFOOD | 70 | 8 | -0.0262 |
| KOTAKBANK | 549 | 56 | +0.0222 |
| L&TFH | 97 | 19 | +0.0071 |
| LICHSGFIN | 382 | 33 | +0.0969 |
| LT | 548 | 56 | +0.0461 |
| LTI | 105 | 13 | +0.1048 |
| LUPIN | 533 | 62 | +0.0529 |
| M&M | 531 | 60 | +0.0649 |
| M&MFIN | 114 | 17 | +0.0466 |
| MARICO | 313 | 65 | +0.0520 |
| MARUTI | 534 | 77 | +0.0707 |
| MCDOWELL-N | 535 | 49 | +0.0868 |
| MOTHERSON | 317 | 50 | -0.0212 |
| MRF | 143 | 26 | +0.1273 |
| MUTHOOTFIN | 113 | 18 | +0.0657 |
| NAUKRI | 115 | 16 | +0.0053 |
| NESTLEIND | 148 | 22 | +0.0295 |
| NHPC | 191 | 43 | +0.0283 |
| NIACL | 66 | 25 | +0.1136 |
| NICOLASPIR | 259 | 39 | +0.0141 |
| NMDC | 435 | 53 | +0.0627 |
| NTPC | 504 | 89 | +0.0596 |
| NYKAA | 30 | 9 | +0.0889 |
| OIL | 247 | 40 | -0.0201 |
| ONGC | 514 | 97 | +0.0800 |
| P&G | 283 | 59 | -0.0699 |
| PAGEIND | 56 | 15 | -0.1429 |
| PETRONET | 376 | 64 | +0.0239 |
| PFC | 418 | 50 | +0.0551 |
| PIDILITIND | 304 | 48 | +0.0875 |
| PIIND | 52 | 13 | +0.1280 |
| PNB | 477 | 68 | +0.0399 |
| POWERGRID | 503 | 94 | +0.0486 |
| RANBAXY | 160 | 27 | +0.0437 |
| RCOM | 251 | 27 | +0.0478 |
| RECLTD | 326 | 37 | +0.0290 |
| RELCAPITAL | 234 | 19 | +0.0824 |
| RELIANCE | 543 | 57 | +0.0721 |
| RPOWER | 199 | 23 | +0.0553 |
| SAIL | 434 | 52 | +0.0725 |
| SBICARD | 116 | 10 | +0.1533 |
| SBILIFE | 210 | 37 | +0.0994 |
| SBIN | 534 | 74 | +0.0650 |
| SESAGOA | 496 | 80 | +0.1017 |
| SHREECEM | 297 | 42 | +0.0683 |
| SHRIRAMFIN | 442 | 46 | -0.0200 |
| SIEMENS | 547 | 45 | +0.0793 |
| SRF | 34 | 5 | +0.1107 |
| STER | 66 | 7 | +0.0674 |
| SUNDARMFIN | 11 | 15 | +0.2335 |
| SUNPHARMA | 527 | 81 | -0.0084 |
| SUNTV | 71 | 25 | +0.1525 |
| TATACHEM | 204 | 41 | +0.0669 |
| TATACONSUM | 245 | 29 | +0.0008 |
| TATAMOTORS | 555 | 56 | +0.0307 |
| TATAMTRDVR | 68 | 10 | +0.1107 |
| TATAPOWER | 316 | 60 | +0.0544 |
| TATASTEEL | 535 | 58 | +0.0454 |
| TCS | 553 | 41 | +0.0315 |
| TECHM | 505 | 74 | +0.0419 |
| TITAN | 555 | 56 | -0.0557 |
| TORNTPHARM | 210 | 26 | -0.0443 |
| TORNTPOWER | 78 | 21 | +0.1739 |
| UBL | 299 | 66 | +0.0926 |
| ULTRACEMCO | 552 | 59 | +0.0247 |
| UNIONBANK | 204 | 30 | +0.0715 |
| UNIPHOS | 554 | 56 | +0.0421 |
| WIPRO | 510 | 77 | +0.0200 |
| YESBANK | 436 | 80 | +0.0122 |
| ZEEL | 413 | 72 | +0.0297 |

### GF-10

| Stock | Score-1 weeks | Score-0 weeks | φ |
|---|--:|--:|--:|
| ABB | 5 | 79 | -0.0393 |
| ACC | 11 | 209 | +0.0367 |
| ADANIENT | 5 | 81 | -0.0680 |
| ADANIPORTS | 6 | 195 | +0.0727 |
| AMBUJACEM | 14 | 188 | +0.0139 |
| ASIANPAINT | 8 | 184 | -0.0514 |
| AUROPHARMA | 8 | 121 | +0.0557 |
| AXISBANK | 11 | 196 | +0.0169 |
| BAJAJ-AUTO | 13 | 211 | +0.1834 |
| BAJAJAUTO | 5 | 158 | -0.0198 |
| BAJAJFINSV | 7 | 148 | -0.0507 |
| BAJAUTOFIN | 11 | 108 | -0.0595 |
| BANKBARODA | 12 | 162 | -0.0081 |
| BANKINDIA | 6 | 93 | -0.0365 |
| BHARATFORG | 5 | 108 | -0.0289 |
| BHARTI | 11 | 176 | -0.0625 |
| BHEL | 9 | 138 | +0.1311 |
| BIOCON | 6 | 76 | +0.1009 |
| BOSCHLTD | 8 | 164 | +0.0942 |
| BPCL | 11 | 200 | -0.0550 |
| BRITANNIA | 6 | 125 | -0.0480 |
| CADILAHC | 6 | 105 | -0.0571 |
| CAIRN | 5 | 62 | -0.0716 |
| CANBK | 7 | 81 | -0.0448 |
| CHLORIDIND | 6 | 84 | -0.0776 |
| CIPLA | 13 | 178 | +0.2165 |
| COALINDIA | 11 | 164 | +0.1161 |
| COLPAL | 10 | 215 | -0.0414 |
| CONCOR | 9 | 144 | +0.2111 |
| CUMMINSIND | 5 | 116 | -0.0474 |
| DABUR | 6 | 156 | +0.1346 |
| DIVISLAB | 7 | 170 | -0.0497 |
| DLF | 9 | 157 | -0.0539 |
| DRREDDY | 13 | 192 | +0.0340 |
| EICHERMOT | 10 | 137 | +0.0543 |
| GAIL | 12 | 169 | +0.0182 |
| GLENMARK | 7 | 103 | +0.2654 |
| GODREJCP | 10 | 201 | -0.0471 |
| GRASIM | 5 | 161 | -0.0311 |
| HAVELLS | 8 | 110 | -0.0567 |
| HCLTECH | 11 | 197 | -0.0531 |
| HDFC | 12 | 189 | +0.1138 |
| HDFCAMC | 5 | 52 | -0.0414 |
| HDFCBANK | 10 | 194 | +0.0819 |
| HEROHONDA | 12 | 195 | +0.1256 |
| HINDALC0 | 8 | 252 | +0.0732 |
| HINDLEVER | 11 | 169 | -0.0619 |
| HINDPETRO | 10 | 205 | +0.0490 |
| I-FLEX | 10 | 171 | -0.0408 |
| ICICIBANK | 13 | 212 | +0.0797 |
| ICICIPRULI | 6 | 114 | -0.0526 |
| IDEA | 6 | 126 | -0.0625 |
| IDFC | 5 | 76 | -0.0658 |
| INDUSINDBK | 12 | 215 | -0.0558 |
| INDUSTOWER | 8 | 157 | -0.0399 |
| INFOSYSTCH | 14 | 187 | +0.0960 |
| ITC | 13 | 158 | -0.0676 |
| JPASSOCIAT | 5 | 40 | -0.0533 |
| JSWSTEEL | 15 | 191 | +0.0315 |
| KOTAKBANK | 10 | 206 | +0.1295 |
| LICHSGFIN | 7 | 131 | +0.0459 |
| LT | 18 | 193 | +0.0715 |
| LUPIN | 12 | 176 | -0.0432 |
| M&M | 13 | 189 | +0.0134 |
| MARICO | 9 | 142 | +0.0920 |
| MARUTI | 15 | 231 | +0.0157 |
| MCDOWELL-N | 10 | 170 | +0.0324 |
| MOTHERSON | 8 | 150 | -0.0321 |
| NICOLASPIR | 7 | 100 | -0.0521 |
| NMDC | 9 | 136 | +0.0630 |
| NTPC | 8 | 176 | +0.0852 |
| ONGC | 6 | 229 | -0.0284 |
| PETRONET | 6 | 132 | +0.3390 |
| PFC | 13 | 141 | +0.2079 |
| PIDILITIND | 8 | 111 | +0.1361 |
| PNB | 11 | 151 | -0.0655 |
| POWERGRID | 9 | 171 | +0.0994 |
| RECLTD | 8 | 99 | +0.1378 |
| RELCAPITAL | 6 | 67 | -0.0620 |
| RELIANCE | 10 | 203 | +0.1288 |
| SAIL | 5 | 130 | +0.2144 |
| SBILIFE | 5 | 71 | +0.2188 |
| SBIN | 8 | 176 | -0.0455 |
| SESAGOA | 9 | 173 | -0.0383 |
| SHRIRAMFIN | 8 | 124 | +0.3347 |
| SIEMENS | 13 | 195 | +0.0892 |
| SUNPHARMA | 9 | 228 | -0.0347 |
| TATACHEM | 5 | 71 | -0.0538 |
| TATAMOTORS | 11 | 194 | +0.1072 |
| TATAPOWER | 6 | 107 | -0.0609 |
| TATASTEEL | 10 | 219 | +0.0589 |
| TCS | 11 | 193 | -0.0542 |
| TECHM | 10 | 219 | -0.0351 |
| TITAN | 14 | 186 | +0.0270 |
| ULTRACEMCO | 13 | 191 | +0.0201 |
| UNIONBANK | 7 | 73 | -0.0611 |
| UNIPHOS | 10 | 153 | -0.0581 |
| WIPRO | 7 | 234 | -0.0299 |
| YESBANK | 7 | 170 | -0.0346 |
| ZEEL | 5 | 145 | -0.0572 |

