# PTMS — Substrate Certificate

**CERTIFIED 2026-09-13 by operator ruling** — *"certify it, scoped to nifty 100 2023-01-02 to
2026-09-11."*

This is the certificate, not the evidence. The evidence is
`PTMS_P2_CERTIFICATION_UPDATE_2026-09-13.md`, pinned below by digest so that drift in it is
detectable rather than silent.

---

## 1. What is certified

| | |
|---|---|
| **Surface** | Equity breadth 1m — `NSE_EQ|INE…` rows in `data/market_data/nse/candles/1m/{date}.duckdb` |
| **Universe** | Nifty 100, point-in-time, from `data/isd/n100_membership.duckdb` (263 intervals, 216 distinct symbols) |
| **Window** | **2023-01-02 → 2026-09-11**, 917 trading sessions |
| **Clock** | Native era, **start-labelled**: the bar stamped *t* covers *t → t+1*. 917 of 917 sessions resolve native |
| **Price basis** | **Corporate-action adjusted** to the current basis. `equity_bhavcopy` is as-traded; the two stores disagree by the CA ratio before any ex-date |
| **Gates** | C1 timestamp semantics · C2 PIT & entity integrity · C3 tradeability & synthetics · C4 VIX |

## 2. What the certificate rests on

| Artifact | Size | SHA-256 (first 16) |
|---|--:|---|
| `docs/reports/index_research/PTMS_P2_CERTIFICATION_UPDATE_2026-09-13.md` | 20,609 | `44b86fb30c7bf521` |
| `data/isd/c1_labeling_census_eq.jsonl` | 262,372 | `dbe69587864c718c` |
| `data/isd/n100_membership.duckdb` | 798,720 | `0be19812766d5572` |
| `data/cas/cas_category.duckdb` (366 intervals, to 2026-09-11) | 798,720 | `dd11c1ff42f428fd` |

Repository state at certification: commit **`999bb9f`**, 2026-09-13.

**A digest is not a guarantee of immutability — it is a tripwire.** The 1m store itself is not
hashed: it is thousands of files and it legitimately grows. What is hashed is the universe, the
category table, the census, and the evidence. If a later reading disagrees with this certificate,
recompute these four first.

## 3. Gate evidence, in one line each

| Gate | Evidence |
|---|---|
| **C1** | Era rule as code that refuses an unrecognised stamp (`core/market/bar_labeling.py`); two agreeing event-anchored arms — the 09:15 opening print, and the CAS 15:15 halt where 15:14 carries traded bars on 30/30 post-CAS sessions and 15:15 on 0/30; census **917 files, 917 native, 913 OK, 4 GAP, 0 REFUSED, 0 MISDATED, 0 false synthetic** |
| **C2** | A1 discharged by substitution (membership built from press releases + 198 MCWB archives, independent of the candle store) · A2-1 closed · A2-2 resolved · A3 certified · A4 PASS · A5 vacuous under this universe · A6 scoped out · coverage **0 absent (session, name) cells across 917 sessions** |
| **C3** | `cas_category` rebuilt from the point-in-time futures bhavcopy to 2026-09-11; all 30 post-CAS sessions marked — **85,156 synthetic bars, 0 non-equity rows, 0 outside the auction window, 0 carrying volume** |
| **C4** | Complete per `PTMS_P2_CERTIFICATION_REPORT_2026-09-12.md` §3; 2021-02-12 permanently quarantined |

## 4. Residuals this certificate CARRIES

Certification does not erase these. It means they are known, bounded and declared.

1. **Four sessions are short ten minutes in total** — 2023-07-12 (14:57), 2023-07-24 (12:49–12:51),
   2023-08-07 (15:23), 2024-04-23 (10:52–10:57, 10:54 present). Whole-market outages; every symbol
   absent. **Not repaired by argument**: the only probe is a re-fetch, and the fetcher upserts onto
   today's CA basis, which could leave a symbol on a mixed basis within its own history.
2. **HDFC is absent from 130 sessions** (2023-01-02 → 2023-07-12) — delisted at the merger,
   unfetchable. **Accepted at 99/100 by operator ruling.** Its daily record is complete, so the
   loss is intraday only.
3. **Sector labels are out of scope** — A6 was scoped out, not built.

## 5. Obligations that ride with it

A certificate that nothing enforces is documentation. These are the conditions under which it
continues to hold.

1. **Eligibility must pin the HDFC exception, never relax to a tolerance.** Assert *100 names, or
   exactly 99 where the missing name is HDFC and the date is before 2023-07-13* — anything else
   hard-fails. A `≥ 99` rule would silently absorb the next absence.
2. **Declare the four GAP sessions; never assert 375 bars blindly.** Expected minutes come from
   `session_windows`, which knows Muhurat hours and split Saturdays.
3. **Resolve labelling from the observed first bar** (`core.market.bar_labeling`), refusing an
   unrecognised stamp. Never infer the era from the calendar date.
4. **Always filter `is_synthetic = FALSE`** for tradeability, and never apply a `volume = 0`
   predicate to `NSE_INDEX`.
5. **No sector label may be read** — not `governance/carry/sector_classification.csv`, not a
   sector/thematic constituent list, not as a post-hoc diagnostic. A design that needs one reopens
   A6 as a hard blocker.
6. **Never join 1m prices to `equity_bhavcopy` prices across a corporate action.** Different bases.
7. **Rebuild `cas_category` whenever `futures_bhavcopy` advances**, and re-run the CAS marker after
   any ingest touching post-CAS sessions. Nothing couples them; that is how the last gap opened.
8. **Add the next Muhurat to `SPECIAL_SESSIONS` before it happens.** A special session absent from
   that table falls back to the era schedule and is answered 09:15–15:30, wrong in both directions.

## 6. What this certificate does NOT cover

Stated so it cannot be stretched by silence.

- **Any date outside 2023-01-02 → 2026-09-11**, and in particular the **vendor era**. C1-a — the
  vendor bundle's own timestamp specification — remains an open operator dependency, and the
  store-wide census shows the vendor seam is a **per-symbol** property: on 2023-01-31 and across
  247 sessions in 2022, `NSE_INDEX|Nifty 50` is end-labelled while `Nifty Bank` and `India VIX`
  are not.
- **Any universe other than the Nifty 100.** A5's whole-panel halt is vacuous *here* because no A5
  item was ever an N100 or N200 constituent; it is not resolved.
- **Any symbol class other than `NSE_EQ`.** 1,822 `MCX_FO` rows still carry a false synthetic flag;
  11 index sessions in Apr–May 2025 carry post-close prints.
- **Every other surface** in the 09-12 matrix — 1d index family, equity/futures/options EOD — which
  still read UNCERTIFIED.
- **Tradeability beyond bar integrity.** This certifies what the bars *are*, not that a construct
  built on them will clear fees, capacity, or demonstrability. Those are RFA and battery questions.

## 7. Provenance of the repairs behind it

Every mutation went through committed, re-runnable code with the baseline taken **before** the
write — `data/_baselines/{cas_category_pre_rebuild_2026-09-13, 1m_pre_post_close_prune,
1m_pre_misdated_prune, 1m_pre_false_synthetic_clear, 1m_pre_n100_backfill, 1m_orphans}/` and the
per-file `.pre_cas_mark` snapshots.

| Repair | Scale |
|---|---|
| 1m coverage backfill to the N100 universe | mean absent 11.0 → 0.143 → **0** |
| Post-close print tails pruned | 466 rows, 4 sessions |
| Misfiled rows removed | 23,670 rows, 3 files |
| False synthetic marks cleared | 548 rows, 2 files |
| `cas_category` rebuilt | 210 intervals extended, 0 other changes |
| CAS marker run on the tail | 10 sessions, 28,660 bars |

---

**Certified by:** operator, 2026-09-13.
**Prepared by:** Claude Opus 5, at meta + substrate-verification access. No OHLC value entered a
feature, signal, label or fitted parameter in producing this certificate or its evidence.
