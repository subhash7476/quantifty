# RFA Retrospective — Non-Binding Context Appendix

**These numbers are prior-exposed observations. They carry no weight in any binding
RFA declaration** (design spec §2.2). They exist to test one claim in CLAUDE.md, not
to calibrate the gate.

**Claim under test:** the power-feasibility pre-check "would have saved the back half
of C5, C4, C2, and F1."

| Case | delta | SD | n | Max power | Verdict | Source |
|---|--:|--:|--:|--:|---|---|
| C5 | 0.067639 | 0.246232 | 42 | 0.5422 | ABANDON | `PSB1_C5_REPORT.md` |
| C4 | 0.046550 | 0.208949 | 42 | 0.4110 | ABANDON | `PSB2_C4_REPORT.md` |
| C2_PSB2 | 0.034892 | 0.104033 | 84 | 0.9198 | PROCEED | `PSB2_C2_REPORT.md` |
| C2_PHASE0_5 | 0.022552 | 0.100137 | 84 | 0.6563 | ABANDON | `C2_PHASE0_5_MINIBATTERY.md` |
| F1_TRAIN | 0.015400 | 0.076695* | 83 | 0.5672 | ABANDON | `F1_FEASIBILITY_SCREEN_REPORT.md` |

\* SD recovered from block-bootstrap CI width via a normal-symmetric back-out
(`SE = (CI_high - CI_low) / 3.92`, `SD = SE x sqrt(n)`). The bootstrap CI is
asymmetric and percentile-based, so this is an approximation adequate for a
feasibility bound — it is not F1's actual dispersion.

## Finding

The CLAUDE.md claim is **partly wrong, and the exception is informative.**

The gate fires on C5, C4, and F1. It does **not** fire on C2 as PSB-2 recorded it:
at delta=0.034892, SD=0.104033, n*=84 the projected power is 0.9198, comfortably
clear of the hurdle. A pre-check run before PSB-2 would have returned PROCEED.

C2 fails only once the extended-history re-estimate widens its dispersion. That is
exactly the caveat PSB-2 recorded against itself: the recommendation rested on a
55-observation, 2.3-year SD estimate, and power is a function of SD.

**This does not weaken the gate; it locates its dependency.** The verdict is only as
good as the declared SD, which is precisely why the design requires SD to be
independently defended and frozen rather than inherited from a short in-sample read
(design spec §2.1, §2.3).
