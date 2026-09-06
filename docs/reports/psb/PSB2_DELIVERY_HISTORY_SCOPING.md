# PSB-2 → Successor — Delivery-History Extension Scoping

**Date:** 2026-07-17
**Question:** C2's recommendation rests on a power projection whose SD is estimated from only 55 fortnightly formations over 2.3 years, because `deliv_pct` in the pinned store begins 2020-01-01. **Is that boundary an NSE-source limit (delivery data does not exist earlier) or an ingestion-side limit (it exists but we don't fetch it)?** The answer decides whether C2's foundation can be strengthened cheaply before any sealed-window read.

## Verdict: ingestion boundary, not a source limit

The pre-2020 delivery data was never fetched, not never published. Two independent facts establish this.

### 1. The store already reaches back to 2010 — only the delivery column stops at 2020

`equity_bhavcopy` (7,030,920 rows) carries price/volume from **2010-01-04**. `deliv_pct` is non-NULL only from **2020-01-01**. Coverage by year:

| Years | Price rows | deliv_pct non-NULL |
|---|---|---|
| 2010–2019 | ~3.76M | **0** |
| 2020–2026 | ~3.27M | ~2.95M |

The price series is a full decade longer than the delivery series *in the same table*. Whatever stopped delivery at 2020 did not stop price — so it is not a "no data before 2010" problem.

### 2. The ingester uses a delivery source that only exists from 2020

`scripts/csmp/ingest_equity_bhavcopy.py` auto-detects three source eras per date (its own docstring, verified 2026-07-08):

| Source | File | Span | Delivery? |
|---|---|---|---|
| **SECFULL** | `sec_bhavdata_full_{DDMMYYYY}.csv` | 2020-01-01 → present | **Yes** — *"the only delivery source"* |
| LEGACY | `cm{DD}{MON}{YYYY}bhav.csv.zip` | 2010-01-01 → 2024-07-05 | No — stored NULL |
| UDIFF | `BhavCopy_NSE_CM_..._F_0000.csv.zip` | fallback | No — stored NULL |

Per date the richest source wins (SECFULL > UDIFF > LEGACY). For 2010–2019 no SECFULL file exists, so the ingester falls back to LEGACY, which has no delivery field, and writes `deliv_pct = NULL`. **The 2020 boundary is exactly the SECFULL file's start date — a property of which file the ingester fetches, not of what NSE has published.**

## The concrete backfill path (lead — requires verification)

NSE published deliverable-position data before the consolidated `sec_bhavdata_full` file existed, in a **separate daily file** the current ingester does not consume:

- **MTO ("Market Trades to delivery") / security-wise deliverable position**, historically `MTO_DDMMYYYY.DAT`, archived under NSE's equities path (pattern `archives.nseindia.com/archives/equities/mto/MTO_DDMMYYYY.DAT`).
- This file carries per-symbol deliverable quantity and deliverable %, which is exactly what `deliv_qty` / `deliv_pct` need.

If this archive is reachable and parseable for 2012–2019, C2's SD could be re-estimated on ~9 years of delivery formations instead of 2.3 — strengthening (or falsifying) the recommendation **without touching the sealed 2023→2026 window**.

### What must be verified before committing to a backfill (open risks)

1. **Archive availability** — does NSE still serve historical MTO files at a stable URL, and how far back? (The ingester's SECFULL fetch already needs a session/cookie prime — `get_session()` in the ingester — so a naive curl will likely 403; availability must be tested through the same primed session, not a raw request.)
2. **Format/parse** — MTO is a fixed-layout `.DAT`, not the CSV the current parser handles; it needs its own reader.
3. **Series/symbol join** — MTO keys by symbol; it must join to the EQ-series rows and survive the same rename/entity-recycling handling the store already enforces (`symbol_entity_intervals`, `symbol_changes`).
4. **Substrate impact** — `equity_bhavcopy` feeds both PSB and CSMP. Backfilling a column is a store change and would follow the same copy-first / re-certify discipline as prior CSMP gate work; it is not a loader-local patch.
5. **This is a fourth source era** — it would extend the ingester's era map (add an `MTO` source for delivery-only backfill of 2012–2019), not replace SECFULL.

## Bottom line for the operator

The 55-observation limitation is **not fundamental** — it is an artifact of the ingester standardizing on the post-2020 consolidated file for delivery. The pre-2020 delivery data very likely exists at NSE in the MTO archive. Extending it would de-risk C2 far more cheaply than spending the one-shot sealed window on 2.3 years of evidence.

**Recommended next step:** a small, bounded feasibility probe — fetch and parse a handful of pre-2020 MTO files through the ingester's primed session to confirm (a) the archive serves them and how far back, and (b) the format parses and joins to EQ rows. That probe is read-only against NSE, touches no store and no sealed window, and converts "very likely" into a yes/no. Only if it passes does a store-backfill + re-certify + C2 re-estimate become the real path; if it fails, the successor pre-registration must instead own the 55-observation SD explicitly and the operator decides whether that is enough.
