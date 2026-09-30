# Hostile Audit of the RFA (Research Feasibility Assessment) Framework

**Date:** 2026-09-29 · **Status:** independent audit, read-only (no market-data reads for this audit beyond what cited documents contain; no code run — all power figures below recomputed by hand from the framework's own inputs and cross-checked against its reports).
**Scope:** what RFA mathematically and logically does when a construct is submitted to it. M1c's market merit is not judged; no strategy is designed; the framework's self-descriptions were treated as claims and verified against code and records.
**Materials:** design spec (`2026-07-20-rfa-power-feasibility-gate-design.md`), governance contract (`governance/rfa/declaration.py`), `scripts/rfa/{power,gate,report,run_rfa,retrospective}.py`, all 17 frozen declarations, 9 gate reports (FLOW, RS-MOM, CB-N50, CARRY, A-INDEX-INTRADAY, N50-LS, OSC, STOCK-STRADDLE-M10, O1), O1 review, retrospective, V2 remediation record, and the full M1c chain (RFA v1–v4 plus four reviews).

## 1. RFA's actual decision function

RFA answers exactly one question (design §1): given the formations actually available and an
independently defended effect-size band, can this construct reach power 0.80 even under assumptions
more generous than anyone believes? Formally, with band corners and fixed sample size:

- `rank_ic`: max_power = P(reject H0 | δ=δ_hi, SD=sd_lo, n=n_available); noncentral-t, ncp = δ√n/σ.
- `per_trade_pnl`: max_power = P(reject H0 | S=sharpe_hi, n=c·T); ncp = S√T (cadence cancels).
- Verdict: ABANDON iff max_power < 0.80, else PROCEED. One-sided/two-sided and α follow the declaration (α=0.05 in `power.py`; M1c hand-computed α=0.025 for VAL).

Three structural facts about this function: (i) it evaluates **only the optimistic corner** — central and pessimistic corners never enter the verdict (they feed `n_required` context only); (ii) it is monotone in every input, so the verdict is a pure ceiling test; (iii) it is one-sided as a screen — it can only ever establish "even the best case is underpowered" or "not provably infeasible." It cannot confirm feasibility, edge existence, or viability, by construction.

## 2. Complete input inventory

| Input | Class |
|---|---|
| n_available (formations/sessions actually available) | Observed empirical fact (calendar/store arithmetic; e.g. pre-2016 futures unobtainable fixes n=42) |
| Test form (t-test, NW lag, α, one/two-sided, hurdle 0.80) | Arbitrary/frozen convention (0.80, α levels, optimistic-corner rule are choices, not theorems) |
| ncp = δ√n/σ or S√T, noncentral-t power | Mathematical consequence (verified correct in code; hand-checks match reports to rounding) |
| Band values (δ/SD or Sharpe) | Human judgment with cited provenance — the only input that can smuggle conclusions |
| Provenance narratives (literature, first principles, adjacent repo numbers) | Externally sourced evidence mixed with prior-exposed observations, laundered through prose |
| prior_exposure statements | Observed empirical fact (what was read), used as disclosure only — correctly carries no mathematical weight |
| Grinold translation (IR = IC·√BR), breadth N_eff/b, SD carry-overs ([0.10,0.18] reused across 6+ declarations) | Modelling assumption, usually unstated as such |
| "Independently defended" status, frozen SHA digests | Governance convention (freezing binds the author against revision, not against initial error) |

## 3. Decision dependency graph

The verdict is a step function of exactly five quantities: optimistic effect (δ_hi or sharpe_hi),
optimistic dispersion (sd_lo — rank_ic only), n_available, α/test-sidedness, hurdle 0.80. Provenance
text, central/pessimistic corners, fee analyses, prior-exposure statements, and all diagnostics have
**zero** mechanical effect on the verdict. Consequently: whoever sets the optimistic corner and n
determines the verdict up to arithmetic. The audit's sensitivity results (§8) quantify each lever.

## 4. Mathematical reconstruction (units and scalings checked)

- `power.py`: ncp = δ√n/σ, noncentral-t survival at Student-t critical value. Correct; hand-verified: FLOW ncp=0.03·√42/0.10=1.944 → 0.603 (≈0.6053 reported); N50-LS ncp=1.4·√3.52=2.627 → Φ(2.627−1.96)=0.748 (≈0.7466); RS-MOM 0.65·√3.58=1.230 → 0.339 (≈0.3372); A-INDEX per-trade 1.45/√237=0.0942, ×√873=2.783 → 0.872 (≈0.8720); CB-N50 0.035·√887/0.15=6.95 → 1.000. All match.
- `gate.py` per_trade_pnl: per-formation Sharpe S/√c with n=cT gives ncp=S√T — cadence invariance holds **for iid per-period observations**. For the M1c overlapping-hold test the correct form is S√(T/H) at session scale, reunited with S√T at strategy scale via regrouping (M1c v4 derivation, review-verified). The framework core has no HAC/overlap machinery: any dependence must be handled by hand outside the gate (M1c did; CB-N50's "AC1=0.3 → n≈477" is prose, not code).
- Normal-vs-exact-t gap: hand Φ-approximations overstate power at small n (STOCK-STRADDLE: Φ gives 0.834 vs exact 0.8211 — a 1.3pp gap against a 2.1pp verdict margin; see §10).
- α handling is inconsistent across cases by necessity: `power.py` hardcodes 0.05; M1c VAL (α=0.025) was hand-computed outside the gate. The "same core" claim holds only where α matches.

## 5. Pre-data rejection analysis

Yes — RFA routinely rejects without market data: FLOW (no TRAIN read taken), RS-MOM, N50-LS, OSC (no declaration even frozen), M1c (four versions, zero reads). What makes this possible is fully identified: (a) n fixed by calendar/store arithmetic, (b) test form frozen, (c) the band ceiling asserted by prose, (d) the hurdle fixed at 0.80. Of these, only (c) contains empirical content about the world — and it is the one input never measured. Pre-data rejection is therefore rejection **conditional on the band**, i.e. a check of internal consistency between ambition (band) and budget (n), not a finding about markets.

## 6. Effect-size prior audit (critical)

| Band source | Observed | Population/mechanism | Breadth/horizon/costs | Translation justified? |
|---|---|---|---|---|
| CB-N50 HOLDOUT +0.0294 → ISD-OD/OG bands, N50-LS Sharpe, M1c ceiling, A-INDEX optimistic (via ISD F4) | Daily rank IC, OOS 2020–22, reversal+basis combined | 50 large-cap names, daily cross-section | No cost model; breadth re-chosen per use (N_eff 1→8; b 5→15) | **No — this is the reference-class-ceiling pattern**: one repo OOS number became the ceiling for four later gates across different mechanisms (intraday momentum, gap fade, L/S book, tail reversion) |
| ISD F4 (IC −0.029, cost-killed) → A-INDEX optimistic 1.45 | Intraday composite, net-negative | Index intraday | Killed on costs — yet used gross as ceiling | No: a cost-killed composite anchoring a net Sharpe band |
| C5 +0.068 → IVOL optimistic cap | Monthly low-vol IC, in-sample, power-failed | Cash equity cross-section | Different substrate/fees | Partially: capped below, but in-sample failed construct as ceiling input |
| TS_BASIS TRAIN +0.089 → own optimistic 0.090 | Monthly IC, in-sample, pre-declaration | Same construct | None | **No: in-sample realization as its own ceiling** (filed openly, still circular) |
| Own-history Sharpes → STOCK-STRADDLE [0.65, 1.51] | 43-cycle confirmation + post-reform window | Same construct, spent windows | Costs partly missing (0.15% STT) | No: corners are the historical record itself; central implies power 0.59 while verdict reads 0.82 |
| Literature (MOP/KMPV/JT/Ang/etc.) | Foreign-market published effects | Various, mostly US monthly | No transfer model to NSE India | Weakly: directionally plausible, magnitudes untransported (LAG's "larger frictions → larger IC" is a bet, not a measurement) |
| O1 crossed corner (Sharpe 1.44 implied vs 1.0 ceiling) | Coupled δ-from-SD construction | — | — | Caught and withdrawn; v2 contract bans the mechanism |

The design's firewall ("Historical PSB/SFB results must not define these ranges") is drafted against PSB/SFB by name — and the practice routes around it by citing CB-N50/ISD/C5/TS_BASIS numbers that are prior-exposed in exactly the same sense. Nine of seventeen declarations anchor on in-repo historical figures.

## 7. Breadth audit

Grinold IR = IC·√BR converts any IC into any Sharpe via the breadth dial: M1c's ceiling moves 1.04 (b=5) → 1.80 (b=15) on the same IC, and b* ≈ 28.7 (V4-2: (2.4865/0.0294)²/250) flips its ABANDON outright. N50-LS embeds N_eff 1→8 to reach 1.40; at N_eff=15 the same IC gives 1.78 → power 0.92 → PROCEED. Breadth ("independent bets") is unobservable by construction — in every case surveyed it is **imported** (CB-N50's 50-name universe), **inferred** (12 sectors, corr 0.3–0.6), or **chosen** (5–15/day) — never observed, never capped by rule. **Yes: increasing assumed breadth reverses real ABANDON verdicts.** The O1 fix banned coupled δ/SD corners while Grinold-coupling (observed IC × chosen breadth) reintroduces coupling through the back door: the optimistic corner pairs a measured IC with a selected breadth.

## 8. Sensitivity / fragility (recomputed)

- **N50-LS (real ABANDON, 0.7466):** ceiling 1.40 → 1.60 (+14%) gives Φ(1.6·1.876−1.96) = 0.851 → PROCEED. The cited literature top end (1.5) already gets 0.83. Verdict-critical input: band ceiling, ±15%.
- **FLOW (0.6053):** sd_lo 0.10 → 0.07 (−30%) gives 0.86 → PROCEED; δ_hi 0.030 → 0.038 (+27%) same flip. Verdict-critical: either band edge at ±30%.
- **M1c HOLDOUT:** needs S ≥ 2.49; robust to 2× band error (S=2.0 → 0.64), fragile only to breadth (b* ≈ 29) or window length (frozen). Verdict-critical: breadth cap + frozen n.
- **STOCK-STRADDLE (real PROCEED, 0.8211):** central 1.08 implies 0.59; margin over hurdle is 2.1pp against ~1.3pp of normal-vs-exact-t approximation gap. Verdict-critical: optimistic corner (= best historical sub-window) and distributional exactness.
- **RS-MOM (0.337):** needs S ≈ 1.32 (2× ceiling). Robust ABANDON. **CB-N50 (1.00):** robust PROCEED (even pessimistic corner clears at reduced n).

## 9. False-negative risk

Yes — by at least five concrete mechanisms, three demonstrated on real verdicts: (a) low-balled ceiling (N50-LS flips on +14%); (b) breadth cap set below truth (M1c flips at b*≈29 daily bets on a 2,300-name panel — not obviously out of reach); (c) SD overestimate (FLOW flips on −30%); (d) frozen-n shortfall conflated with no-edge (M1c: "cannot be validated in 250 sessions" recorded as construct ABANDON; 478 sessions at S=1.8 would pass); (e) metric mismatch — rank_ic linear-IC power for edges that live in tails/skew (straddle skew −1.19 acknowledged in its own file; t-test underpowered vs the true payoff); (f) the verdict reads the least-plausible corner, so any construct whose truth sits at central-but-not-ceiling with n slightly short is abandoned despite realistic feasibility.

## 10. False-positive risk

Yes: (a) the verdict fires on the optimistic corner alone — STOCK-STRADDLE passes 0.8211 while its central corner implies 0.59, with corners taken straight from the best historical sub-window; (b) circular priors — TS_BASIS's ceiling is its own TRAIN realization; the CB-N50→ISD→N50-LS→M1c chain re-uses one OOS number four times, so a single lucky +0.029 propagates into four PROCEED-capable ceilings; (c) O1's crossed corner printed PROCEED 0.99 on Sharpe 1.44 vs a 1.0 ceiling (caught post-hoc — the machinery emitted it); (d) unread-n risk — A-INDEX counts ~20 projected sessions/month that may not materialize; (e) ground truth from history: CB-N50 PROCEEDed then CLOSED without a P&L gate (breadth→futures fail) having spent TRAIN+HOLDOUT — PROCEED protected nothing; CARRY PROCEEDed into SEALED PASS yet carries B-status defects (dividend sign, uncertifiable PIT) the gate cannot see.

## 11. What RFA does NOT establish

Design says it outright (§1/§6: no fees, MaxDD, turnover, economic significance) and practice confirms the gaps: (i) feasibility of proving an effect — only at the declared band, which is assumed; (ii) probability the effect exists — no Bayesian update occurs anywhere; RFA never outputs or updates a belief; (iii) economic existence of an edge — a passed construct can be fee-doomed (PSB-1 C1–C4 pattern; M1c H∈{1,5} fee analysis) and a failed one can be real but small; (iv) empirical evidence for the mechanism — no data is read, and where "evidence" appears (Grinold inputs, ceilings) it is imported, often from the repo's own prior reads.

## 12. Governance assessment (derived, not preferred)

The mathematics implements exactly one operation: a ceiling-conditional infeasibility screen (C — an experiment-design feasibility report). The optimistic-corner construction adds a weak abandonment disposition: *if even the best case is underpowered, building cannot pay for its own proof.* That supports (A) **only** for the literal proposition "undemonstrable at declared bands." But bands are human judgments with documented circularity (§6–§7), breadth freedom (§7), and ±15–30% verdict-criticality (§8) — so hard-(A) status converts judgment error into research death with no appeal except re-declaration. As practiced the framework is already (B): M1c/CB-N50 outcomes steer queue order while staged reads (TRAIN/HOLDOUT/sealed) do the actual killing or confirming. Verdict: **C by mathematics, B in practice, A only conditionally** — hard abandonment is legitimate solely when the band is a genuine ceiling argued adversarially against the construct (not assembled from its cousins' best numbers), and the record shows that condition routinely fails.

## 13. The M1c case (worked example, after independent reconstruction)

- **Does ABANDON follow mathematically?** Yes, given premises: best optimistic power anywhere is VAL 0.61 / HOLDOUT 0.26 (H-collapsed per v4); HOLDOUT needs S ≥ 2.49; fee floors independently doom H∈{1,5}. The arithmetic is verified cell-by-cell.
- **Does it depend on contestable assumptions?** Yes — decisively on the breadth cap (b ≤ 15 imported from a 50-name universe onto a 2,300-name panel; b* ≈ 29 flips HOLDOUT) and secondarily on W (rescue needs Σρ ≤ −0.42, implausible but unmeasured) and the 1.8 ceiling.
- **Were those empirically established?** No. Breadth was chosen, not measured; the ceiling is a stacked-favorable translation; W is a standard premise, not a finding.
- **Is "M1c is not worth researching" equivalent to what was demonstrated?** No. Demonstrated: (i) a 250-session HOLDOUT cannot resolve any Sharpe below 2.49; (ii) VAL resolves ≥1.26 but is prior-exposed; (iii) only H=10 is fee-arguable. "No meaningful edge" is a strictly stronger proposition requiring evidence RFA never touches. The correct reading is the narrow one: *unvalidatable in the frozen window at any defensible Sharpe.*

---

# Closing five

1. **What RFA actually does:** computes optimistic-corner noncentral-t power for a frozen test/size/band triple and kills constructs whose best case clears 0.80 nowhere. It is a consistency check between ambition and budget, with all world-content concentrated in the band ceiling.
2. **What RFA is mathematically sound at:** the power core (verified to rounding on five cases), cadence algebra where its iid premises hold, monotone-ceiling logic, and cheap true negatives with headroom (FLOW 0.61, RS-MOM 0.34 — robust ABANDONs that saved real work, the documented $0 kills).
3. **Where RFA relies on assumptions rather than evidence:** band ceilings (9/17 anchored on in-repo prior reads despite the firewall's intent), breadth/N_eff (always chosen, verdict-flipping at b*≈29 / N_eff 15), SD floors, Grinold translations, W/iid premises, unread-n counts, and normal approximations at small n.
4. **Where RFA can prematurely kill research:** any construct whose truth exceeds its ceiling (N50-LS at +14%), whose breadth exceeds its cap (M1c at b*≈29), whose SD is overestimated (FLOW at −30%), or whose window is frozen short (M1c: 478 sessions would pass at S=1.8) — with the kill recorded as a property of the construct rather than of the ceiling, window, or cap.
5. **Whether RFA should remain a hard ABANDON gate:** No — not as currently operated. Its mathematics earns it the feasibility-report role (C) with a conditional hard edge: ABANDON is dispositive only for the proposition "undemonstrable at these bands in this window," which is worth enforcing solely when the band is an adversarially argued ceiling. The record shows ceilings routinely assembled from adjacent best numbers plus chosen breadth, which makes hard-(A) status a machine for converting judgment calls into research death. Keep it as (B)/(C): run every gate, publish every table, but let ABANDON mean "not now, not this window" — appealable by re-declaration with better-anchored bands — rather than terminal.
