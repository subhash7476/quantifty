import math

from scripts.rfa.gate import POWER_HURDLE


def render(decl, verdict, digest):
    meaning = (
        "The construct cannot be demonstrated at the declared bands. Do not build it."
        if verdict.decision == "ABANDON"
        else "not provably infeasible — this is a floor, not authorization to build."
    )
    lines = [
        f"# {decl.name} — Research Feasibility Assessment",
        "",
        f"**VERDICT: {verdict.decision}** — {meaning}",
        "",
        f"- Methodology version: `{verdict.methodology_version}`",
        f"- Declaration SHA-256: `{digest}`",
        f"- Metric: {decl.metric} | Test: {decl.test_type} | Power hurdle: {POWER_HURDLE}",
        f"- Formations available: {decl.n_available} ({decl.cadence}, {decl.window})",
        "",
    ]
    if decl.metric == "per_trade_pnl":
        lines += _render_per_trade_pnl(decl, verdict)
    else:
        lines += _render_rank_ic(decl, verdict)
    lines += _render_scope()
    return "\n".join(lines)


def _render_rank_ic(decl, verdict):
    return [
        "## Optimistic corner",
        "",
        "| Quantity | Value |",
        "|---|---|",
        f"| delta (high) | {verdict.corner_delta} |",
        f"| SD (low) | {verdict.corner_sd} |",
        f"| n (raw, no AC haircut) | {verdict.n_available} |",
        f"| **Max achievable power** | **{verdict.max_power:.4f}** |",
        "",
        "The corner is **intentionally unrealistic.** This independence holds for",
        "`rank_ic` because IC mean and IC dispersion are separately estimable — a",
        "declaration coupling them (e.g. deriving one from the other) is invalid and",
        "the gate's `validate()` will reject it. With independence established,",
        "(delta_hi, sd_lo) describes a large edge with unusually stable outcomes —",
        "the least plausible combination in practice and the most generous to the",
        "construct. This maximizes the burden of proof for ABANDON, so a firing gate",
        "is unarguable, while correspondingly weakening PROCEED to its stated meaning",
        "of *not provably infeasible*.",
        "",
        "## Formations required for power 0.80",
        "",
        "| Band point | n required |",
        "|---|---|",
        f"| Optimistic corner | {verdict.n_required_corner} |",
        f"| Central | {verdict.n_required_central} |",
        f"| Pessimistic | {verdict.n_required_pessimistic} |",
        f"| **Available** | **{verdict.n_available}** |",
        "",
        "## Declared bands and provenance",
        "",
        f"**delta: [{decl.delta_lo}, {decl.delta_hi}]**",
        "",
        decl.delta_provenance,
        "",
        f"**SD: [{decl.sd_lo}, {decl.sd_hi}]**",
        "",
        decl.sd_provenance,
        "",
        "**Prior exposure**",
        "",
        decl.prior_exposure,
        "",
    ]


def _render_per_trade_pnl(decl, verdict):
    c = decl.cadence_per_year
    T_years = decl.n_available / c
    per_formation_corner = verdict.corner_sharpe / math.sqrt(c)
    return [
        "## Optimistic corner",
        "",
        "| Quantity | Value |",
        "|---|---|",
        f"| Annualized Sharpe (high) | {verdict.corner_sharpe} |",
        f"| Cadence per year | {c} |",
        f"| Per-formation Sharpe | {per_formation_corner:.6f} |",
        f"| Elapsed time T = n/c | {T_years:.4f} years |",
        f"| n (raw, no AC haircut) | {verdict.n_available} |",
        f"| **Max achievable power** | **{verdict.max_power:.4f}** |",
        "",
        "**There is no crossed corner for `per_trade_pnl`.** The noncentrality",
        f"parameter reduces to `ncp = (S/√c)·√(c·T) = S·√T`, so cadence cancels and",
        f"power depends only on annualized Sharpe and elapsed time. Declaring separate",
        f"`delta` and `sd` bands for a PnL metric would re-introduce a redundant degree",
        f"of freedom the gate does not inspect (the O1 defect, `RFA_GATE_O1_REVIEW.md`",
        f"§1); the contract forbids it. SD is *not* a free parameter here — it is",
        f"fully determined once Sharpe and the per-formation mean are pinned.",
        "",
        "## Formations required for power 0.80",
        "",
        "| Band point | Annualized Sharpe | n required |",
        "|---|---|---|",
        f"| Optimistic corner | {decl.sharpe_hi} | {verdict.n_required_corner} |",
        f"| Central | {(decl.sharpe_lo + decl.sharpe_hi) / 2} | {verdict.n_required_central} |",
        f"| Pessimistic | {decl.sharpe_lo} | {verdict.n_required_pessimistic} |",
        f"| **Available** | — | **{verdict.n_available}** |",
        "",
        "Equivalently (because cadence cancels): power 0.80 is reachable **iff** the",
        "true annualized Sharpe clears the threshold implied by T alone. A longer time",
        "window helps; a higher cadence does not.",
        "",
        "## Declared Sharpe band and provenance",
        "",
        f"**Annualized Sharpe: [{decl.sharpe_lo}, {decl.sharpe_hi}]** at cadence",
        f"{c} formations/year.",
        "",
        decl.sharpe_provenance,
        "",
        "**Prior exposure**",
        "",
        decl.prior_exposure,
        "",
    ]


def _render_scope():
    return [
        "## Scope",
        "",
        "This assessment covers **demonstrability only.** It does not evaluate fees, MaxDD,",
        "turnover, or economic significance. A construct can clear this gate and still fail",
        "on transaction costs, as PSB-1's C1-C4 did. ABANDON is dispositive; PROCEED is not",
        "clearance.",
        "",
    ]
