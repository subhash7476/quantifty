# Carry — Capacity Analysis

**Script-generated** — `scripts/signal_engine/carry/capacity_analysis.py`. Code commit `da3e3ba`.

**Generated:** 2026-07-23

**Protocol:** `CARRY_IMPLEMENTATION_BRIDGE.md` §6.2 — max AUM before ADV caps bind.

**Method:** for each formation date, construct the target book at increasing gross-exposure levels and measure the fraction of names whose equal-weight allocation exceeds 10% of trailing 20-day ADV (the binding cap).


---

## 1. Per-Window Cap Incidence (% names capped per leg, mean across formations)


| AUM (Cr) | TRAIN Long % | TRAIN Short % | HOLDOUT Long % | HOLDOUT Short % | Overall % |
|---:|--:|--:|--:|--:|--:|
| 1 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 2 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 3 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 5 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 7 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 10 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 15 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 20 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 30 | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% |
| 50 | 0.4% | 0.0% | 0.0% | 0.0% | 0.1% |
| 75 | 1.5% | 0.7% | 0.0% | 0.1% | 0.5% |
| 100 | 2.9% | 1.9% | 0.3% | 0.7% | 1.4% |

---

## 2. Capital Displacement (% of target capital reallocated by capping, mean)


| AUM (Cr) | TRAIN Long Displ | TRAIN Short Displ | HOLDOUT Long Displ | HOLDOUT Short Displ |
|---:|--:|--:|--:|--:|
| 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 2 | 0.0% | 0.0% | 0.0% | 0.0% |
| 3 | 0.0% | 0.0% | 0.0% | 0.0% |
| 5 | 0.0% | 0.0% | 0.0% | 0.0% |
| 7 | 0.0% | 0.0% | 0.0% | 0.0% |
| 10 | 0.0% | 0.0% | 0.0% | 0.0% |
| 15 | 0.0% | 0.0% | 0.0% | 0.0% |
| 20 | 0.0% | 0.0% | 0.0% | 0.0% |
| 30 | 0.0% | 0.0% | 0.0% | 0.0% |
| 50 | 0.0% | 0.0% | 0.0% | 0.0% |
| 75 | 0.3% | 0.0% | 0.0% | 0.0% |
| 100 | 0.8% | 0.0% | 0.1% | 0.0% |

---

## 3. Tail-Risk View (p90 of cap incidence — worst-formation-month exposure)


| AUM (Cr) | TRAIN p90 Long | HOLDOUT p90 Long |
|---:|--:|--:|
| 1 | 0.0% | 0.0% |
| 2 | 0.0% | 0.0% |
| 3 | 0.0% | 0.0% |
| 5 | 0.0% | 0.0% |
| 7 | 0.0% | 0.0% |
| 10 | 0.0% | 0.0% |
| 15 | 0.0% | 0.0% |
| 20 | 0.0% | 0.0% |
| 30 | 0.0% | 0.0% |
| 50 | 0.0% | 0.0% |
| 75 | 5.9% | 0.0% |
| 100 | 7.6% | 1.7% |

---

## 4. Thin-Name Tail — ADV Distribution

Median ADV of the 5th-percentile name (the binding name) across all formation dates, for each window. This is the ADV of the thinnest name that typically enters the book.


**TRAIN** — p5 ADV: **Rs 23.7 Cr** (range 14.4–66.1 Cr across 58 formations). At 10% cap: **Rs 2.37 Cr** max per name.

**HOLDOUT** — p5 ADV: **Rs 32.9 Cr** (range 18.0–57.5 Cr across 24 formations). At 10% cap: **Rs 3.29 Cr** max per name.


---

## 5. Ceiling

- Binding threshold: >10% of names capped per leg (mean across formations).

- **TRAIN ceiling:** Rs 100 Cr gross before caps exceed 10% (at 100 Cr: 2.9% long / 1.9% short capped).

- **HOLDOUT ceiling:** Rs 100 Cr gross (at 100 Cr: 0.3% / 0.7%).

- **Technical ceiling: Rs 100 Cr** gross (Rs 50 Cr/leg) — the ADV cap formula itself does not bind at any tested scale. The cap starts touching the thinnest names (~Rs 2.4 Cr/name in TRAIN) above ~Rs 50 Cr, but mean incidence stays below 10% through Rs 100 Cr.


**Finding: the ADV cap is not the binding constraint.** At Rs 100 Cr gross, only 2.9% of names are capped in TRAIN, 0.3% in HOLDOUT. The real capacity constraint is execution impact/slippage on the thin-name tail — a separate analysis (not ADV-capping). The p5 ADV is Rs 23.7 Cr (TRAIN) / Rs 32.9 Cr (HOLDOUT), giving 10%-cap headroom of Rs 2.4–3.3 Cr per name. With ~20–25 names per leg, the book can scale well past Rs 100 Cr before the cap formula itself compresses the edge.


**Implication for WS-E:** capacity is limited by slippage, not by formula. PAPER mode should size conservatively (Rs 1–5 Cr gross) and measure realized slippage before scaling. The cap ceiling of Rs 100 Cr is a soft upper bound — the practical ceiling is likely lower and set by market impact.

