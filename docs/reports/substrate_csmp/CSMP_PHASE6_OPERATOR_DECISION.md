# CSMP Phase 6 — Operator Decision: Increment 1 CLOSED

**Date:** 2026-07-12
**Decision party:** Operator
**Author of record:** Claude (Lead Reviewer — records the decision; does not make it)
**Governing rule:** Frozen dossier §10, row 3 (`CSMP_PHASE1_RESEARCH_DOSSIER.md`), and the charter §6 amendment (`CSMP_PHASE0_CHARTER.md`, 2026-07-12).

---

## The result being decided on

The sealed held-out window (2023-01-01 → 2026-06-30) was read **once**, on 2026-07-12, and is now **spent**. The verdict was rendered mechanically by code from a decision table written before the data was seen (`CSMP_PHASE6_SEALED_READ.md`, `validation_id` `872a0c05…`, `code_commit` `0ae1dc4`, HEAD `6e1a76f`):

> **Inconclusive (Not Approved)** — gate LB = **−0.0147** (one-sided 95% Student-t on mean_IC 0.0279, SD 0.1638, n 42). **Not > 0.**

`Δ_net` = **+6.19%** (deployment qualifier met) — **moot**, because the gate did not clear. The artifact `csmp-xs-momentum-v1` v1.0.0 is **Not Approved**.

## The decision

**CSMP increment 1 is CLOSED. The exploratory top-40 PaperBroker consumer is NOT built.**

The operator declined the §10-row-3 / §6-amendment option to build the consumer as an explicitly exploratory deployment, and closed the increment on the Not-Approved verdict instead.

## What this decision is, and is not

**It is not a rejection of the hypothesis.** `mean_IC ≤ 0` would have been falsification (§10 row 4). That is not what happened. The point estimate is positive and close to dev (sealed +6.19% net spread vs dev +5.95%). The hypothesis is **untested at adequate power**, not refuted.

**It is a refusal to promote a Not-Approved artifact on an encouraging point estimate.** The pre-registration fixed the expectation in advance: a valid, one-sided, correctly-covered test on 42 months is **~41% powered** against the program's own point estimate, so **"Inconclusive" was the single likeliest outcome (~59%) even if momentum works exactly as well out-of-sample as in-sample.** It arrived. The +6.19% is precisely the encouraging-looking number the charter §6 amendment's four controls were written to resist — an artifact that failed its gate, wearing a positive result. Building on it was permitted; it was not indicated.

This is the same shape as the MSRP D1 STOP: the methodology working, not the methodology failing.

## What is now binding

1. **The sealed window (2023-01 → 2026-06) is spent and is never re-read.** Re-reading nested data is the D-iii multiplicity trap (naive-schedule FWER 0.130 — the exact level of the coverage bug that D-i removed pre-seal).
2. **No tuning, no retrofit.** The frozen construct fence stands: universe, score, K=40, metric, baselines, cost model, §5.2, and the inference/extension design cannot be edited. Any change requires a **new pre-registration**, not an amendment.
3. **No consumer.** The top-40 PaperBroker consumer is not built under this increment. Nothing in `core/strategies/` is authored against this artifact.
4. **The artifact is retained, not deleted** — `csmp-xs-momentum-v1` v1.0.0 stays as an immutable Not-Approved record with its sealed validation record intact. It may never appear in Approved / Deployable / certified language, in code, dashboards, or reports.
5. **Any future momentum work starts fresh.** A new pre-registration with frozen rules and **fresh α**, scored on forward data (2026-07 onward) that did not exist when this window was read. Power is bought from new data — never from re-reading the spent one.

## What the program bought

The five defects found and closed **while the window was still sealed** — the only time any of them could be fixed for free:

- a gate whose CI under-covered by ~4× (would have approved a worthless artifact ~1 time in 8 while presenting itself as conservative);
- an extension schedule whose FWER equalled the bug it replaced;
- a selection rule that named no metric and pointed at two different gates;
- a survivorship bug inside the very script that chose the gate;
- a governance escape hatch dressed as a definition (charter §6, closed as a dated amendment with teeth).

And the data substrate itself — gates (a)–(e): a clean 7.03M-row equity store, a corporate-action layer with **0 undocumented residue across the sealed window**, a point-in-time NIFTY-200 universe with no survivor list as input, and an era-accurate delivery-fee model. **None of that is spent.** It is the foundation any future cross-sectional pre-registration starts from.

## Status

**CSMP increment 1: CLOSED (Not Approved).** No open items. No pending prompts. The next action, whenever the operator chooses one, is a **new pre-registration** — not a continuation of this one.
