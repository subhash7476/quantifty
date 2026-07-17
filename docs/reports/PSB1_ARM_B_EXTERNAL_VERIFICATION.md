# PSB-1 §11.1 — Arm B External Verification Worksheet

**Companion to:** `PSB1_ARM_B_RECONCILIATION_DOSSIER.md` (committed `2d2dc21`) — that document holds the store-side facts. This one is the **outside-sources** task: what to look up, where, and what each answer decides.

**Who can run this:** the operator, or a research assistant / web-enabled model handed §A–§C verbatim. **Nothing here touches the repo.**

---

## A. The one question that decides everything

For each of four ticker handoffs, our substrate computed a single-session return across a multi-year trading gap. The entity links themselves are corroborated by NSE's own `symbol_changes` records, so the links are probably right. **What is not established is whether the shares before the gap and the shares after the gap are the same instrument.**

> **The decisive question, per case: between the last trade under the old ticker and the first trade under the new one, was the existing equity cancelled, reduced, consolidated, or re-issued — or did ordinary shareholders simply hold the same shares through a suspension and a name change?**

Why it decides the work:

- **Same shares, just renamed across a suspension** → the price move is real but unearnable (the stock wasn't trading). This is a bookkeeping exclusion — the case gets recorded in the disposition register with its evidence, and certification proceeds.
- **Equity cancelled / reduced / re-issued** → the two price series are **different instruments**, and no adjustment factor can bridge them. The entity link must be *terminated* at the gap. That is a real substrate defect and a different repair.

Nothing else in the lookup changes the outcome. Ignore anything that doesn't bear on this.

---

## B. Do the cheap test first — the ISIN

**This one field resolves most of the question in about ten minutes**, and it is the test PSB-1 already learned to trust.

Our store has **no ISIN recorded for any of the four new tickers** — that gap is why this worksheet exists. Look each one up and compare against the old ISIN on record.

| Case | Old symbol | **Old ISIN (on record)** | New symbol | **New ISIN (find this)** |
|---|---|---|---|---|
| 1 | INDOSOLAR | `INE866K01015` | **WAAREEINDO** | ? |
| 2 | SPENTEX | `INE376C01020` | **CLCIND** | ? |
| 3 | NTL | `INE333I01036` | **NEUEON** | ? |
| 4 | WEIZFOREX | `INE726L01019` | **EBIXFOREX** (later `DELPHIFX`) | ? |

**Where:** NSE publishes `EQUITY_L.csv` (the full equity list, symbol → ISIN) — the fastest source for currently-listed names. NSDL's ISIN search (`nsdl.co.in`) covers delisted and historical ISINs. BSE's scrip master is a useful cross-check.

**How to read the answer** — an Indian ISIN is `INE` + a 5-character **issuer code** + a 4-digit **serial**. Read the three parts separately:

| Finding | Meaning | Decides |
|---|---|---|
| **Identical ISIN** (e.g. WAAREEINDO = `INE866K01015`) | Same instrument, unbroken. A rename only. | → Plain rename. Disposition. |
| **Same issuer code, different serial** (e.g. `INE866K01015` → `INE866K0102x`) | Same company, but the security was **re-issued** — face-value change, consolidation, or a capital event. | → A capital event happened. Go to §C and find out which. |
| **Different issuer code** (e.g. `INE866K…` → `INE9xxZ…`) | **A different company.** The entity link is wrong. | → Decision 1 fails. Escalate — this is the DVL→DTIL class after all. |

The middle row is the one to be careful with. PSB-1 already learned that *an ISIN is not one entity for all time* — PHILIPCARB re-issued from `INE602A01015` to `INE602A01031` on a face-value change and remained the same company. So a serial change alone does **not** mean "different entity"; it means "a capital event you must identify."

---

## C. Per-case lookups

Only run these for a case where §B didn't already settle it.

### Case 1 — INDOSOLAR → WAAREEINDO (gap 2019-07-10 → 2025-06-19, ~6 years)

Indosolar Limited went through insolvency and the business was acquired by Waaree. **This is the highest-stakes case: a resolution plan very commonly extinguishes or massively dilutes existing equity.**

Find:
1. **The NCLT-approved resolution plan** and its treatment of existing equity shareholders. Search IBBI (`ibbi.gov.in`) for Indosolar Limited's CIRP, and NCLT order archives. Waaree Energies' filings and annual reports will describe the acquisition.
2. **Whether the plan cancelled, reduced, or diluted the pre-CIRP shares** — the exact words matter. "Reduction of share capital", "extinguishment", "cancellation of existing equity", or a consolidation ratio all count.
3. The **NSE relisting circular** for WAAREEINDO (June 2025) — relisting notices often state the revised capital structure explicitly.
4. Whether the trading suspension was due to insolvency proceedings, and its dates.

**If existing equity was cancelled or reduced: this is not a disposition, it is an entity termination.** Say so plainly in the record.

### Case 2 — SPENTEX → CLCIND (gap 2020-09-01 → 2026-01-30, ~5.4 years)

Same shape and same decisive question. Spentex Industries Limited → CLC Industries Limited, ~5-year suspension.

Find:
1. Spentex Industries' insolvency / restructuring history — IBBI, NCLT, and company announcements.
2. **Treatment of existing equity** on relisting as CLC Industries.
3. The NSE relisting circular (Jan 2026) and the capital structure it states.

*(Context, not a lookup: the first session under CLCIND traded **60 shares** at ₹8.96. Whatever the paperwork says, that print is near-meaningless as a price.)*

### Case 3 — NTL → NEUEON (gap 2024-09-16 → 2025-12-23, ~15 months)

Chain: Sujana Towers → Neueon Towers → Neueon Corporation. **The mildest case and most likely a plain rename** — but the 15-month suspension still needs a reason.

Find:
1. Why NTL was suspended from Sept 2024, and the relisting circular for NEUEON (Dec 2025).
2. Any capital event across the gap — Neueon Towers has an insolvency history worth confirming.
3. That the Sujana → Neueon Towers → Neueon Corporation chain is one continuous company.

### Case 4 — WEIZFOREX → EBIXFOREX (gap 2020-02-26 → 2020-04-21, 33 sessions)

**The only case in the dev window — the one that could touch a candidate number — and the most interesting for a reason its size hides.** The gap spans **26 Feb → 21 Apr 2020**: the COVID crash, through which the market fell roughly a third and **NSE never closed**. This stock shows **+31.4%** across it. No holder could have earned that; it wasn't trading.

Find:
1. **Why it was suspended Feb–Apr 2020**, and whether it was surveillance-driven.
2. **Why the series moved EQ → BE** (trade-for-trade). BE is a surveillance measure, not a neutral rename artifact — the reason matters.
3. Any capital event across the gap.
4. The chain: Weizmann Forex → EbixCash World Money → Delphi World Money. Our rename record for the **2020** change already carries the name "DELPHI WORLD MONEY LIMITED", which looks like the *current* name backfilled onto a historical row — **confirm what the company was actually called on 2020-03-20.** If NSE's contemporaneous circular says "EbixCash World Money", our `symbol_changes` name field is retroactively overwritten, which is worth knowing on its own.

---

## D. Record the answer in this shape

One block per case. **Cite the source for each answer** — a circular number, filing date, or URL. An unsourced answer is not usable here; the whole point is that it can be checked by someone else later.

```
Case:              INDOSOLAR -> WAAREEINDO
Old ISIN:          INE866K01015
New ISIN:          <found>            Source: <where>
ISIN verdict:      identical | same-issuer-new-serial | different-issuer
Suspension reason: <...>              Source: <...>
Capital event:     none | cancellation | reduction | consolidation | fresh issue
                                      Source: <...>
Existing equity survived the gap?     YES | NO | UNCLEAR
Finding:           plain rename across suspension
                   | capital event, entity continuous
                   | equity extinguished, different instrument
                   | link is wrong
```

**"UNCLEAR" is a legitimate answer** and better than a guess. Arm B halts either way; an unresolved case simply stays halted, which is the design working. Do not round an ambiguity up to "plain rename" to clear the gate — the standing rule in this program is that nothing is weakened to make a check pass.

---

## E. What each finding triggers

| Finding | Action | Touches |
|---|---|---|
| Plain rename across suspension | Disposition, class `relisting_after_suspension`, evidence attached | Wire the register lookup into Arm B (it has none today — `certify_substrate.py:265`) |
| Capital event, entity continuous | Register the missing factor, then re-run the suite — the splice may resolve on its own | `ingest_corporate_actions.py` |
| Equity extinguished / re-issued | **Terminate the entity interval at the gap.** A real substrate repair, not an exclusion | `symbol_entity_intervals` |
| Link is wrong | Escalate — DVL→DTIL class, a mis-key | Entity resolution |
| UNCLEAR | Nothing. Arm B stays halted. | — |

**A gap rule is not on this list, and will not be added to it.** See the dossier's Decision 2 for why: Arm B's `"Any gap (no MAX_GAP_DAYS)"` is deliberate, and filtering it would make every *future* relisting pass silently.

**Reminder on stakes:** none of these nine tickers has ever been in the NIFTY-200 universe — zero membership rows, ever. **No candidate can score them, so no Phase 2 number moves either way.** This gate is bookkeeping, and §11.1 requires it recorded before Prompt 2 runs. Verify it honestly rather than quickly; there is no result riding on the answer, which is exactly the condition under which it's cheapest to get right.
