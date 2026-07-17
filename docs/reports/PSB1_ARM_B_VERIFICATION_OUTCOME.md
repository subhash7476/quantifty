# PSB-1 §11.1 — Arm B Verification Outcome

**Inputs:** operator's completed `PSB1_ARM_B_EXTERNAL_VERIFICATION.md` worksheet, returned 2026-07-17.
**Predecessors:** `PSB1_ARM_B_RECONCILIATION_DOSSIER.md` (store facts), `PSB1_ARM_B_EXTERNAL_VERIFICATION.md` (the lookup task).
**Status:** analysis only — **no code changed, nothing dispositioned, no factor registered.**

---

## 1. The headline: the substrate is wrong, and this is worse than the dossier assumed

The dossier's framing was **"all four are real price moves measured across a hole"** — i.e. a bookkeeping problem. **The verification refutes that for three of the four.**

> **Three of the four boundaries had a real capital reduction that our store never recorded. Those are missing corporate actions — a genuine substrate defect of exactly the class PSB-1 exists to catch — not gaps to be excused.**

| Case | ISIN verdict | Capital event | Class |
|---|---|---|---|
| INDOSOLAR → WAAREEINDO | `INE866K01015` → **`INE866K01023`** | reduction (Waaree resolution plan) | **missing factor** |
| SPENTEX → CLCIND | `INE376C01020` → **`INE376C01038`** | reduction, 1-for-100 | **missing factor** |
| NTL → NEUEON | `INE333I01036` → **`INE333I01044`** | reduction, FV ₹10 → ₹1 | **missing factor** |
| WEIZFOREX → EBIXFOREX | `INE726L01019` → **identical** | none | **plain rename — RESOLVED (§4), disposition, no factor** |

**The ISIN test earned its keep.** Three serial bumps on unchanged issuer codes — precisely the PHILIPCARB pattern (`INE602A01015` → `INE602A01031`). Same company, security re-issued. Had we dispositioned these four as "renames across a suspension," we would have **filed three missing corporate actions as bookkeeping and moved on.** That is the outcome the ISIN check prevented, and it is the second time in this program that the issuer-prefix rule has caught something a plausible story would have buried.

**And "entity continuous" is right in all three.** Equity survived — diluted to 1% at SPENTEX, but it survived. So the fix is a factor, not an entity termination. Decision 1 resolves in favour of the links.

---

## 2. Registering the factors will NOT clear Arm B — derived, not assumed

My worksheet's §E said a splice "may resolve on its own" once the factor is registered. **That was wrong, and I should not have written it without deriving it.** Back-adjusting the historical closes by the reduction ratio and recomputing each boundary:

| Case | Raw return | Factor | Adjusted old close | **Adjusted return** | Arm B (`abs(r) ≥ 20%`) |
|---|---:|---:|---:|---:|---|
| INDOSOLAR → WAAREEINDO | +16,406.7% | *unknown* | — | — | needs a factor in **[138, 206]** to clear |
| SPENTEX → CLCIND | +1,094.7% | 100 | ₹75.00 | **−88.1%** | **still HALTS** |
| NTL → NEUEON | +110.2% | 10 | ₹27.40 | **−79.0%** | **still HALTS** |
| WEIZFOREX → EBIXFOREX | +31.4% | 1 | ₹391.90 | **+31.4%** | **still HALTS** |

**The factor flips the sign and keeps the magnitude.** And that is not a failure of the repair — **−88% and −79% are economically correct.** Shareholders in an insolvency capital reduction really did lose that much across the suspension. The adjusted series will be *right* and Arm B will *still* halt, because a correct multi-year unearnable move is still a >20% single-session print.

**So the two actions are cumulative, not alternative:**

1. **Register the missing factors** — required for substrate correctness, independent of Arm B. The adjusted series is wrong today.
2. **Then disposition the residual** — required to clear certification, because step 1 does not.

The dossier's Decision 2 stands unchanged and is now the *second* step rather than the only one.

---

## 3. What blocks the repair: the ratios

**The worksheet asked what kind of event happened. It did not ask for the ratio — my design gap.** The ratio is the number `ingest_corporate_actions.py` needs, and it is missing or unusable in all three:

- **INDOSOLAR — no ratio at all.** "Capital reduction & fractional share processing under Waaree resolution plan" names the event and omits the number. Nothing can be registered from this. *(For calibration only: clearing Arm B would need a factor in [138, 206] — do not treat that as a target. The factor is whatever the NCLT order says, and the residual is whatever it is.)*
- **SPENTEX — internally contradictory.** "public shareholding reduced/consolidated by **95%** (1 share for every **100** held)". 1-for-100 is a **99%** reduction, not 95%. Both numbers cannot be right; the table above assumed 100 and that assumption is unconfirmed.
- **NTL — the stated event does not imply a price factor.** "Face value reduced from ₹10 to ₹1" and "reducing the outstanding base by 90%" are **different events**. A face-value reduction with the share count unchanged is an accounting write-off: the holder keeps the same number of shares and **no price adjustment applies** (factor = 1). A 1-for-10 *consolidation* cancels 9 of every 10 shares and **does** carry a factor of 10. The report asserts both. If it is FV-only, NTL's true adjusted return stays **+110.2%**, not −79.0%.

**A wrong factor is worse than no factor.** It fabricates an adjusted series that looks authoritative — the DVL→DTIL lesson in a new costume. None of these three can be registered until the NCLT order's own words give the entitlement ratio.

**Also unconfirmed, and cheap:** the reduction **effective dates**. INDOSOLAR's order is dated 2022-04-21 but relisting was 2025-06-19 — a three-year lag. A factor must be registered at the date it took effect, not the order date, or it back-adjusts the wrong span.

---

## 4. WEIZFOREX — **RESOLVED.** Plain rename across a real suspension

> **Update (2026-07-17, second lookup).** The exchange has **no prints for WEIZFOREX in early March 2020**; the stock was **suspended 2020-02-26 → 2020-04-21**. This resolves the case and **retracts the objection below.**

**The ingestion worry is closed, and that was the item with reach.** The open question was whether NSE held prints our store lacked — which would have made this an *ingestion* defect, and ingestion defects do not stay confined to one symbol. They do not exist. **Our store's gap matches the exchange's gap. Ingestion is correct here.**

**My "the dates don't align" objection was wrong, and the new fact explains why.** I argued that a "name change processing window" should bracket the 2020-03-20 rename, and ours brackets neither side — last WEIZFOREX print 17 sessions before it, first EBIXFOREX print a month after. **But if the suspension spans 2020-02-26 → 2020-04-21, the rename fell *inside* it.** A last print weeks before and a first print weeks after is then not an anomaly — it is the exact signature of a symbol changing while the stock is halted. The dates I called inconsistent are consistent; I had the causality backwards.

**Disposition class: plain rename across suspension. No factor needed.** The load-bearing fact is the **identical ISIN** (`INE726L01019` on both sides), which rules out a re-issue — the split / consolidation / face-value class that bumped the serial in all three other cases, and that bumped this very symbol's own serial later (`→ INE726L01027`, 2021). Strictly, ISIN identity does not by itself rule out a **bonus or rights issue** (those keep the ISIN). But both are dilutive and would push the boundary return *down*; neither explains a **+31.4% rise**. Their absence is consistent with the record.

**Still not credible, and it does not matter:** *"a formal name change processing window"* as the **cause** of a 2-month halt. Name changes do not suspend stocks — NSE rolls the symbol with the stock trading. The suspension was near-certainly for the underlying restructuring, and the rename merely happened during it. **This is a defect in the explanation, not in the substrate**, and it cannot change the disposition class: ISIN identity and "no capital event" already settle the only question the repair consumes.

**The +31.4% stands as a real, unearnable move.** The gap spans the COVID crash — the market fell roughly a third while NSE never closed — and this stock reopened 31.4% higher, on Trade-for-Trade, thin. That is what reopening after a halt looks like: the print is wherever it opens, not a return anyone could have earned. **Exactly what Arm B is built to catch, and exactly why it must be recorded rather than silenced.**

**Residual result risk: nil.** WEIZFOREX has never been in NIFTY-200 — zero membership rows. Dev-window placement made it the case worth scrutinising; no candidate can score it either way.

**Confirmed and useful, though:** the contemporaneous name was **EBIXCASH WORLD MONEY INDIA LIMITED** (NSE `NSE/CML/43889`, 2020-03-20). Our `symbol_changes` carries "DELPHI WORLD MONEY LIMITED" on that 2020 row — a name not adopted until **2021-08-09**. **Our rename table is retroactively backfilled with current names**, which is a real finding about the store's provenance and is not confined to this symbol.

**Latent, not this gate:** the ISIN shifted `INE726L01019` → `INE726L01027` under the 2021 Delphi restructuring. That is the **EBIXFOREX → DELPHIFX handoff (2021-09-01)**, which Arm B did *not* flag — so its return is under 20%. **A capital event with an ISIN re-issue at a boundary that Arm B passes** is a missing factor hiding beneath the threshold. Arm B is a >20% tripwire, not a completeness check; it was never meant to find this. Log it, don't chase it here.

---

## 5. Confidence in the verification itself

The findings are plausible, mostly coherent, and the ISIN results are the kind of thing that is easy to check and hard to fake usefully. **But three of the four contain the specific defect that unverified generated detail produces:** a contradictory ratio (SPENTEX 95% vs 1-for-100), two mutually exclusive events asserted together (NTL FV-reduction vs consolidation), and a named event with the operative number absent (INDOSOLAR). Circular numbers and bench dates are cited crisply throughout, which raises confidence in the *shape* of the answer and not at all in the *arithmetic*.

**The shape is almost certainly right: three real capital reductions, one rename.** That conclusion is safe to act on. **The ratios are not**, and they are the only part the repair consumes.

---

## 6. Recommended next step

**Go back to the primary orders for three numbers, then stop.** Per case (1–3): the **entitlement ratio in the NCLT order's own words**, the **effective date** of the reduction, and for NTL specifically **whether the share count changed at all** or only the face value.

Sources that carry the operative wording: the NCLT order PDF, the NSE relisting/recommencement circular (which states the revised capital structure), and the company's post-relisting shareholding pattern — pre- and post- share counts settle NTL definitively without needing anyone's interpretation.

**Do not register any factor from the current worksheet.** Two of its three ratios contradict themselves and the third is absent.

**Not blocking Phase 2 numerically:** none of these nine tickers has ever been in NIFTY-200 — zero membership rows. No candidate can score them. §11.1 gates on the *record*, not the result.

**Reviewer's note.** §E's "the splice may resolve on its own" is the fourth number this session I asserted without deriving — after the C4 33σ error, the turnover ≈ 1/6 pin, and the gap-rule recommendation. The pattern is identical every time: a plausible mechanism stated as a conclusion. The arithmetic in §2 took one command.
