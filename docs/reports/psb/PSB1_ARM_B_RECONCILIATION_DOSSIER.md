# PSB-1 §11.1 — Arm B Reconciliation Dossier (4 splice fabrications)

**Purpose:** put every fact needed to disposition the four Arm B splices in one place, so the operator can verify each against NSE sources and record a decision.
**Prepared by:** Claude (Lead Reviewer), 2026-07-17. **Status:** for operator decision — **no code changed, nothing dispositioned.**
**Source:** `PSB1_SUBSTRATE_CERTIFICATION.md` §Arm B (line 114); all detail below queried read-only from `data/market_data/equity_bhavcopy.duckdb`.
**Blocks:** PSB-2 Phase 2 (§11.1 — "before any candidate score touches real data").

---

## The headline: all four are the same thing, and it is not the DVL→DTIL class

**These are not mis-keys.** Every one is a **relisting after a trading suspension**, where the entity link is corroborated by NSE's own `symbol_changes` record, and the "fabricated return" is the adjusted view computing a single-session return **across a gap of 33 to 1,473 missed sessions.**

**None of the four is a wrong link. All four are a real price move measured across a hole.**

And the fact that most changes the stakes:

> **None of these nine tickers has ever been in the NIFTY-200 universe — zero membership rows, ever. No candidate can score them. The result risk from these four is nil.**

Arm B halts anyway, and correctly so: it is a substrate contract with **zero structural filters** by design (`certify_substrate.py:265`). It tests the whole panel, not the universe. That is the point of it — a universe filter is exactly the "evidence-screen blind spot" the four-arm suite was built to remove. So this needs a **recorded disposition**, not a shrug — but it is a bookkeeping gate, not a live threat to any number.

---

## The four cases

### 1. INDOSOLAR → WAAREEINDO — 2025-06-19 — **+16,406.7%**

| | |
|---|---|
| Old symbol | `INDOSOLAR`, ISIN `INE866K01015`, traded 2010-09-29 → **2019-07-10**, 2177 rows |
| New symbol | `WAAREEINDO`, no ISIN in `symbol_isin`, traded **2025-06-19** → 2026-07-09, 184 rows |
| Last close (old) | **₹1.05** on 2019-07-10 (series BE) |
| First close (new) | **₹173.32** on 2025-06-19 (series BE) |
| Gap | **2,171 calendar days — 1,473 missed sessions (~6 years)** |
| NSE rename record | `symbol_changes`: `INDOSOLAR → WAAREEINDO`, 2025-06-17, "Indosolar Limited" |
| Corporate actions near boundary | **none** (±400/+120 days) |
| Window | **Sealed (2023–2026)** |

**Verify externally:** Indosolar was resolved through insolvency and acquired by Waaree. **The question that decides the disposition: was existing equity cancelled, reduced, or heavily diluted in the resolution plan?** If shareholders' claims were extinguished and re-issued, ₹1.05 and ₹173.32 are not the same instrument and no adjustment factor can bridge them — the series must break, not splice.

### 2. SPENTEX → CLCIND — 2026-01-30 — **+1,094.7%**

| | |
|---|---|
| Old symbol | `SPENTEX`, ISIN `INE376C01020`, traded 2010-01-04 → **2020-09-01**, 2584 rows |
| New symbol | `CLCIND`, no ISIN in `symbol_isin`, traded **2026-01-30** → 2026-07-06, 36 rows |
| Last close (old) | **₹0.75** on 2020-09-01 (series BE) |
| First close (new) | **₹8.96** on 2026-01-30 (series BE, volume 60) |
| Gap | **1,977 calendar days — 1,343 missed sessions (~5.4 years)** |
| NSE rename record | `symbol_changes`: `SPENTEX → CLCIND`, 2026-01-01, "CLC Industries Limited" |
| Prior chain | `SPENTXIND → SPENTEX`, 2006-12-20, "Spentex Industries Limited" |
| Corporate actions near boundary | **none** |
| Window | **Sealed (2023–2026)** |

**Verify externally:** same question as INDOSOLAR — Spentex Industries' ~5-year suspension and the capital structure on relisting as CLC Industries. Note the first session traded **60 shares**; the print is near-meaningless as a price.

### 3. NTL → NEUEON — 2025-12-23 — **+110.2%**

| | |
|---|---|
| Old symbol | `NTL`, ISIN `INE333I01036`, traded 2017-02-17 → **2024-09-16**, 1040 rows |
| New symbol | `NEUEON`, no ISIN in `symbol_isin`, traded **2025-12-23** → 2026-07-09, 48 rows |
| Last close (old) | **₹2.74** on 2024-09-16 (series BE) |
| First close (new) | **₹5.76** on 2025-12-23 (series BE) |
| Gap | **463 calendar days — 315 missed sessions (~15 months)** |
| NSE rename record | `symbol_changes`: `NTL → NEUEON`, 2025-12-22, "Neueon Corporation Limited" |
| Prior chain | `SUJANATWR → NTL`, 2017-02-17, "Neueon Towers Limited" |
| Corporate actions near boundary | **none** |
| Window | **Sealed (2023–2026)** |

**Verify externally:** the three-step chain Sujana Towers → Neueon Towers → Neueon Corporation, and what happened during the 15-month suspension. This is the least extreme of the four and the most likely to be a plain rename with no capital event.

### 4. WEIZFOREX → EBIXFOREX — 2020-04-21 — **+31.4%**

| | |
|---|---|
| Old symbol | `WEIZFOREX`, ISIN `INE726L01019`, traded 2011-06-28 → **2020-02-26**, 1991 rows |
| New symbol | `EBIXFOREX`, no ISIN in `symbol_isin`, traded **2020-04-21** → 2021-08-31, 342 rows |
| Last close (old) | **₹391.90** on 2020-02-26 (**series EQ**) |
| First close (new) | **₹514.80** on 2020-04-21 (**series BE**) |
| Gap | **55 calendar days — 33 missed sessions (~2 months)** |
| NSE rename record | `symbol_changes`: `WEIZFOREX → EBIXFOREX`, 2020-03-20, "DELPHI WORLD MONEY LIMITED" |
| Later chain | `EBIXFOREX → DELPHIFX`, 2021-09-01, "DELPHI WORLD MONEY LIMITED" |
| Corporate actions near boundary | **none** |
| Window | **Dev (2012–2022)** — the only one |

**This is the only case in a dev window, and it is the one worth the most scrutiny — for a reason the size doesn't advertise.** The gap spans **26 Feb → 21 Apr 2020**: the COVID crash, during which the market fell roughly a third and **NSE never closed.** This stock posted **+31.4%** across it. A real holder could not have earned that; the stock was suspended.

Two further tells: the **series flips EQ → BE** (trade-for-trade — a surveillance move, not a neutral rename), and the company-name field reads "DELPHI WORLD MONEY LIMITED" on a 2020 rename to *Ebix*Forex, which looks like the **current** name backfilled onto a historical row.

**Verify externally:** the Weizmann Forex → EbixCash World Money → Delphi World Money chain, the reason for the Feb–Apr 2020 suspension, the EQ→BE move, and whether any capital event accompanied it.

---

## What the pattern means

| | Old last trade | New first trade | Missed sessions | Return | Window |
|---|---|---|---:|---:|---|
| INDOSOLAR → WAAREEINDO | 2019-07-10 | 2025-06-19 | **1,473** | +16,406.7% | Sealed |
| SPENTEX → CLCIND | 2020-09-01 | 2026-01-30 | **1,343** | +1,094.7% | Sealed |
| NTL → NEUEON | 2024-09-16 | 2025-12-23 | **315** | +110.2% | Sealed |
| WEIZFOREX → EBIXFOREX | 2020-02-26 | 2020-04-21 | **33** | +31.4% | **Dev** |

The magnitude tracks the gap almost perfectly, which is the tell: **these are not signals, they are elapsed time.** Nothing here is a wrong entity link — every link has an NSE `symbol_changes` row behind it, and the union-find/interval machinery did what it was told. The view simply has **no concept of a suspension**: it takes the last observation under one ticker and the first under the next and calls the ratio a one-session return.

**No corporate actions exist near any of the four boundaries.** For a plain rename that is correct — a rename needs no factor. For an insolvency relisting it is the open question: if equity was cancelled or reduced, the missing record is not a factor but the fact that **the series should terminate rather than continue.**

---

## What you have to decide

**Decision 1 — are these four links right?** The dossier says yes on NSE's own records. Verify against the source, especially INDOSOLAR and SPENTEX, where insolvency may have extinguished the original equity. **If the equity was cancelled, the correct answer is not "adjust" — it is "these are different instruments and the entity interval must end."** That would be a genuine substrate defect rather than a disposition, and it is the one outcome that changes the work.

**Decision 2 — how is Arm B cleared?**

> **Correction (2026-07-17, before any action was taken).** An earlier draft of this dossier recommended **giving the view a gap rule** — "don't compute a return across a boundary spanning more than *N* missed sessions." **That recommendation was wrong, and the code says so explicitly. It is withdrawn.** It is recorded here, with its refutation, so it is not re-proposed later.

**Why a gap rule is the wrong answer — this is the load-bearing paragraph.**

The absence of a gap filter is not an oversight in Arm B. It is a **declared design property**:

- `contract_arms.py:11` — the suite is defined by "zero structural filters (no sample, no alag>0, no symbol-partition, **no MAX_GAP_DAYS**, …)".
- `arm_b` docstring (`:180`) — "**Any gap (no MAX_GAP_DAYS).** Rename-path and ISIN-merge alike."
- `certify_substrate.py:265` — `b_halt = arm_b.splices  # ALL splices HALT (none dispositioned)`.

Taken together those three lines describe a **ratchet**: Arm B is the one arm with **no exclusion path at all**, so *every* future relisting halts certification until a human looks at it. **A gap rule would make the next relisting pass silently** — which is exactly the structural-filter blind spot the four-arm suite was built to remove, and a direct contradiction of this program's own standing principle that *the disposition register is the only permitted exclusion*. The gap rule does not merely fail to help; it re-breaks what PSB-1 spent six prompts repairing.

A second, more concrete reason: **there is no stored fabricated return to "fix."** The adjusted view stores adjusted *closes*; Arm B computes the ratio itself with a `LAG` over the entity's observations (`_LAGGED_CTE`, `:78`). The only version of a gap rule that would actually silence Arm B is **breaking the entity interval** — and that corrupts entity-grain factor application for companies that, on NSE's own records, genuinely are continuous. Unnecessary, and risky in a way the original framing hid.

**The design-consistent path — and it is gated:**

- **The register is the only exclusion**, per `PSB1_CERTIFICATION_METHODOLOGY.md`. Arms A and D already have their lookups (`arm_a_excl`, `arm_d_excl`); **Arm B has none** — no splice has ever been dispositioned, so the mechanism was never built. Clearing these four therefore means **wiring the same register lookup into Arm B** (class `relisting_after_suspension`, with the evidence per case), which is a change to certified code plus a full suite re-run. The ratchet survives: future relistings still halt until dispositioned.
- **But this cannot be triggered until Decision 1 is resolved.** If INDOSOLAR's or SPENTEX's equity was cancelled or reduced in insolvency, those two are **not** benign renames to disposition — the correct action is **terminating the entity link**, a genuine substrate repair. Still not a gap rule; a different fix entirely.

**So the order is: verify externally (Decision 1) → then choose per case.** A case that is a plain rename across a suspension → disposition. A case where the old equity was extinguished → the entity interval must end. The two outcomes need different code, which is why the implementation prompt cannot be written until the verification comes back.

**Decision 3 — sequencing.** Three of the four are in the **sealed** window and one is in **dev** — and none is in NIFTY-200, so no candidate score is exposed either way. **§11.1 still gates Phase 2 on a recorded disposition**, so this needs an answer before Prompt 2 runs, but it is not a reason to expect any Phase 2 number to move.

---

## Verification checklist (external sources)

For each of the four, confirm from NSE circulars / exchange filings / company announcements:

1. The symbol-change circular and its effective date matches `symbol_changes`.
2. The **reason for the suspension** and its dates.
3. **Whether any capital event accompanied the relisting** — capital reduction, share cancellation, consolidation, fresh issue under a resolution plan. *(The decisive item for cases 1 and 2.)*
4. For case 4 only: why `WEIZFOREX` moved **EQ → BE**, and whether the Feb–Apr 2020 suspension was surveillance-driven.
5. Whether the new ticker's ISIN differs from the old (`symbol_isin` has **no ISIN recorded for any of the four new symbols** — worth confirming independently; a changed ISIN is itself evidence of a re-issued instrument, and PSB-1 already learned that an ISIN is not one entity for all time).
