# PSB-1 Phase 1 — Lead Review 8

**Subject:** Prompt 4 (CA register evidence audit, DVL→DTIL re-key, F-7 rider)
**Commit:** `4ef4dfb`
**Date:** 2026-07-14
**Reviewer:** Lead — independent verification against the live store. The implementer's
runner (`scripts/psb1/repair_ca_register.py`) was deliberately **not** re-run: re-running it
would only replay its own assertions.

---

## 0. Disposition

| | |
|---|---|
| **Prompt 4 deliverables** | **PASS.** Every claim P1–P7 verifies exactly, independently. |
| **A2 substrate certification** | **BLOCKED.** Not on Prompt 4's account — on a pre-existing defect Prompt 4 neither introduced nor was asked to look for. |

These two verdicts are separate and must not be collapsed.

The implementer's closing statement — *"Substrate is clean… OMAXE is the one item still needing
an operator disposition before the A2 substrate is certified"* — is **false**. A fabricated
return is sitting in the substrate right now, on an in-universe name, inside the dev fence. It
is invisible to **both** screens (the evidence screen and R1), which is why four rounds of
repair have walked past it.

---

## 1. Prompt 4 verification — every claim independently reproduced

Direct query against `data/market_data/equity_bhavcopy.duckdb`.

| Claim | Asserted | Lead-verified | |
|---|---|---|---|
| P1 — DVL 2021-08-05 return | −6.55% | prev_adj 300.7500 → adj 281.0500 = **−6.550%** | ✅ exact |
| P2 — DTIL 2021-08-05 return | −0.23% | prev_adj 347.4333 → adj 346.6500 = **−0.225%** | ✅ exact |
| P3 — no double-apply | DVL 0, DTIL 1 | DVL **0** rows, DTIL **1** row (f=0.666667), provenance on the moved row | ✅ |
| P4 — LITL 2010-01-04 prev_close | 576.70 → 57.67 | adj prev_close = **57.6700**; close **58.1000** unchanged | ✅ exact |
| P6 — first-session invariant | 0 violations | recomputed from scratch, no `alag` filter: **1** entity has a first-session ex-date, **0** violations of `adj_prev = raw_prev × cum(t) × f(t)` | ✅ |
| P7 — row conservation | 7,030,920 | adjusted **7,030,920** = raw **7,030,920** | ✅ |
| P7 — R1 | 220/2/1/34 | harness scan: 220 moves, 2 residue, 1 halt (KWALITY), 34 large-genuine | ✅ |
| Task 2 — STAMPEDE now flagged | flagged | `ca_evidence_exceptions`: STAMPEDE 2017-01-10, `no_reprice` | ✅ |
| Task 2 — 13 f≥0.75 no-reprice | 13 | exactly **13** enumerated | ✅ |
| Task 4 — OMAXE sole material suspect | 1 hit | OMAXE 2013-11-11, f=0.7959 | ✅ |
| DVL/DTIL cleared from exceptions | — | **0** remaining | ✅ |

**The engineering is sound.** Three things are right and worth recording:

- The new `LEFT JOIN events f` **cannot fan out**: `events` is `GROUP BY entity, ex_date`, so
  the join key is unique. Row conservation is *structural* here, not lucky.
- The F-7 fallback is algebraically correct. `cum` excludes the same-day factor
  (`x.ex_date > e.trade_date`), so `cum(t−1) = cum(t) × f(t)` — exactly
  `j.cum_price * COALESCE(f.price_factor, 1.0)`. It fires only where `prev_cum_price IS NULL`,
  i.e. exactly once per entity, on its first session.
- `apply_factor_overrides` is genuinely idempotent and asserts before it moves.

The two self-corrections the implementer disclosed (the `COUNT(DISTINCT factor)` double-apply
check; the first-session formulation) were checker bugs, correctly diagnosed and fixed without
touching the view. Right instinct, right disclosure.

---

## 2. F-8 — CONFIRMED unadjusted 5:1 split on an in-universe name (**HIGH**)

### The finding

`adjustment_factors` contains **4 rows that resolve to zero entity intervals.** The `events`
CTE inner-joins `symbol_entity_intervals`, so those factors are **silently discarded** — they
adjust nothing. Nothing in the codebase asserts they must resolve.

One is a live defect:

```
factor:  (PCBL, 2018-04-19, SPLIT, f=0.2000)     <- registered to the MODERN ticker
prints:  PCBL trades only from 2022-01-13        <- no interval covers 2018-04-19
         => the factor matches nothing => DROPPED

PHILIPCARB (2,986 prints, 2010-01-04 .. 2022-01-12) is the SAME COMPANY, pre-rename.
```

The split is real and PHILIPCARB took it. The raw prints are unambiguous:

```
RAW 2018-04-18 PHILIPCARB  close = 1128.50
RAW 2018-04-19 PHILIPCARB  open  =  228.90      228.90 / 1128.50 = 0.2028 ≈ f = 0.2
```

And it is **unadjusted in the substrate today**:

```
ADJ 2018-04-18 PHILIPCARB  close = 1128.50
ADJ 2018-04-19 PHILIPCARB  close =  236.95   ==>  −79.00%   FABRICATED
```

### Why this is not cosmetic

- **`PHILIPCARB` is in `universe_membership` from 2017-10-31 to 2018-06-29** (9 rebalances).
  The ex-date sits inside a membership window.
- **2018-04-19 is inside the dev fence** (`DEV_HI = 2022-12-31`) — the window the A2 candidates
  are screened on.
- A 5-day formation return (C1) spanning 2018-04-19 sees −79% and ranks PHILIPCARB the most
  extreme loser in the panel. This is direct contamination of the signal PSB-1 exists to certify.

### Why both screens missed it — structural, not an oversight

**1. The evidence screen cannot see it.** `record_evidence_exceptions` joins factors to prices
**by symbol**. `PCBL` has no prints in 2018, so the CA has no adjacent-session evidence and is
**excluded from the test population entirely** — not "passed", never tested. Prompt 4's Task 2
was built to catch *"CA registered but the stock didn't reprice."* This is the **dual** failure:
*"the stock repriced but the CA reached no prints."* The screen is structurally blind to it.

**2. R1 misclassifies it as genuine.** Run against the implementer's own harness:

```
factors known for entity PHILIPCARB : NONE
factors known for entity PCBL       : [(2018-04-19, 0.2), (2022-04-11, 0.5)]

PHILIPCARB 2018-04-19  ret = -79.00%
  large_genuine : [('PHILIPCARB', 2018-04-19, -0.790, 0.2100)]   <-- lands HERE
  residue_rows  : []
  undocumented  : []
```

R1 sees a −79% move on an entity with **no factors**, so nothing can explain it, so it is classed
`genuine` and filed in `large_genuine`.

> **Therefore "R1 unchanged 220/2/1/34" is literally true and is not evidence of a clean
> substrate. The defect is inside the 34.**

`large_genuine` is not a safe bucket; it is a sink. It needs triage, not a count. (9 of the 34
carry a clean CA ratio. Most of those are genuine collapses — DHFL, JetAirways, YesBank — or
demergers — Adani, Mastek, Arvind — a different CA class. I am **not** claiming 9 defects. I am
claiming the bucket is unaudited and demonstrably capable of hiding one.)

---

## 3. Root cause — entity fragmentation by security re-issue

An Indian ISIN is `INE` + issuer(4) + type(2) + serial(3). **A face-value change re-issues the
security**: same issuer, new serial.

```
PHILIPCARB  INE602A01015          INTEGRA   INE418N01027
PCBL        INE602A01031          ESSENTIA  INE418N01035
            ^^^^^^^^^ same issuer            ^^^^^^^^^ same issuer
```

Entity resolution keyed on the **full 12-char ISIN** therefore **severs a company at exactly the
corporate action it is supposed to adjust for.** The 5:1 split *is* what changed PHILIPCARB's ISIN.

The rename register does not rescue it. `symbol_changes` (1,050 rows) carries `DTIL→DPTL` and
`DPL→DVL` — which is how the Dhunseri chain resolved correctly — but **`PHILIPCARB→PCBL` is
absent.** The register is incomplete and nothing validates its completeness.

**Scope: 107 issuers have symbols sharing an ISIN issuer prefix but mapped to different entities.
~73 are `INE` (corporate equity)** — the real class. The rest are `INF` (fund/ETF) ISINs where a
shared AMC prefix is expected; that is a false positive of the prefix heuristic, discount it.

The 73 are transparently the same companies: `CASTROL/CASTROLIND`, `AVANTI/AVANTIFEED`,
`SUBEX/SUBEXLTD`, `PATANJALI/RUCHISOYA`, `TUBEINVEST/CHOLAHLDNG`, `ALOKTEXT/ALOKINDS`,
`PCBL/PHILIPCARB`, `ESSENTIA/INTEGRA`, …

Note `STAMPEDE/GATECH` (INE224E01), `RAJRAYON/RAJRILTD` (INE533D01) and `SIGNET/SIGIND`
(INE529F01) are in this list — several names already surfacing in the evidence screen are
entangled with the fragmentation class.

---

## 4. Disposition of all four orphan factors

Settled with the deterministic CA fingerprint `open(ex_date) / close(prev session) ≈ f` — the
test that nailed PHILIPCARB. Only the true pre-rename ticker breaks at exactly that date and ratio.

| Orphan factor | Verdict |
|---|---|
| `(PCBL, 2018-04-19, SPLIT, 0.2)` | **CONFIRMED DEFECT.** PHILIPCARB open_ratio **0.2028**, close_ratio 0.2100; last print 2022-01-12 abuts PCBL's first print 2022-01-13. In-universe. |
| `(ESSENTIA, 2022-02-03, SPLIT, 0.3333)` | **Fragmentation confirmed** (INTEGRA: 951 prints before the ex-date, shared issuer INE418N01) **but no symbol repriced at ~⅓ on 2022-02-03.** The registered ex-date does not match any price break. Needs adjudication: wrong ex-date, or the split was effected in the 2022-02-28 → 2022-03-14 gap. **Not** currently a fabricated return. |
| `(KMSUGAR, 2010-03-26, SPLIT, 0.2)` | **INERT.** No symbol repriced ×0.2 that day; all KMSUGAR prints (from 2010-08-30) post-date the ex-date, so the factor can never enter `cum(t)`. Harmless. |
| `(VASWANI, 2011-09-29, BONUS, 0.8)` | **INERT.** All VASWANI prints (from 2011-10-24) post-date the ex-date. |

### A false finding I nearly filed — and the F-12 it exposes

The open-ratio search returned `PGEL` for VASWANI at **open_ratio = 0.8001** — exactly the shape
of a mis-keyed 1:4 bonus (the DVL→DTIL signature). **It is not.** The raw prints:

```
PGEL 2011-09-29  prev 386.60  open 309.30   -> 0.8001
PGEL 2011-10-03  prev 303.65  open 242.95   -> 0.8001
```

`PGEL` was a post-IPO collapse repeatedly **opening at the −20% lower circuit**. A circuit-limit
open is numerically identical to `f = 0.80`.

> **F-12 (MEDIUM) — `rekey_candidate` has a systematic false-positive mode.** At `f ≈ 0.80` it
> cannot distinguish a 1:4 bonus from a −20% lower-circuit open; at `f ≈ 1.20`, from the +20%
> upper circuit (see `RADIOCITY` → `GAYAHWS (open=1.2000)` in the exception table). The column is
> a **lead generator, not evidence**, and must be labelled as such before an operator sees it.
> DVL→DTIL was confirmed by the BSE register plus the company name — *not* by ratio search.
> **No row may be re-keyed on `rekey_candidate` alone.**

---

## 5. Findings ledger

| ID | Sev | Finding |
|---|---|---|
| **F-8** | **HIGH** | PHILIPCARB 2018-04-19 5:1 split unadjusted → fabricated −79% on an in-universe name inside the dev fence. Pre-existing; the re-key did not create it (DTIL's interval covers 2021-08-05). **Blocks substrate certification.** |
| **F-9** | **HIGH** | No invariant asserts that every `adjustment_factors` row resolves to exactly one entity interval. 4 resolve to zero and are silently dropped by `events`. Cheap halt condition. **Necessary but not sufficient** — a CA dated *after* a missed rename resolves fine yet still misses the pre-rename entity, so F-9 alone does not close the general class. |
| **F-10** | **MEDIUM** | R1's CA-shape test runs on **close-to-close**, so a normal intraday move on the ex-date pushes a clean split outside `MAGNITUDE_TOLERANCE` and into `large_genuine`. PHILIPCARB is the proof: close ratio **0.2100** (5% off f=0.2 → misses) vs open ratio **0.2028** (1.4% off → would hit). The evidence screen already uses the open; R1 should too. |
| **F-11** | **MEDIUM** | **Two entity resolvers disagree.** `screening_harness.load_factors_by_entity:219` joins `adjustment_factors` to **`universe_eligibility`** on symbol with **no date condition**; the view's `events` CTE uses **time-aware `symbol_entity_intervals`**. Hence the harness believes entity PCBL owns a 2018 factor while the view drops it. Prompt 3 migrated the view to interval resolution but left the R1 path on the old map. One register must have one resolver. |
| **F-12** | **MEDIUM** | `rekey_candidate` circuit-limit false positives at f≈0.80 / f≈1.20 (§4). Lead generator, not evidence. |
| **F-13** | **LOW** | `large_genuine` is presented as "honest disclosure" but functions as an unaudited sink. Needs per-row triage, not a count. |

---

## 6. Prompt 5 — authorized scope

Not implemented here; this is a review. Prompt 5 is authorized to address, **in this order**:

1. **Invariant first (F-9).** Assert every `adjustment_factors` row resolves to exactly one
   `symbol_entity_intervals` row; **HALT** otherwise. This is the guard that would have caught
   F-8 on day one. It must land *before* any repair, so the repair is verifiable.
2. **Entity linkage (F-8 root cause).** Link entities by **ISIN issuer prefix**, not full ISIN,
   so a face-value re-issue no longer severs a company. Scope: ~73 `INE` issuers. Every merge
   must be individually evidenced (shared issuer prefix **and** abutting print ranges) — not
   applied in bulk on the prefix alone. Note `symbol_isin` holds one ISIN per symbol and will
   need to become time-aware for this to be exact.
3. **Re-verify** PHILIPCARB 2018-04-19 adjusts to ≈ 0% (split absorbed) and that R1's
   `large_genuine` loses that row.
4. **F-10** — move R1's CA-shape test to the open ratio (or dual open/close, gate-(b)'s convention).
5. **F-11** — collapse the two resolvers to one.
6. **Do not** bulk-disposition the 13 f≥0.75 no-reprice CAs or OMAXE on `rekey_candidate`
   evidence (F-12). Those remain open for operator adjudication.

**OMAXE is no longer the last item.** It now sits behind F-8/F-9.

---

## 7. Reproduction

Read-only against `data/market_data/equity_bhavcopy.duckdb`.

```sql
-- F-9: orphan factors (4 today; must be 0 after Prompt 5)
SELECT af.symbol, af.ex_date, af.action_type, af.factor
FROM adjustment_factors af
WHERE NOT EXISTS (
  SELECT 1 FROM symbol_entity_intervals i
  WHERE i.symbol = af.symbol
    AND af.ex_date >= i.valid_from AND af.ex_date < i.valid_to);

-- F-8: the fabricated return (−79.00% today; must be ≈0% after Prompt 5)
SELECT trade_date, symbol, prev_close, close
FROM equity_bhavcopy_adjusted
WHERE symbol = 'PHILIPCARB' AND trade_date BETWEEN '2018-04-18' AND '2018-04-19';

-- root cause: same issuer, different entity
SELECT SUBSTR(si.isin,1,9) AS issuer, COUNT(DISTINCT ue.entity) AS n_ent,
       STRING_AGG(DISTINCT si.symbol, ' / ') AS syms
FROM symbol_isin si
JOIN universe_eligibility ue ON ue.symbol = si.symbol
WHERE si.isin LIKE 'INE%'
GROUP BY 1 HAVING COUNT(DISTINCT ue.entity) > 1;
```

---

## 8. Summary

Prompt 4 did what it was asked to do, correctly, and disclosed honestly. The DVL/DTIL thread is
closed. But the substrate is **not** clean: a 5:1 split on an in-universe name has sat unadjusted
in the panel through four rounds of repair — hidden by an evidence screen that never tested it and
an R1 bucket that waved it through as a genuine −79% move. The mechanism that hid it — a company
severed into two entities by the very corporate action that needs adjusting — is the correct
target for Prompt 5.

**Prompt 4: PASS. A2 substrate: NOT CERTIFIED.**

---

## 9. Amendment (same day, post-review verification)

Two corrections to my own §5/§6, made after verifying claims I had *inferred* rather than
executed. Neither changes the disposition. **§6 item 4 as originally written would have
misdirected Prompt 5, and is corrected here.**

### 9.1 F-10 — right conclusion, wrong constant; remedy now verified

I named `MAGNITUDE_TOLERANCE` as the gate. **That is wrong.** `MAGNITUDE_TOLERANCE = 0.25` is
only consulted when a factor **spans** the move (`audit_corporate_actions.py:282`) — which for
PHILIPCARB never happens, because its factor was dropped. PHILIPCARB falls to the
`is_ca_shaped(ret, prev_close)` branch (line 289), whose gate is **`CA_RATIO_TOLERANCE = 0.02`**
against `CA_RATIOS = [0.5, 0.4, ⅓, 0.25, 0.2, ⅙, 0.1, 0.05, 0.02, 0.01]`.

Executed, not inferred:

```
PHILIPCARB 2018-04-19   prev_close=1128.50  open=228.90  close=236.95

  close-implied survived = 0.2100   -> 4.98% from 0.2   is_ca_shaped = False   <- R1 today
  open-implied  survived = 0.2028   -> 1.42% from 0.2   is_ca_shaped = True    <- the fix
```

**The remedy holds.** The 2% tolerance sits between the two, so moving the shape test to the open
ratio converts PHILIPCARB from `genuine` to `CA-shaped-orphan` — i.e. into RESIDUE, into the halt
set, where it belongs. The reason is now precise: the **close-to-close ratio conflates the CA with
the ex-date's own intraday move** (PHILIPCARB rose ~5% intraday after the split), and a 5% move is
enough to push a clean 1:5 split outside a 2% shape tolerance. The open does not have this defect,
which is exactly why gate-(b)'s evidence screen already uses it.

**Prompt 5, §6 item 4 corrected:** move `is_ca_shaped` to the **open**-implied ratio (or accept a
hit on either open or close — gate-(b)'s dual-price convention). Do **not** widen
`MAGNITUDE_TOLERANCE`; it is not on this path and widening it would only loosen the
factor-explained test.

**Size of the F-10 class:** panel-wide (dev fence, >|20%|, no spanning factor under the *time-aware*
factor set, ≥Rs 5, gap ≤ 5) — **467** moves screened, **27** are CA-shaped on close (R1 catches
these), and **12** are CA-shaped on **open only** (R1 misses these). The 12 are a **candidate** set,
not 12 defects: most are demergers (SUVEN, IDFC, STAR, IIFL, BORORENEW) or ETF unit splits
(HNGSNGBEES, ICICINXT50), whose factors are legitimately absent from a split/bonus register.
**PHILIPCARB is the one confirmed unadjusted split among them.**

### 9.2 Mechanism reach ≠ defect count

§3 and §8 said the fragmentation "affects on the order of 73 issuers." A reader could take that as
73 defects. It is not. Stated precisely:

| | Count |
|---|---|
| INE issuers fragmented across ≥2 entities (**mechanism reach, upper bound**) | ~73 |
| Factors silently dropped (orphans) | **4** |
| **Confirmed live fabricated returns** | **1** (PHILIPCARB) |
| Fragmentation confirmed, CA needs adjudication | 1 (ESSENTIA/INTEGRA) |
| Inert (all prints post-date the ex-date) | 2 (KMSUGAR, VASWANI) |

The 73 is a **latent-trap and series-continuity hazard**, not 73 fabricated returns: where a
company is severed, each half is internally self-consistent, so no *within-entity* false return
appears unless a factor lands on the wrong side (PHILIPCARB) — but any code that splices the two
halves into one series will manufacture one, and the survivorship/continuity premise of the entity
grain is broken for all ~73.

**NOT CERTIFIED rests on the 1 confirmed defect, not on the 73.** The 73 is why Prompt 5 must fix
the *mechanism* rather than patch PHILIPCARB.

### 9.3 F-11 is larger than stated

Corroborating evidence for the two-resolver split: scanning with the **time-aware** factor set
(`symbol_entity_intervals`, the view's map) finds **27** close-CA-shaped moves with no spanning
factor, while R1 — using the **time-agnostic** `universe_eligibility` map — reports **1**
`CA-shaped-orphan`. The populations are not directly comparable (mine includes ETFs, which
gate-(b) excludes via `NON_EQUITY_PREDICATE`, and equities like FOURSOFT resolve to a spanning
factor under one map but not the other). The point stands regardless: **R1 classifies moves against
a factor set the adjustment view does not use.** Any R1 result is therefore evidence about a
substrate that was never built. F-11 should be treated as a **HIGH**, not a MEDIUM, and fixed
*before* F-10 — otherwise F-10's re-run measures the wrong thing.
