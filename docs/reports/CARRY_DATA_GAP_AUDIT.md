# Carry Substrate — Data Gap Audit

**Run:** 2026-07-21 · read-only queries against the live stores · no data mutated
**Purpose:** close every data gap before any Carry implementation prompt is issued.
**Scope:** the substrate the Carry sleeve consumes — futures, spot, corporate actions, entity
machinery, sector, index. Options coverage checked as a by-product (Skew readiness).

---

> **⚠️ STATUS 2026-07-22 — G1, G2, G3 and G5 are all CLOSED. Re-measured, not assumed.**
> · **G1** index history: 3,563 files 2012-02-21 → 2026-07-21, Gate A + Gate B both ALL PASS
>   (see §2 banner and `CARRY_G1_R4_VERIFICATION.md`).
> · **G2** sector: Tier 1 285→302, hand register 60→43, `evidence` column added, 0 unclassified.
>   The 17.6% error rate had a root cause — a bare `except: pass` hid a 404 on
>   `ind_niftyconsumerdgoodslist`, so real names fell into the hand register.
> · **G3** equity tail: `equity_bhavcopy` now 2010-01-04 → 2026-07-21 (7,052,381 rows, 0 duplicate
>   keys); the adjusted VIEW auto-propagated. **The futures↔spot join in §1.1 is now
>   100.00% — 0 misses across all 477,577 FUTSTK cells**, up from 99.69%.
> · **G5** ISIN: all 11 mapped from the NSE listed master (3,628 → 3,639 rows, 0 lost, 0 changed).
>
> **Still open:** G4 needs nothing (option (a), settled) · G6 is document-only · the 43 delisted
> sector names remain unsourced · **participant-wise OI (§6) is not ingested** and remains the
> highest-value remaining fetch in the project.

## Verdict

**The futures + spot substrate is in far better shape than the design docs assumed.** The
futures↔spot join — the join that fabricates a basis when it slips, and the single largest
risk in this sleeve — is **99.69% complete with every miss confined to one known tail**.

Three gaps remain. Ranked by whether they block:

| # | Gap | Blocks | Fixable? |
|---|---|---|---|
| **G1** | **No Nifty 50 daily history before 2023-01-02** | **§4 beta neutralization on TRAIN + HOLDOUT — hard blocker** | Yes — free NSE download |
| **G2** | **No sector classification anywhere** | **§4 sector neutralization — hard blocker** | Yes, ~95%+, in three tiers |
| G3 | Equity spot ends 2026-07-09, futures 2026-07-20 | Sealed read only | Yes — re-run 11 days |
| G4 | No dividend announcement dates | **Downgraded — see below** | Not worth an ingest |
| G5 | 11 FUTSTK names have no ISIN | Sealed window only | Defer |
| G6 | 12 special-session dates absent from futures | Nothing | Document, don't "fix" |

---

## 1. What is clean (verified, not assumed)

### 1.1 Futures↔spot join — 99.69%
477,577 (name, date) FUTSTK cells. **1,470 have no same-session EQ-series spot close = 0.308%.**
Every single one falls in **2026-07-10 → 2026-07-20** (G3, the equity tail). Miss count for
2016-02-11 → 2026-07-09 is **zero**. The symbol join between the two feeds needs no repair.

### 1.2 EQ/BE series — no fan-out risk
Zero (symbol, date) cells carry both an EQ and a BE row, so filtering `series='EQ'` cannot
double-count. Distressed names do enter BE (RCOM 974 days, MCLEODRUSS 581, RELINFRA 529,
DHFL/SREINFRA/RNAVAL), but NSE removes names from F&O around the same transition — which is
why the EQ-only join loses nothing. **Certified as fact, not assumed.**

### 1.3 Near-month selector — fully feasible
98.6% of cells (470,990) carry **3 live expiries**; 3,422 carry 2; 3,165 carry 1. The T−3 roll
rule always has a next contract to roll into. Multi-expiry also means basis-momentum stays a
free later add, as `SIGNAL_ENGINE_DESIGN.md` §2.1 claimed.

### 1.4 Universe breadth — healthy across the whole window
Names per session by year: 2016 avg 173 · 2018 avg 206 · 2020 avg 140 (the trough) ·
2022 avg 196 · 2025 avg 216. Comfortably inside the pre-reg §2 expectation of ~120–180
post-liquidity-screen, and cross-sectional breadth never collapses.

### 1.5 Entity machinery — complete
`symbol_entity_intervals` covers **363 of 363** FUTSTK names. `symbol_isin` covers 352/363
(G5). `symbol_changes` covers 88 — expected, only renamed names appear.

### 1.6 Corporate actions over the F&O universe
Since 2016-02-11: **1,545 dividends · 114 bonuses · 58 splits**, across 322 of 363 names.
Dense enough that Arm C has real work to certify, not a token pass.

### 1.7 Options — Skew is unblocked now
2,571 distinct option dates vs 2,572 futures dates. **Two futures dates lack options data**
(2016-07-28, 2017-04-10). `SIGNAL_ENGINE_DESIGN.md` §2.1's "ingest in progress" is stale — the
stock-options store is complete at 98.3m rows, 2016-02-11 → 2026-07-20, 363 underlyings.

---

## 2. G1 — No index history for the beta leg (**CLOSED 2026-07-22 — read the banner first**)

> **⚠️ SUPERSEDED. This section describes the store as of 2026-07-21 and is now false.**
> The 1d index store holds **3,563 files, 2012-02-21 → 2026-07-21**, with
> `NSE_INDEX|Nifty 50` on every one; 252-session beta is computable from **2013-02-19**, so
> §4 beta neutralization runs on TRAIN and HOLDOUT as pre-registered. **Gate A and Gate B
> both ALL PASS**, including B1 cross-source agreement at **0.0000** index points against
> operator CSVs. Getting here took six verification rounds and cost 59 sessions to an ad-hoc
> deletion along the way — see `CARRY_G1_R4_VERIFICATION.md` and the `CARRY_G1_R*` chain.
> **Do not re-fetch index history on the strength of the text below.**

Pre-reg §4 requires residualizing against **trailing 252-day beta to Nifty**. The only index
series in the repo is `data/market_data/nse/candles/1d/{date}.duckdb` — 867 daily files
covering **2023-01-02 → 2026-07-03** and holding `NSE_INDEX|Nifty 50`, `Nifty Bank`,
`India VIX`.

**That is the sealed window and nothing else.** TRAIN (2016-03 → 2020-12) and HOLDOUT
(2021-01 → 2022-12) have **no Nifty series at all**, and beta needs a further 252-day warmup
before the first formation — so the requirement runs back to ~2015-03.

This was not flagged in either design doc. Half of §4's neutralization is currently
uncomputable on the exact windows it must run on.

**Fix — free, same download method already working.** NSE publishes a daily all-indices close
file on the same `nsearchives` host the futures/options bhavcopy ingests already pull from
(`ind_close_all_<DDMMYYYY>.csv` pattern). One file per session gives Nifty 50 OHLC — plus every
sectoral index as a by-product. Verify the archive actually reaches back to 2015 before
committing to the range; if it stops short, the fallback is a panel-derived market proxy
(cap- or equal-weighted mean return of the eligible universe), which is defensible but is a
**deviation from §4's text and must be written into the pre-reg before freeze, not after**.

---

## 3. G2 — Sector classification (**hard blocker, but you are right that it is downloadable**)

No sector/industry field exists in any store. Quantified coverage of the candidate sources:

| Source | Covers | TRAIN+HOLDOUT cell coverage |
|---|---|---|
| `nifty200_current.csv` (the only sector data in-repo) | 192 of 363 names (52.9%) | **61.8%** — unusable |
| Current NSE listed master (`equity_l.csv`, 2,384 symbols) | **311 of 363 (85.7%)** | — |
| **Gap: delisted / renamed** | **52 names** | **14.8% of cells** |

The 52 names absent from any current NSE file:

> ABIRLANUVO, ALBK, AMARAJABAT, ANDHRABANK, BHARATFIN, CADILAHC, CAIRN, CAPF, CENTURYTEX,
> CROMPGREAV, DALMIABHA, DHFL, EQUITAS, GMRINFRA, GSPL, GUJGASLTD, HDFC, HEXAWARE, IBREALEST,
> IBULHSGFIN, IDFC, IDFCBANK, INFIBEAM, INFRATEL, JETAIRWAYS, JPASSOCIAT, KPIT, L&TFH, LTI,
> LTIM, MCDOWELL-N, MINDTREE, MOTHERSUMI, NIITTECH, ORIENTBANK, PEL, PVR, RDEL, RELCAPITAL,
> RELINFRA, RNAVAL, SINTEX, SKSMICRO, SREINFRA, SRTRANSFIN, SYNDIBANK, TATAGLOBAL, TATAMOTORS,
> TATAMTRDVR, TV18BRDCST, UJJIVAN, ZOMATO

**The survivorship shape, quantified.** Cells belonging to these names by year:
2016 **346** · 2017 **489** · 2018 **466** · 2019 321 · 2020 196 · 2021 182 · 2022 181. The gap
is **concentrated in early TRAIN and decays monotonically** — exactly the bias pattern a
current-snapshot source produces. A naive "use the current index file" approach would leave
sector-neutralization weakest precisely where the sample is oldest.

**Three-tier fix gets to ~95%+ with no judgment calls fitted to results:**

1. **Live names (311).** NSE industry classification, downloadable. Same archive host.
2. **Renamed / merged (most of the 52).** Inherit the successor's sector through the entity
   map — `symbol_entity_intervals` already covers **363/363**, so the link exists. HDFC→HDFCBANK,
   MINDTREE/LTI→LTIM, MOTHERSUMI→SAMVARDHANA, TATAGLOBAL→TATACONSUM, ZOMATO→ETERNAL,
   IDFC→IDFCFIRSTB, ALBK/ANDHRABANK/SYNDIBANK/ORIENTBANK→acquiring PSU banks. Sector is
   unchanged through a rename or a same-industry merger, so this is inheritance, not inference.
3. **Genuinely dead (JETAIRWAYS, DHFL, SINTEX, RNAVAL, SREINFRA, RELCAPITAL, …).** BSE's scrip
   master carries industry for delisted names, and `corporate_actions.scripcode` already holds
   BSE scrip codes. Whatever survives that goes into a **small committed manual register** —
   legitimate here because the sector of ~10 well-known Indian companies is public fact, not a
   parameter that can be tuned toward a result.

Report coverage at every tier; pre-register the UNCLASSIFIED rule (own dummy bucket vs. drop
from formation) **before** seeing which names land there.

---

## 4. G4 — Dividend announcement dates: **downgraded, do not build an ingest**

Measured against 82 monthly formations (2016-03 → 2022-12) and 14,732 (name, formation) cells:

- Cells with a dividend ex-date falling in `(t, t+35d]`: **229 = 1.55%**
- When it hits, it is large: median `D/S` **0.678%**, p90 2.065%, max 7.70% →
  **annualized basis step: median 7.07%, p90 21.5%**

Read this correctly, because the two facts point in opposite directions:

- **Rare** (1.55%) → the unverifiable-PIT concern is not load-bearing on mean rank-IC. Chasing
  BSE board-meeting dates back to 2016 for 1.55% of cells is a poor trade.
- **Large when present** → those cells land in the *tails* of the basis distribution, which is
  exactly where the top/bottom quintiles live. So the dividend **adjustment itself** (§3.2)
  still matters for the spread metric even though its **PIT-ness** doesn't.

**Recommendation: OPEN-1 option (a), and treat it as closed.** Use ex-date-known dividends,
disclose the bounded lookahead, and carry "IC without dividend adjustment" as a mandatory
robustness column. At 1.55% exposure the two columns should be near-identical; if they are not,
that divergence is itself the finding.

---

## 5. G5 / G6 — defer and document

**G5 — 11 names with no ISIN:** SAMMAANCAP, WAAREEENER, TMPV, GVT&D, SWIGGY, HYUNDAI,
GMRAIRPORT, PREMIERENE, LTM, ETERNAL, VMM. **Every one first appears in futures on 2024-12-11
or later** — entirely inside the sealed window, zero TRAIN/HOLDOUT impact. Several are renames
(TMPV, ETERNAL, LTM, VMM) that Arm B will need ISIN linkage for, so fix before the sealed read
— not now.

**G6 — 12 equity sessions with no futures data:** 2016-10-30, 2017-08-30, 2019-10-27,
2020-02-01, 2020-11-14, 2021-03-30, 2023-11-12, 2024-01-20, 2024-03-02, 2024-05-18, 2025-02-01,
2026-02-01. These are Muhurat sessions, Budget Saturdays, and special live-trading drills — not
ingest failures. Monthly formations taken as the last futures session of each month never land
on them. Document as known special-session exclusions; do not "repair."

---

## 6. Not a Carry gap, but the highest-value remaining ingest

**Participant-wise OI is still not ingested** — the Flow sleeve. Per `SIGNAL_ENGINE_DESIGN.md`
§2.1, composite power at n*=42 goes **3 sleeves ≈ 0.75 → 4 sleeves ≈ 0.86**. Flow is the sleeve
that carries the engine over the 0.80 hurdle, the file is free and published daily, and the
download method is now proven. It blocks nothing in Carry, but it is the single ingest with the
largest effect on whether the engine is ever demonstrable.

---

## 7. Recommended order

1. **Ingest Nifty 50 (and all-indices) daily history back to ~2015** → unblocks G1.
2. **Ingest sector, three tiers, with a coverage report** → unblocks G2.
3. Re-run 11 days of equity spot (G3) — trivial, can wait for the sealed read.
4. Then issue the Carry certification prompt (P2 in `CARRY_IMPLEMENTATION_PROMPTS.md`).

P1 (RFA declaration) and P3a (futures fee model) read no market data and are **unblocked by all
of the above** — they can go out now, in parallel with the two ingests.
