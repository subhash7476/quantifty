# G1 / G2 Remediation — Verification Review

**Reviewed:** 2026-07-21 · independent read-only verification of the G1 index ingest and the
G2 sector classification delivered against `CARRY_DATA_GAP_AUDIT.md`.
**Method:** measured the produced artifacts against the stores; no claim accepted on report.

---

## Verdicts

| Gap | Claim | Verdict |
|---|---|---|
| **G1 — index history** | unblocked, 2015-03-02 → 2026-07-21 | **ACCEPT with 3 defects** — data is real and correct; two fixes needed, one cosmetic |
| **G2 — sector classification** | unblocked, "100% coverage" | **REJECT — must be redone.** Coverage is 100% of *labels typed*, not of *sources consulted*, and the taxonomy is internally inconsistent in a way that breaks §4 neutralization |
| G3 — spot tail | deferred | **ACCEPT**, with one caveat to re-check |

---

## 1. G1 — ACCEPT with defects

### What verified clean

**Values are genuinely correct.** Spot-checked against known history:

| Date | Stored Nifty 50 close | Reality |
|---|---|---|
| 2015-03-02 | 8,956.75 | ✓ |
| 2020-03-23 | 7,610.25 | ✓ COVID low |
| 2022-12-30 | 18,105.30 | ✓ |
| 2023-01-02 | 18,197.45 | ✓ matches the pre-existing file |

**No unit errors, no fabricated seam.** Only 3 day-over-day moves exceed 8% across 2,762
sessions — 2020-03-12 (−8.3%), 2020-03-23 (−13.0%), 2020-04-07 (+8.8%) — all real COVID-crash
moves. The 2016 CNX→Nifty rename seam is clean: 2016-02-29 6,987.05 → 2016-03-01 7,222.30
(+3.4%) is the actual Budget-day rally, not a splice artifact. **Exactly one** Nifty 50 close
per file across all 2,762 files — no duplicates introduced by the rename mapping.

### DEFECT G1-1 (must fix) — schema divergence between old and new files

```
2015-03-02.duckdb   timestamp = VARCHAR      (new)
2022-12-30.duckdb   timestamp = VARCHAR      (new)
2023-01-02.duckdb   timestamp = TIMESTAMP    (pre-existing)
2026-07-01.duckdb   timestamp = TIMESTAMP    (pre-existing)
```

`store_candles()` in `scripts/g1_ingest_index_history.py:138` issues
`CREATE TABLE IF NOT EXISTS` with `timestamp VARCHAR` and inserts `trade_date.isoformat()`.
On the 2023+ files the table already existed as `TIMESTAMP`, so the store is now **split down
the middle at 2023-01-01** — the exact TRAIN/HOLDOUT ↔ SEALED boundary. Any consumer reading
the full span (beta needs precisely that) hits a type mismatch on UNION or a silent coercion.
Fix: normalize to `TIMESTAMP` across all 2,762 files.

### DEFECT G1-2 (must fix or document) — 58 missing sessions, all in 2015

Nifty 50 coverage against the equity trading calendar:

- beta-warmup + TRAIN (2015-03-02 → 2020-12-31): **1,387 of 1,445 sessions = 95.99%**
- HOLDOUT (2021-01 → 2022-12): **496 of 496 = 100.00%**

All 58 misses fall in 2015 and arrive in **contiguous blocks** (2015-03-24 → 03-30,
2015-04-06 → 04-23, …), which reads as archive gaps or a URL-pattern change, not random 404s.
They sit inside the 252-day beta warmup rather than inside TRAIN itself, so beta remains
computable — but on ~4% fewer observations at the start. Either re-attempt those dates against
an alternate NSE path, or document the reduced warmup density in the pre-reg before freeze.

### DEFECT G1-3 (cosmetic, note only) — leftover CNX symbols

1,904 rows across the first 400 files still carry `CNX` in the symbol. `CNX_TO_CURRENT`
(`g1_ingest_index_history.py:52`) maps 21 names; unmapped ones fall through to
`f"NSE_INDEX|{raw_name}"`, so e.g. `NSE_INDEX|CNX Nifty Junior` pre-2016 and
`NSE_INDEX|Nifty Next 50` post-2016 are two identities for one index. **Nifty 50 itself is
correctly mapped**, so beta is unaffected. Matters only if sectoral indices get used later.

---

## 2. G2 — REJECT, must be redone

### The headline number is not what it appears

"100% coverage, 363 names" is **100% of names given a label**, not 100% sourced. The audit
specified Tier 1 = *download NSE industry for the 311 live names*. That download was never
performed. Tier 1 remained the in-repo 192-name `nifty200_current.csv`, and the shortfall was
absorbed by hand-typing **156 entries** into a Python dict — of which **107 are live,
currently-listed names**, entered under a comment reading *"Live names not in NIFTY 200,
classified from public knowledge"* (`g2_ingest_sector_classification.py:86`). Tier 3 is
therefore larger than the sourced Tier 1, and its contents are model recall, not a feed.

### DEFECT G2-1 (fatal) — two incompatible taxonomies, and the split is not random

Tier 1 carries NSE's official 18-label macro scheme. Tier 3 invents a parallel 21-label scheme.
**Only 7 labels overlap. 32 distinct labels would become sector dummies.**

The same true sector lands in different buckets purely by tier:

| True sector | Tier 1 / 2 label | Tier 3 label |
|---|---|---|
| IT | INFY, TCS, WIPRO, LTI → `Information Technology` | KPIT, CYIENT, LTTS, BSOFT, TATATECH, MINDTREE → `IT` |
| Pharma | SUNPHARMA, CIPLA → `Healthcare` | ABBOTINDIA, AJANTPHARM, IPCALAB, SYNGENE → `Pharmaceuticals`; LALPATHLAB → `Healthcare Services` |
| Auto | MARUTI, TATAMOTORS, MOTHERSUMI → `Automobile and Auto Components` | APOLLOTYRE, CEATLTD, SONACOMS → `Automobile`; UNOMINDA → `Auto Ancillaries` |
| Oil & Gas | RELIANCE → `Oil Gas & Consumable Fuels` | IGL, MGL, PETRONET, GSPL → `Oil & Gas` |

**Why this is fatal rather than cosmetic.** §4 residualizes against sector dummies. If one
sector is split across two or three dummies, the regression cannot remove that sector's common
component — and, worse, **tier membership is correlated with survivorship and size** (Tier 3 =
delisted names plus names outside NIFTY-200, i.e. the smaller and the dead). So the "sector"
control would partially encode a **size/survivorship factor**, and the residual
`z_carry_neut` would be contaminated by it. The contamination is invisible downstream: the IC
read looks normal while the neutralization silently did the wrong job. This is exactly the
defect class the substrate-certification discipline exists to catch, arriving through the
sector door.

### DEFECT G2-2 (serious) — outright misclassifications from model recall

Sampled, not exhaustive:

| Symbol | Assigned | Actual business |
|---|---|---|
| BALKRISIND | `Chemicals` | Balkrishna Industries — off-highway **tyres** → auto ancillaries |
| SKSMICRO | `IT` | SKS Microfinance — **microfinance lender** → financials |
| HONAUT | `IT` | Honeywell Automation — **industrial automation** → capital goods |
| KFINTECH | `IT` | KFin Technologies — **registrar / transfer agent** → financials |
| PGEL | `Chemicals` | PG Electroplast — **electronics manufacturing** → consumer durables |
| KAYNES | `IT` | Kaynes Technology — **electronics manufacturing services** → industrials |
| ICIL | `Chemicals` | Indo Count — **home textiles** |
| PEL | `Consumer Goods` | Piramal Enterprises — **NBFC** → financials |
| STAR | `Healthcare Services` | Strides Pharma Science — **pharmaceuticals** |

Six of these are financial or industrial names labelled `IT` or `Chemicals`. A hand register
was sanctioned in the audit for **~10 genuinely dead names** where sector is public fact; it
was not sanctioned as the primary classification method for 156 names, and this error rate is
why.

### DEFECT G2-3 (mechanical) — Tier 2 collapses the entity map

`get_entity_map()` (`g2_ingest_sector_classification.py:217`) runs
`SELECT DISTINCT symbol, entity` into a `{symbol: entity}` dict. A symbol mapping to more than
one entity over time silently keeps whichever row arrives last — the exact recycled-ticker
failure mode `CLAUDE.md` documents ("an entity is not one symbol for all time"). Measured blast
radius: **1 symbol affected (DTIL, 2 entities)**, so today's damage is negligible — but the
mechanism is wrong and must not be carried into the certified path.

### DEFECT G2-4 — sector stored as time-invariant

One row per symbol, no validity interval. PEL (pharma → NBFC) and the demerged Tata Motors
entities genuinely changed sector inside the window. Lower priority than G2-1, but the schema
should carry `valid_from` / `valid_to` so a later fix is not a re-key.

---

## 3. G3 — accept, with a caveat to re-check

Deferral is correct per the audit. One thing to verify before the sealed read: the report says
NSE "hasn't published" the 2026-07-10 → 2026-07-20 equity bhavcopy. NSE publishes equity
bhavcopy same-day, so seven business days outstanding as of 2026-07-21 more likely indicates a
URL/format issue in the ingest for recent dates than an absent archive. Not blocking — but do
not assume it is an NSE-side gap when the sealed read eventually needs those days.

---

## 4. Required corrections

**G1 (both mechanical, no judgment):**
1. Normalize `timestamp` to `TIMESTAMP` across all 2,762 daily files.
2. Re-attempt the 58 missing 2015 sessions; if genuinely unavailable, document the reduced
   beta-warmup density in the pre-reg **before freeze**.

**G2 — redo, in this order:**
1. **Actually download NSE industry classification** for the 311 currently-listed names. This
   is the step that was skipped and the one that makes the taxonomy single-sourced.
2. **Pin one vocabulary — NSE's official macro-sector scheme — and map every name into it.**
   No parallel label set. If a Tier 2/3 name cannot be expressed in the Tier 1 vocabulary, that
   is a mapping problem to solve, not a licence to invent a label.
3. **Fix Tier 2** to resolve entities time-awarely rather than by dict collapse.
4. **Shrink the manual register to genuinely dead names only**, recording per name the evidence
   used (BSE scrip-master industry, or the successor entity it inherits from). BALKRISIND,
   HONAUT, SKSMICRO, KFINTECH, PGEL, KAYNES, ICIL, PEL and STAR must come from a source, not
   recall.
5. **Re-report coverage per tier after the redo**, and pre-register the UNCLASSIFIED rule before
   seeing which names land there.

Until G2 is redone, **P4 (signal build) stays blocked** — §4 sector neutralization cannot run on
a taxonomy that splits one sector across three dummies along survivorship lines.
