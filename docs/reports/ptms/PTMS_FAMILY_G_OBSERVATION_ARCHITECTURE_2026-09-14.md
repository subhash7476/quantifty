# PTMS Family G — is "one observation per weekly expiry" fundamental?

**Date:** 2026-09-14 · **Type:** research-design analysis (no data, no design selected)
**Scope honoured:** no option outcome read, no P&L, no RFA, `PTMS-G-PTSQ` unmodified and unfrozen,
no declaration, no new hypothesis selected. No parameters, thresholds, strikes or horizons are
proposed. No power is computed for the architectures below, because their n does not exist until
someone designs one.

> **Answer.** One-P&L-per-weekly-expiry is **a choice made for PTMS-G-PTSQ, not a property of
> Family G.** What *is* fundamental to Family G on its certified surface is narrower and harder:
> **one underlying, EOD grain, fixed calendar fences.** Because of that, no observation
> architecture escapes the power wall **while the outcome is exposure to the NIFTY path**. Denser
> sampling raises n and lowers the Sharpe of each observation, and the two cancel. Only a
> hypothesis whose *claim* is relative pricing across units at one formation changes the
> arithmetic, and that is a different research question, not a better sampling of this one.

---

## 1. What makes a Family G observation independent

On the certified surface every contract is a claim on **one index path** (NIFTY; there is no
BankNifty in the store). Two observations are independent draws only if they share none of the
following:

| Shared element | Why it breaks independence |
|---|---|
| **An overlapping outcome interval** | Both outcomes load on the same realized index increments |
| **A settlement event** | Same final settlement price, so the same terminal shock |
| **A formation-time shock** on the same outcome horizon | Strikes or expiries formed on one date and resolved over one interval respond to one move |

Three consequences follow.

1. **Strikes of one expiry, or expiries on one date, are not independent observations** when their
   outcomes run over the same interval. They are one draw measured several ways. Counting them
   separately is the error CLAUDE.md records against CB-N50: a rank statistic manufactured over
   objects that share one underlying, to dress up an index-level timing rule.
2. **Non-overlap is necessary, not sufficient.** Volatility clusters, so the *magnitudes* of
   non-overlapping NIFTY moves are serially correlated, and straddle-type outcomes depend on
   magnitude. Non-overlapping observations are *approximately* independent. Serial dependence has
   to be handled (HAC or block methods) and declared, not assumed away.
3. **The binding limit on information is calendar time on one path.** Per the repo's RFA rule,
   `ncp = S·√T` and **cadence cancels**. Cutting a fixed calendar span into more non-overlapping
   intervals multiplies n by `c` and divides each observation's Sharpe by `√c`. For an effect that
   accrues with time on the path, observation density buys no power.

## 2. Is one-observation-per-settling-expiry required by Family G?

**No.** The governing definition is `PTMS_P3_FAMILY_CATALOGUE_2026-09-12.md`, Family G:

| Field | Catalogue text | Mentions expiries? |
|---|---|---|
| Origin rule | "Formation = a declared session's close" | No |
| Label | "Forward return over a declared horizon" | No |
| Multiplicity | "*m* = statistics × lookbacks × horizons" | No |
| Null | "Nested price-only control is mandatory — `price` vs `price + derivatives`" | — |

The family's unit is **a formation session and a declared horizon.** Settling each observation at
expiry came from PTMS-G-PTSQ choosing a held-to-settlement option P&L as its outcome.

**Disclosure — PTMS-G-PTSQ is a narrow and non-standard instance of the catalogued family.** The
catalogue's Family G hypothesis is that **positioning** (OI, OI change, term structure) carries
information **beyond price**, tested against a **mandatory nested price-only control**. PTMS-G-PTSQ
excludes OI from its primary (its §4), uses an option P&L rather than a forward return, and has no
nested control. It exercises Family G's *surface*, not its declared *mechanism*. That is not a
defect in its specification. It is a fact the operator should weigh when deciding what Family G is
for.

**Superseded catalogue fact.** The catalogue row says index options "stall at 2026-07-17" and marks
availability CONDITIONAL. The G0 repair moved the store to **2026-09-11**, and certification fixed
the windows (TRAIN 2021-01-01 → 2022-12-31, HOLDOUT 2026-01-01 → 2026-09-11). Cite the
certification report, not that row.

## 3. Can one calendar period legitimately yield several independent observations?

**Yes, but only in two shapes, and only one of them changes the power arithmetic.**

- **Several non-overlapping intervals in time** (e.g. one per session instead of one per expiry).
  Legitimate. Independence holds approximately, subject to §1.2. **It does not raise the
  noncentrality** of a claim about the index path, because cadence cancels. The exception would be
  an effect that genuinely lives only at a short horizon, and that is a claim about the phenomenon
  which would have to be defended without data. The architecture cannot create it.
- **A cross-section of units at one formation** (strikes, or expiries on the term structure),
  aggregated to **one statistic per formation.** The observation is still the formation, so n is
  still bounded by the calendar. The cross-section improves the **precision of each observation**,
  and that is the route by which `rank_ic` escapes the wall (CB-N50's √n came from cross-sectional
  density). It is legitimate **only if the primary claim is about relative pricing across those
  units** and the outcome is relative, so the common index move is netted out. Used to re-express
  an index-timing claim, it is invalid.

**Several positions in the same interval are never several observations,** whatever strikes or
expiries they use.

## 4. Observation architectures

These are architectures, not designs. Every horizon, lookback, strike set, statistic and threshold
is deliberately left undeclared.

| # | Architecture | One observation is… | The outcome is… |
|---|---|---|---|
| **A0** | Per settling expiry *(PTMS-G-PTSQ's choice, for reference)* | One weekly cycle | A position held to that cycle's settlement |
| **A1** | Per session, time series | One formation session | A forward quantity over a declared horizon, formed within the options surface |
| **A2** | Disjoint partition of each cycle | One of a fixed set of non-overlapping sub-intervals inside each cycle | As A1, over that sub-interval |
| **A3** | Cross-strike relative value | One formation date, with a cross-section of strikes of one expiry reduced to one statistic | Each strike's **relative** outcome over the horizon, common move netted out |
| **A4** | Term-structure relative value | One formation date, with a cross-section of expiries reduced to one statistic | Each expiry's **relative** outcome, common move netted out |
| **A5** | Positioning with nested price control *(the catalogue's own shape)* | Time series as in A1, or cross-sectional as in A3/A4 | Forward return over a declared horizon, `price` vs `price + OI` |

**Unavailable on the certified surface:** multiple underlyings, which are the only genuinely
independent cross-section. BankNifty is absent from the store. Stock options are uncertified and
spent (O-1). Per the P3 instruction, that is a STOP dependency, not an architecture.

**Covariate boundary, for A1 and A5.** "Forward return" must be formed **inside the options store**
(for example a parity-implied forward). A label built from spot, futures or VIX reaches an
uncertified surface, and that is a STOP.

## 5. Per-architecture properties

| # | Independent observation | How overlap is prevented | TRAIN / HOLDOUT separation | New hypothesis? | New multiplicity slot? | Changes the power arithmetic? |
|---|---|---|---|---|---|---|
| **A0** | One cycle | Formation after the previous FTD; FTD spacing ≥ 3 sessions | Cycle assigned by FTD; its anchor must lie inside the window | — (PTMS-G-PTSQ) | — | Reference: `ncp = 0.82·S` on HOLDOUT |
| **A1** | One session interval | **Horizon ≤ formation spacing**, declared before any read; one position per interval | Assigned by interval end; intervals crossing a fence are dropped | **Yes** | **Yes**; each horizon is a slot (catalogue: × horizons) | **No** for a path-exposure claim (cadence cancels) |
| **A2** | One sub-interval | Fixed partition, sub-intervals disjoint by construction | As A1 | **Yes.** Applied to PTMS-G-PTSQ's construct `R`, it is a *re-sampling of the same claim*: allowed only as a separately registered slot **before** PTMS-G-PTSQ's RFA, and **barred after an ABANDON** (PTMS-G-PTSQ §13.7) | **Yes** | **No**, as A1 |
| **A3** | One formation date (not one strike) | Formation spacing ≥ horizon; strikes share the date's observation and are never counted separately | By formation and outcome end date | **Yes**, and only legitimate if the claim is genuinely relative across strikes | **Yes**; statistic × horizon | **Possibly**, via per-formation precision. Requires an **independently defended IC SD band**, and the repo has no precedent for option cross-strike dispersion |
| **A4** | One formation date (not one expiry) | As A3 | As A3 | **Yes**, same legitimacy test | **Yes** | **Weakly.** Few expiries are liquid at once, so the cross-section is thin |
| **A5** | Per A1 or per A3/A4 | Per its shape | Per its shape | **Yes** | **Yes**; statistics × lookbacks × horizons, **plus** the nested control structure | Per its shape: no if time series, possibly if cross-sectional |

**TRAIN/HOLDOUT separation is unchanged by any architecture.** The windows are calendar fences, not
observation counts. Every architecture assigns an observation by the date its outcome resolves and
drops observations that cross a fence.

**Choosing an architecture from data-free arithmetic is not data-mining,** because no outcome is
read. It carries one standing hazard: picking a cross-sectional statistic *because* it clears the
gate. CLAUDE.md's rule decides that case. The primary claim must be cross-sectional in substance, or
the architecture is invalid.

## 6. Can extending the calendar with spent periods create confirmatory evidence?

**No — unconditionally, for every architecture.** Register **GR-1.3** (appended 2026-09-14): a
window read at spending level before a hypothesis's specification froze may not contribute to
`n_available`, may not be pooled into a confirmatory read, and may not sit on any gate's pass path.
**The order of freezing does not change this.** Observation architecture is irrelevant to it: a
denser architecture over a spent window is still a read of a spent window.

What *can* supply confirmatory evidence, stated as governance facts and not proposed:

| Source | Status under GR-1 | Note |
|---|---|---|
| Past windows **never read at spending level** before the freeze | Can be confirmatory | Index options: 2016-02-11 → 2016-06-30 (monthly-only era, 100-point grid); 2021-01-01 → 2022-12-31 and 2026-01-01 → 2026-09-11, *provided* no gate reads one before the other is declared |
| **Future sessions** after a specification freezes | Can be confirmatory | The only lever that grows. **Closed for PTMS-G-PTSQ**, whose HOLDOUT endpoint is frozen at 2026-09-11. A genuinely new hypothesis frozen later could fence a later window |
| Windows read at `estimation` level | Operator adjudicates per successor | Register §1 |
| Spent windows (2016-07 → 2020 Skew; 2023–2025 MSRP) | **Never** | GR-1.3 |

One fact bears on the operator's decision, and it is **not** a proposal to change PTMS-G-PTSQ.
PTMS-G-PTSQ fits nothing, so its TRAIN is a gate rather than an estimation surface. Declaring
2021–2022 and 2026 **jointly confirmatory**, before either is read, would be consistent with GR-1.
Data-free arithmetic at that n = 138 gives power **0.49** at S = 1.00, which is still below 0.80.
It would be a specification change and is not made here.

## 7. For the operator

1. **Architecture is not fundamental to Family G; the single-path calendar limit is.** A0, A1 and A2
   are the same research object sampled differently and share one wall.
2. **The real fork is the claim, not the sampling:**
   - (a) **Index-path claims** on this surface. They are bounded by `S·√T` whatever the
     architecture, and the only lever that grows is future calendar time.
   - (b) **Relative-pricing claims** across strikes or expiries (A3/A4), or the catalogue's own
     **positioning-beyond-price** claim (A5). These are different questions, each a new hypothesis
     with its own multiplicity slot. A3/A4 additionally need an IC dispersion band defended without
     data.
3. **PTMS-G-PTSQ does not test the catalogued Family G mechanism.** Whether it should remain Family
   G's candidate, and whether a Family G hypothesis must exercise positioning, are your decisions.

*STOP. No hypothesis selected, no RFA, no declaration.*
