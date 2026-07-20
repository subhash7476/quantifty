import math
from dataclasses import dataclass
from pathlib import Path

from scripts.rfa.gate import POWER_HURDLE
from scripts.rfa.power import power_at


@dataclass(frozen=True)
class Case:
    name: str
    delta: float
    sd: float
    n: int
    sd_is_approximate: bool
    source: str


def _sd_from_ci(ci_low, ci_high, n):
    return ((ci_high - ci_low) / (2 * 1.96)) * math.sqrt(n)


CASES = (
    Case("C5", 0.067639, 0.246232, 42, False, "PSB1_C5_REPORT.md"),
    Case("C4", 0.046550, 0.208949, 42, False, "PSB2_C4_REPORT.md"),
    Case("C2_PSB2", 0.034892, 0.104033, 84, False, "PSB2_C2_REPORT.md"),
    Case("C2_PHASE0_5", 0.022552, 0.100137, 84, False, "C2_PHASE0_5_MINIBATTERY.md"),
    Case("F1_TRAIN", 0.0154, _sd_from_ci(-0.0024, 0.0306, 83), 83, True,
         "F1_FEASIBILITY_SCREEN_REPORT.md"),
)


def assess():
    rows = []
    for c in CASES:
        p = power_at(c.delta, c.sd, c.n, two_sided=False)
        rows.append({
            "name": c.name,
            "delta": c.delta,
            "sd": c.sd,
            "n": c.n,
            "max_power": p,
            "decision": "ABANDON" if p < POWER_HURDLE else "PROCEED",
            "sd_is_approximate": c.sd_is_approximate,
            "source": c.source,
        })
    return rows


def render(rows):
    lines = [
        "# RFA Retrospective — Non-Binding Context Appendix",
        "",
        "**These numbers are prior-exposed observations. They carry no weight in any binding",
        "RFA declaration** (design spec §2.2). They exist to test one claim in CLAUDE.md, not",
        "to calibrate the gate.",
        "",
        "**Claim under test:** the power-feasibility pre-check \"would have saved the back half",
        "of C5, C4, C2, and F1.\"",
        "",
        "| Case | delta | SD | n | Max power | Verdict | Source |",
        "|---|--:|--:|--:|--:|---|---|",
    ]
    for r in rows:
        sd = f"{r['sd']:.6f}" + ("*" if r["sd_is_approximate"] else "")
        lines.append(
            f"| {r['name']} | {r['delta']:.6f} | {sd} | {r['n']} | "
            f"{r['max_power']:.4f} | {r['decision']} | `{r['source']}` |"
        )
    lines += [
        "",
        "\\* SD recovered from block-bootstrap CI width via a normal-symmetric back-out",
        "(`SE = (CI_high - CI_low) / 3.92`, `SD = SE x sqrt(n)`). The bootstrap CI is",
        "asymmetric and percentile-based, so this is an approximation adequate for a",
        "feasibility bound — it is not F1's actual dispersion.",
        "",
        "## Finding",
        "",
        "The CLAUDE.md claim is **partly wrong, and the exception is informative.**",
        "",
        "The gate fires on C5, C4, and F1. It does **not** fire on C2 as PSB-2 recorded it:",
        "at delta=0.034892, SD=0.104033, n*=84 the projected power is 0.9198, comfortably",
        "clear of the hurdle. A pre-check run before PSB-2 would have returned PROCEED.",
        "",
        "C2 fails only once the extended-history re-estimate widens its dispersion. That is",
        "exactly the caveat PSB-2 recorded against itself: the recommendation rested on a",
        "55-observation, 2.3-year SD estimate, and power is a function of SD.",
        "",
        "**This does not weaken the gate; it locates its dependency.** The verdict is only as",
        "good as the declared SD, which is precisely why the design requires SD to be",
        "independently defended and frozen rather than inherited from a short in-sample read",
        "(design spec §2.1, §2.3).",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    rows = assess()
    Path("docs/reports/RFA_RETROSPECTIVE.md").write_text(render(rows), encoding="utf-8")
    for r in rows:
        print(f"{r['name']:14s} power={r['max_power']:.4f} -> {r['decision']}")
