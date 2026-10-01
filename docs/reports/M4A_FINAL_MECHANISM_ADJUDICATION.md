# M4a — Final Mechanism Adjudication

**Date:** 2026-10-01
**Question:** Does the proposed level-controlled term-structure test still constitute the original M4a mechanism — "compression → expansion" — or has controlling for current ATR10 transformed it into a materially different mechanism?

---

## 1. What M4a was intended to test

The Vault defines M4a as: *"Periods of unusually low realised range are followed by expansion, with direction resolved by the break."*

The mechanism is **compression → expansion** in the underlying's realized volatility, with a directional trade resolved by the break direction. The key word is *"unusually"* — compression is inherently a relative concept: ATR10 is low **relative to its own history**. The Vault's squeeze subset (BB/Keltner) operationalizes this as a band-width contraction, which is also relative to its own history.

The intended test: does a compression state predict a subsequent expansion, and does the break direction resolve the sign?

## 2. What the original experiment actually tested

DeepSeek's review found the original construct was **~76% collinear with current ATR10 level**. This means the original was predominantly a **vol-level mean-reversion** test: "when ATR10 is low in absolute terms, does forward range rise?" That is a different hypothesis from "when ATR10 is compressed relative to its own history, does it expand?"

The confound: ATR10 level and ATR10/ATR60 ratio are correlated. A low ATR10 can mean either (a) the market is in a low-vol regime (level effect) or (b) vol has recently contracted from a higher regime (compression effect). The original construct could not separate these.

## 3. What information remains in ATR10/ATR60 after controlling for ATR10

After partialling out ATR10 level via `f(log ATR10)`, the residual variation in `x = log(ATR10/ATR60)` is the **term structure of volatility**:

- **x < 0**: short-term vol is below long-term vol — the vol curve is in backwardation, i.e., recent vol has contracted relative to its own baseline. This *is* compression.
- **x > 0**: short-term vol is above long-term vol — recent vol has expanded relative to baseline.

The ratio is a direct measure of "unusually low realised range" — the Vault's own words. It is not a proxy; it is the mechanism's native variable.

## 4. Whether the proposed β test is still legitimately an M4a test

**Yes.** The proposed specification:

```
y = log(forward range / ATR10_t)
x = log(ATR10_t / ATR60_t)
y ~ date FE + flexible f(log ATR10) + βx
```

tests whether the compression state (x) predicts forward expansion (y), after removing the level confound. The β coefficient is a direct test of: *"does compression predict expansion, holding the level of volatility constant?"*

This is not a different mechanism. It is the same mechanism with the confound removed. The original construct failed **not because the mechanism is invalid** but because it was **unidentified** — 76% of its variation was level, not compression.

The fitted persistence null is also appropriate: it establishes that the ratio has predictive power beyond what a simple AR(1) on vol would give.

## 5. Whether it deserves another research slot and a fresh research surface

**Yes to both.**

- **Research slot:** M4a is status **C** (adjacent research exists; the mechanism itself was never tested). The original construct was confounded; the reformulation is the first clean test of the mechanism. Spending a slot on a properly identified test of an untested mechanism is exactly what the research queue is for.

- **Fresh surface:** Yes. The original construct's data surface is contaminated by the level confound. The reformulation requires a new specification, new pre-registration, and a fresh holdout. It should not inherit the original's surface.

## 6. Whether to close M4a as C5 construct-scoped/open-but-unresolved

**No.** Closing M4a would be appropriate if:
- The mechanism had been tested and failed (it hasn't — the original was confounded)
- The reformulation tested a different mechanism (it doesn't — same mechanism, better identification)
- The reformulation were out of scope for M4a (it isn't — it's the mechanism's native variable)

The original construct's failure is an **identification failure**, not a **mechanism failure**. Closing M4a would conflate the two.

---

## Final decision

### **A = Same M4a mechanism; proceed to protocol design.**

**Reasoning:**

The proposed test is the same mechanism — compression → expansion — with the level confound removed. The ATR10/ATR60 ratio is not a new signal; it is the correct operationalization of "unusually low realised range" (the Vault's own definition). The control for ATR10 level does not change the hypothesis; it isolates the hypothesis from a confound that prevented clean identification.

The three-way distinction:

| Option | Definition | Applies? |
|---|---|---|
| **A** | Same mechanism, better identification | **Yes** — the ratio is the mechanism's native variable; the level control removes the confound |
| **B** | Narrower reformulation of the same mechanism | No — the reformulation is not narrower; it is the same breadth with cleaner identification |
| **C** | Materially different mechanism | No — the hypothesis (compression → expansion) is unchanged; only the operationalization is corrected |

The original construct was not a test of M4a. The proposed construct is the first actual test of M4a. Proceed to protocol design.

---

**Caveats carried:**
- This adjudication is based on the Vault definition and DeepSeek's characterization. No data was read, no experiment run, no holdout consumed.
- The reformulation must be pre-registered as a new construct with a fresh holdout. It does not inherit the original's surface.
- The 76% collinearity finding is accepted as stated; it has not been independently verified in this pass.
