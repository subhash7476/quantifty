# DayType — The 13:00 Regime Fact Is a Directional Prior, Not a Same-Horizon Forecast

**Date:** 2026-09-09
**Resolves:** Finding A (HIGH) of `REGIME_DETECTION_SPEC_AUDIT_2026-09-09.md`
**Resolution:** option (b) — disclose the semantics. The label is **not** re-derived and the model is **not** retrained.

---

## 1. The mismatch, stated exactly

Three different horizons are involved, and conflating any two of them produces a claim the evidence does not support.

| | Window | What it is |
|---|---|---|
| **The label** | 09:15 → 15:29 (full session) | KMeans cluster over whole-session features (`cluster_day_types.py`). "BullTrend" describes the shape of an entire day. |
| **The prediction** | features 09:15 → 13:00 | The classifier nowcasts that full-session label from partial-session features at the 13:00 checkpoint. |
| **The trade** | 13:00 → 15:15 | NiftyShield opens a structure at 13:00 and exits in the afternoon. |

So the model is trained on one horizon and consumed on another, and the traded horizon is the **quiet tail** of the session: median absolute 13:00→15:15 move **10.6 points (0.044% of index)**, median range **47.9 points** (`NIFTY_SHIELD_REGIME_AND_STRUCTURE_AUDIT.md` §2.2).

## 2. What the evidence supports

`scripts/nifty_shield/diagnose_regime_horizon.py`, over **1,606 out-of-sample sessions**:

> BullTrend minus BearTrend, mean forward-window return: **+0.255 pp**, bootstrap 95% CI **[+0.197, +0.312]** — excluding zero.

**That is the whole of the supported claim.** The 13:00 call separates direction over the remainder of the session, by roughly a quarter of a percentage point between opposite calls, with an interval that excludes zero at n = 1,606.

It is a **directional prior**: weak in magnitude, statistically real, measured out of sample.

## 3. What the evidence does not support, and must not be cited as

- **The trainer's documented 75–85% accuracy for the 13:00 checkpoint is not accuracy about the traded window.** It is accuracy against the *full-session* KMeans label. A model can be 80% right about what shape the whole day had and carry far less information about 13:00→15:15 specifically.
- **The 12-session live agreement rate (7/12, or 6/11 on complete sessions) is not comparable to that figure either.** It was measured against a 14-D z-scored nearest-centroid *proxy* for the label, not the true PCA-space KMeans label, and the disagreement cannot be split into model error and proxy error. Both numbers exist; they are not commensurable.
- **No threshold, sizing rule or confidence gate may be derived as if the label described the traded window.** `regime_confidence` is the classifier's confidence in the *full-session* class, not a probability about the afternoon.

## 4. What this means for the live system

NiftyShield's use of the fact is **legitimate under this reading and only under this reading**: the regime label is a prior over afternoon direction that tilts structure selection (`structures.select_structure`) and sizing (`regime_sizing`), while the actual risk is carried by the structure, the strikes, and the exits.

The effect size is small enough that the prior should never be the load-bearing element of a trade. At a +0.255 pp separation between opposite calls, against a median afternoon move of 10.6 points, the regime call is a tilt — not an edge that justifies size on its own.

## 5. Why option (b) rather than re-labelling

Option (a) — re-label on the 13:00→15:15 horizon and retrain — is a **new construct**, not a repair. It would need its own pre-registration, its own train/holdout structure, and it would have to clear the demonstrability arithmetic before any code is written. It may still be worth doing; it is simply not a documentation fix and must not be smuggled in as one.

Option (b) costs nothing, is honest about what the live system actually claims, and leaves (a) available as a separate decision. Nothing here forecloses it.

## 6. Where this disclosure lives

So a reader cannot encounter the fact without encountering its semantics:

| Location | What it says |
|---|---|
| This report | The full reasoning |
| `models/daytype/*/metadata.json` → `horizon_disclosure` | Machine-readable, travels with the model |
| `scripts/daytype/train_daytype_classifier.py` | Written into every future model's metadata |
| `strategies/nifty_shield_v1/source.py`, `facts.py` | At the two points of consumption |

## 7. What would change this

A re-labelled construct on the traded horizon (option (a)), or a direct measurement of the 13:00 call's information content **about 13:00→15:15 specifically** that materially exceeds the +0.255 pp separation. Until one of those exists, the prior stated in §2 is the ceiling of what may be claimed.
