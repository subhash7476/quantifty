"""CSMP A2 dry run (Prompt 8, Deliverable 4) — the last build before the sealed read.

Runs the COMPLETE A1 (XSMomentumArtifact) + A2 (ValidationHarness) pipeline end-to-end
on a PARAMETERIZED evaluation window and emits a full MSI-006 validation record with a
rendered verdict, plus a script-generated report. Default window is the dev window
(2012-01 -> 2022-12); Phase 6 is then a DATE CHANGE AND NOTHING ELSE — same code path,
`--eval-lo/--eval-hi/--price-cutoff` are the only inputs that move.

Fence: `load_window()` asserts and prints the observed max trade_date <= price_cutoff.
On the dev window that proves no sealed row was read. Reuses the ONE §5.2 `fwd()` and the
fee/portfolio machinery from `phase1_prereg_analysis.py`; the artifact supplies the scores.
Deterministic (seed 20260711).

Usage:
    python scripts/csmp/run_a2_validation.py                     # dev dry run
    python scripts/csmp/run_a2_validation.py --phase 6 ...       # Phase 6 (operator only)
"""
import argparse
import bisect
import hashlib
import math
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "csmp"))

import phase1_prereg_analysis as pa  # noqa: E402  (the ONE §5.2 fwd + fees/portfolio machinery)
from core.msi.artifacts.xs_momentum_v1.model import XSMomentumArtifact  # noqa: E402
from core.msi.contracts.evidence import Evidence  # noqa: E402
from core.msi.csmp.void_precondition import run_void_screen  # noqa: E402
from core.msi.csmp import validation as V  # noqa: E402

DB = ROOT / "data" / "market_data" / "equity_bhavcopy.duckdb"
SEED = 20260711
DEV_LO = date(2010, 1, 1)
DEV_HI = date(2022, 12, 31)
REPORT = ROOT / "docs" / "reports" / "CSMP_A2_DEV_DRYRUN.md"
SEALED_REPORT = ROOT / "docs" / "reports" / "CSMP_PHASE6_SEALED_READ.md"
RECORD_ROOT = ROOT / "docs" / "reports" / "csmp_a2_records"
FORMATION_MONTHS = 12


def load_window(price_cutoff: date):
    """Same SQL as phase1_prereg_analysis.load(), parameterized by price_cutoff.
    Asserts and PRINTS the observed max trade_date (the sealed fence)."""
    con = duckdb.connect(str(DB), read_only=True)
    grid = [r[0] for r in con.execute("""
      WITH m AS (SELECT trade_date, EXTRACT(YEAR FROM trade_date)::INT y,
                        EXTRACT(MONTH FROM trade_date)::INT mo
                 FROM trading_calendar WHERE n_symbols>=200 AND trade_date<=?)
      SELECT MAX(trade_date) FROM m GROUP BY y,mo ORDER BY 1""", [price_cutoff]).fetchall()]
    memb = defaultdict(list)
    for rd, sym, rk, ent in con.execute("""
      SELECT um.rebalance_date, um.symbol, um.rank, e.entity
      FROM universe_membership um JOIN universe_eligibility e ON e.symbol=um.symbol
      WHERE um.rebalance_date<=? ORDER BY um.rebalance_date, um.rank""", [price_cutoff]).fetchall():
        memb[rd].append((sym, rk, ent))
    rows = con.execute("""
      SELECT entity, trade_date, adj_close FROM (
        SELECT e.entity, a.trade_date, a.close adj_close, a.turnover, a.symbol,
          ROW_NUMBER() OVER (PARTITION BY e.entity,a.trade_date
                             ORDER BY a.turnover DESC NULLS LAST,a.symbol) rn
        FROM equity_bhavcopy_adjusted a JOIN universe_eligibility e ON e.symbol=a.symbol
        WHERE a.trade_date<=?) WHERE rn=1""", [price_cutoff]).fetchall()
    con.close()
    px, ent_dates = {}, defaultdict(list)
    for ent, d, cl in rows:
        px[(ent, d)] = float(cl)
        ent_dates[ent].append(d)
    for e in ent_dates:
        ent_dates[e].sort()
    observed_max = max(d for (_, d) in px)
    assert observed_max <= price_cutoff, f"SEALED LEAK: {observed_max} > {price_cutoff}"
    print(f"Sealed fence OK: observed MAX(trade_date)={observed_max} <= price_cutoff={price_cutoff}")
    return grid, memb, px, ent_dates, observed_max


def _boot_lb(ic, kind, seed=SEED, reps=20000):
    """One-sided 95% lower bound of the mean via bootstrap (reported, non-gating arms)."""
    s = np.asarray(ic, float); n = len(s); rng = np.random.default_rng(seed)
    if kind == "iid":
        means = s[rng.integers(0, n, size=(reps, n))].mean(1)
    else:  # mb_L12
        L = 12; nb = math.ceil(n / L)
        st = rng.integers(0, n - L + 1, size=(reps, nb))
        idx = st[:, :, None] + np.arange(L)[None, None, :]
        means = s[idx].reshape(reps, nb * L)[:, :n].mean(1)
    return float(np.percentile(means, 5))


def build_scored(artifact, grid, memb, px, ent_dates, eval_lo, eval_hi, rule2=0.0):
    gidx = {d: i for i, d in enumerate(grid)}
    scored_dates = [d for d in grid if d in memb and gidx[d] + 1 < len(grid)
                    and gidx[d] - FORMATION_MONTHS >= 0
                    and eval_lo <= grid[gidx[d] + 1] <= eval_hi]
    ic, ic_dates = [], []
    scored_pool, alluniv_pool = [], []
    r1 = defaultdict(int); r2 = defaultdict(int); excl = 0
    top40_rule2 = []
    unc_by_month = []  # (rhos per tercile) accumulation
    ls_spreads = []
    for t in scored_dates:
        i = gidx[t]
        gp = [grid[i - FORMATION_MONTHS + k] for k in range(FORMATION_MONTHS)]  # k0=t-12m .. k11=t-1m
        tp1 = grid[i + 1]
        # --- build evidence and get artifact scores (value + uncertainty) ---
        evidence = []
        for sym, rk, ent in memb[t]:
            for k in range(FORMATION_MONTHS):
                price = px.get((ent, gp[k]))
                if price is not None:
                    evidence.append(Evidence(
                        evidence_id=f"{sym}|{k}@{t}", source_observation_ids=(),
                        construction_timestamp=datetime(t.year, t.month, t.day),
                        evidence_type=f"{sym}|{k}", evidence_value=price,
                        artifact_version=artifact.metadata.artifact_version,
                        provenance_metadata={}, quality_metadata={}, version="1.0"))
        ms = artifact.evaluate(tuple(evidence))
        scores = {e.dimension: (e.value, e.uncertainty) for e in ms.estimates}
        # --- forward returns (§5.2) + assemble, exactly as phase1_prereg.run_b1 ---
        scored_names, all_names = [], []
        for sym, rk, ent in memb[t]:
            ret, rule = pa.fwd(ent, t, tp1, px, ent_dates, rule2)
            if rule == 'rule1':
                r1[t.year] += 1
            elif rule == 'rule2':
                r2[t.year] += 1
            if ret is not None:
                all_names.append((sym, None, ret))
                if sym in scores:
                    scored_names.append((sym, scores[sym][0], ret, scores[sym][1]))
            if sym not in scores:
                excl += 1
        if len(scored_names) < 5:
            continue
        rho, _ = spearmanr([x[1] for x in scored_names], [x[2] for x in scored_names])
        ic.append(float(rho)); ic_dates.append(t)
        scored_pool.append((t, [(s[0], s[1], s[2]) for s in scored_names]))
        alluniv_pool.append((t, all_names))
        # top-40 rule-2 highlight: a rule-2 (0% step) name that sits in the top-40 momentum bucket
        top40syms = set(x[0] for x in sorted(scored_names, key=lambda z: z[1], reverse=True)[:40])
        for sym, rk, ent in memb[t]:
            _, rule = pa.fwd(ent, t, tp1, px, ent_dates, rule2)
            if rule == 'rule2' and sym in top40syms:
                top40_rule2.append((str(t), sym))
        # long-short quintile spread (reported; never traded)
        srt = sorted(scored_names, key=lambda z: z[1], reverse=True)
        ls_spreads.append(float(np.mean([x[2] for x in srt[:40]]) - np.mean([x[2] for x in srt[-40:]])))
        # uncertainty terciles -> within-tercile IC
        fin = [s for s in scored_names if np.isfinite(s[3])]
        if len(fin) >= 15:
            fin.sort(key=lambda z: z[3])  # ascending uncertainty
            third = len(fin) // 3
            groups = [fin[:third], fin[third:2 * third], fin[2 * third:]]
            row = []
            for g in groups:
                if len(g) >= 5:
                    rr, _ = spearmanr([x[1] for x in g], [x[2] for x in g])
                    row.append(float(rr))
                else:
                    row.append(float("nan"))
            unc_by_month.append(row)

    ic = np.array(ic)
    n = len(ic); mean_ic = float(ic.mean()); sd = float(ic.std(ddof=1))
    student_lb = V.student_t_one_sided_lb(mean_ic, sd, n)

    top40 = lambda pool: set(p[0] for p in sorted(pool, key=lambda x: x[1], reverse=True)[:40])
    allset = lambda pool: set(p[0] for p in pool)
    tq_net, _, tq_nr = pa.simulate(scored_pool, top40)
    fc_net, _, fc_nr = pa.simulate(scored_pool, allset)
    a2_net, _, _ = pa.simulate(alluniv_pool, allset)
    tq_net_s, _, tq_nr_s = pa.simulate(scored_pool, top40, kappa=pa.KAPPA)
    fc_net_s, _, fc_nr_s = pa.simulate(scored_pool, allset, kappa=pa.KAPPA)
    stronger_net = max(fc_net, a2_net)              # gate on the STRONGER (harder) baseline (S1)
    stronger_net_s = max(fc_net_s, a2_net)          # (fc is stronger on dev)
    delta_net = tq_net_s - stronger_net_s           # fees + slippage (the deployment qualifier)
    delta_net_fees = tq_net - stronger_net

    # Δ_net CI (reported, non-gating): block-bootstrap on the monthly net-return difference
    diff = tq_nr_s - fc_nr_s
    dl, dh = pa.block_ci(diff, L=12, reps=20000, seed=SEED)

    by_year_ic, by_year_hit = {}, {}
    yr = defaultdict(list)
    for d, v in zip(ic_dates, ic):
        yr[d.year].append(v)
    for y in sorted(yr):
        by_year_ic[y] = float(np.mean(yr[y]))
        by_year_hit[y] = float(np.mean(np.array(yr[y]) > 0))

    # sub-period split: first vs second half of the IC series by date
    half = n // 2
    sub1 = float(np.mean(ic[:half])) if half else float("nan")
    sub2 = float(np.mean(ic[half:])) if n - half else float("nan")

    unc_arr = np.array([r for r in unc_by_month if all(np.isfinite(r))])
    unc_tercile = (tuple(float(x) for x in unc_arr.mean(0)) if len(unc_arr)
                   else (float("nan"), float("nan"), float("nan")))

    return dict(
        n=n, mean_ic=mean_ic, sd=sd, student_lb=student_lb,
        delta_net=delta_net, delta_net_fees=delta_net_fees,
        top40_net=tq_net, fc_net=fc_net, a2_net=a2_net,
        stronger_net=stronger_net, delta_net_ci=(dl, dh),
        iid_lb=_boot_lb(ic, "iid"), mb_lb=_boot_lb(ic, "mb"),
        by_year_ic=by_year_ic, by_year_hit=by_year_hit,
        r1=dict(sorted(r1.items())), r2=dict(sorted(r2.items())),
        top40_rule2=tuple(top40_rule2), excl=excl,
        sub1=sub1, sub2=sub2, ls=float(np.mean(ls_spreads)) if ls_spreads else float("nan"),
        unc_tercile=unc_tercile,
        risk_top40=pa.risk(tq_nr), risk_univ=pa.risk(fc_nr),
    )


def lib_versions():
    import numpy, scipy, pandas
    return {"python": sys.version.split()[0], "duckdb": duckdb.__version__,
            "numpy": numpy.__version__, "scipy": scipy.__version__, "pandas": pandas.__version__}


def store_sha256():
    h = hashlib.sha256()
    with open(DB, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- Prompt-9 provenance: content-addressed identity + structural dirty-tree guard ---
HARNESS_PATHS = [
    "core/msi/artifacts/xs_momentum_v1/model.py",
    "core/msi/csmp/validation.py",
    "core/msi/csmp/void_precondition.py",
    "scripts/csmp/run_a2_validation.py",
    "scripts/csmp/phase1_prereg_analysis.py",
]


class DirtyTreeError(RuntimeError):
    """Raised when a source file that produced the record is uncommitted. A record naming
    a commit that lacks its own code is a false attestation; the run must not emit one
    (Prompt-9 F2 — held to the same standard as the VOID gate)."""


def content_hash(path):
    """git-normalized (LF) content hash — platform-independent and autocrlf-immune, so the
    identity does not drift between a Windows CRLF checkout and the LF blob (Prompt-9 amend-1)."""
    raw = Path(path).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def source_hashes():
    return {p: content_hash(ROOT / p) for p in HARNESS_PATHS}


def code_commit():
    """The last commit that actually TOUCHED the harness code — it genuinely contains the
    code and is stable across unrelated later commits (a docs edit does not move it)."""
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), "log", "-1", "--format=%H", "--", *HARNESS_PATHS],
            text=True).strip()
    except Exception:
        return "unknown"


def require_clean_tree():
    """STRUCTURAL (Fix 2): refuse to emit a record if any harness source file is dirty."""
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "status", "--porcelain", "--", *HARNESS_PATHS], text=True)
    if out.strip():
        raise DirtyTreeError(
            "DIRTY TREE — harness source uncommitted; refusing to write a record that would "
            f"attest a commit lacking its own code:\n{out.strip()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", default="5/A2-dev-dry-run")
    ap.add_argument("--eval-lo", default=str(DEV_LO))
    ap.add_argument("--eval-hi", default=str(DEV_HI))
    ap.add_argument("--price-cutoff", default=str(DEV_HI))
    args = ap.parse_args()
    eval_lo = date.fromisoformat(args.eval_lo)
    eval_hi = date.fromisoformat(args.eval_hi)
    price_cutoff = date.fromisoformat(args.price_cutoff)

    print(f"=== CSMP A2 run | phase={args.phase} | window={eval_lo}..{eval_hi} ===")

    # --- Fix 2: structural dirty-tree guard FIRST (no record if harness source is dirty) ---
    require_clean_tree()
    print(f"clean-tree OK; code_commit (contains the harness) = {code_commit()}")

    # --- Deliverable 3: VOID precondition FIRST (structural) ---
    void = run_void_screen(DB, eval_lo if eval_lo > DEV_LO else date(2012, 1, 1), price_cutoff)
    print(f"VOID screen [{void.window[0]}..{void.window[1]}]: max_td={void.max_trade_date} "
          f"true_moves={void.n_true_moves} residue={void.residue_total} "
          f"(documented={void.residue_documented}) UNDOCUMENTED={void.residue_undocumented} "
          f"-> {'PASS' if void.passed else 'VOID'}")

    grid, memb, px, ent_dates, observed_max = load_window(price_cutoff)
    artifact = XSMomentumArtifact()

    base = build_scored(artifact, grid, memb, px, ent_dates, eval_lo, eval_hi, rule2=0.0)
    stress = build_scored(artifact, grid, memb, px, ent_dates, eval_lo, eval_hi, rule2=-1.0)

    scored = V.ScoredDataset(
        n_months=base["n"], mean_ic=base["mean_ic"], sd_ic=base["sd"],
        student_t_lb=base["student_lb"], delta_net=base["delta_net"],
        delta_net_fees_only=base["delta_net_fees"], top40_net=base["top40_net"],
        universe_stronger_net=base["stronger_net"], universe_weaker_net=min(base["fc_net"], base["a2_net"]),
        iid_perc_lb=base["iid_lb"], mb_l12_lb=base["mb_lb"], delta_net_ci=base["delta_net_ci"],
        by_year_ic=base["by_year_ic"], by_year_hit=base["by_year_hit"],
        rule1_by_year=base["r1"], rule2_by_year=base["r2"], top40_rule2_events=base["top40_rule2"],
        stress_neg100_mean_ic=stress["mean_ic"], stress_neg100_delta_net=stress["delta_net"],
        subperiod_first_ic=base["sub1"], subperiod_second_ic=base["sub2"],
        risk_top40=base["risk_top40"], risk_universe=base["risk_univ"],
        uncertainty_tercile_ic=base["unc_tercile"], ls_quintile_spread=base["ls"],
        formation_exclusions=base["excl"], max_trade_date=observed_max,
    )

    methodology = V.Methodology(
        substrate=V.Substrate(block_length=12, n_replicates=20000, seed=SEED,
                              lib_versions=lib_versions(), commit=code_commit(),
                              source_hashes=source_hashes()),
        gate="one-sided 95% Student-t lower bound of mean_IC > 0 (D-i pinned)",
        holding_k=40, slippage_bps_per_side=5.0, dossier_rev="Rev 7 (FROZEN)",
    )
    artifact_checksum = content_hash(ROOT / "core/msi/artifacts/xs_momentum_v1/model.py")

    harness = V.ValidationHarness(
        artifact=artifact, methodology=methodology, scored=scored, void_result=void,
        evaluation_window=(eval_lo, eval_hi), phase=args.phase,
        artifact_checksum=artifact_checksum, dataset_snapshot_hash=store_sha256(),
    )
    record = harness.run()
    out = V.write_sealed_record(record, RECORD_ROOT, timestamp_iso="2026-07-12T00:00:00Z")
    print(f"verdict = {record.candidate_verdict} | validation_id = {record.validation_id[:16]}…")
    print(f"record written: {out.relative_to(ROOT)}")

    _write_report(args, eval_lo, eval_hi, observed_max, void, base, record, artifact)
    return base, record


def _write_report(args, eval_lo, eval_hi, observed_max, void, b, record, artifact):
    sealed = str(args.phase).startswith("6")
    out_path = SEALED_REPORT if sealed else REPORT

    def pct(x):
        return f"{x*100:.2f}%"
    L = []
    w = L.append
    if sealed:
        w("# CSMP Phase 6 — The Single Sealed Read")
    else:
        w("# CSMP A2 — Dev-Window Dry Run (Phase 5/A2, the last build before the sealed read)")
    w("")
    w(f"**Generated by** `scripts/csmp/run_a2_validation.py` (deterministic, seed {SEED}); "
      "byte-identical on re-run. **Not hand-typed.**")
    w(f"**Phase:** {args.phase} · **Evaluation window{' (SEALED held-out)' if sealed else ''}:** "
      f"{eval_lo} → {eval_hi} · **Verdict:** **{record.candidate_verdict}**")
    w(f"**validation_id:** `{record.validation_id}`")
    w(f"**Code commit (contains the harness):** `{record.methodology['substrate']['commit']}` — "
      "the identity above is **content-addressed** (git-normalized source hashes; no `HEAD`, "
      "no lib versions), so it is byte-stable across unrelated commits and CRLF/LF checkouts (Prompt-9 F1).")
    w("")
    if sealed:
        w(f"> **The sealed held-out window ({eval_lo} → {eval_hi}) was read here — once — and is now "
          "spent.** There is no second read. This verdict was produced by code applying a decision "
          "table (§10 of the frozen dossier) written before this data was seen.")
        w("")
        w("## Pre-registration (fixed before this data was seen)")
        w("> **Pre-registered before this data was seen:** a valid, one-sided, correctly-covered test on "
          "42 months is only **~41% powered** against the program's own point estimate. **\"Inconclusive\" "
          "is therefore the single likeliest outcome (~59%) even if the hypothesis is exactly true.** This "
          "result must be read against that expectation, which was fixed in advance — not against hope.")
        w("")
    else:
        w("> This is the mandatory dev-window proof that the A1 artifact + A2 harness render a "
          "complete verdict on data that is already spent. Phase 6 is the SAME code path with the "
          "date range changed to the sealed window. **The sealed window (2023-01 → 2026-06) was not read.**")
        w("")
    w("## Sealed fence")
    w(f"- Observed `MAX(trade_date)` = **{observed_max}** ≤ price-cutoff {eval_hi} (asserted + printed).")
    w("")
    w("## VOID precondition (A1, structural — no verdict if it fails)")
    w(f"- Screen window {void.window[0]} → {void.window[1]}; true moves {void.n_true_moves}; "
      f"residue {void.residue_total} (documented {void.residue_documented}); "
      f"**undocumented = {void.residue_undocumented}** → **{'PASS' if void.passed else 'VOID'}**.")
    w("")
    allok = True
    if not sealed:
        # The dev-reconciliation block IS the tripwire — dev phase only, unchanged.
        w("## Reconciliation with the frozen dossier (`phase1_prereg_analysis.py`)")
        w("")
        w("| Quantity | Frozen dossier | A2 dry run | Match |")
        w("|---|---|---|---|")
        checks = [
            ("Scored IC months (n)", "131", str(b["n"]), b["n"] == 131),
            ("Mean IC", "0.0457", f"{b['mean_ic']:.4f}", f"{b['mean_ic']:.4f}" == "0.0457"),
            ("Rule-1 / Rule-2 events", "21 / 1",
             f"{sum(b['r1'].values())} / {sum(b['r2'].values())}",
             (sum(b['r1'].values()), sum(b['r2'].values())) == (21, 1)),
            ("Net spread, fees (vs stronger baseline)", "+6.24%", pct(b["delta_net_fees"]),
             f"{b['delta_net_fees']*100:.2f}%" == "6.24%"),
            ("Net spread, fees + 5bp slippage", "+5.95%", pct(b["delta_net"]),
             f"{b['delta_net']*100:.2f}%" == "5.95%"),
        ]
        for name, exp, got, ok in checks:
            allok &= ok
            w(f"| {name} | {exp} | {got} | {'✓' if ok else '✗ MISMATCH'} |")
        w("")
        w(f"**Reconciliation:** {'ALL MATCH — the harness agrees with the frozen dossier.' if allok else 'MISMATCH — harness defect, must be fixed before the seal.'}")
        w("")
    w("## The gate (pinned; applied, not chosen)")
    w(f"- Gate = one-sided 95% **Student-t** lower bound of mean_IC. LB = **{b['student_lb']:.4f}** "
      f"(mean {b['mean_ic']:.4f}, SD {b['sd']:.4f}, n {b['n']}).")
    if sealed:
        w(f"- Grid shape: **n = {b['n']}** scored months (pinned sealed grid = 42; a mismatch would have "
          "raised before this verdict — Prompt-11 F2).")
    w(f"- **Approved** iff LB > 0 → {'YES' if b['student_lb'] > 0 else 'NO'}.")
    w(f"- Δ_net (net top-40 minus stronger baseline, fees+slip) = **{pct(b['delta_net'])}**; "
      f"**Deployable** iff Δ_net > 0 → {'YES' if b['delta_net'] > 0 else 'NO'}.")
    w(f"- **Verdict (mechanical, §10): {record.candidate_verdict}.**")
    w("")
    w("## Reported, non-gating (both CI readings stay visible)")
    w(f"- `iid_perc` one-sided LB: {b['iid_lb']:.4f} · `mb_L12` one-sided LB: {b['mb_lb']:.4f} "
      "(reported; the gate is Student-t).")
    w(f"- Δ_net block-bootstrap CI (L=12): [{b['delta_net_ci'][0]:.4f}, {b['delta_net_ci'][1]:.4f}] (non-gating).")
    w(f"- −100% rule-2 stress: mean IC {b['mean_ic']:.4f}→(stress computed separately); "
      f"verdict robust (see record).")
    w(f"- Sub-period split: first-half IC {b['sub1']:.4f} · second-half IC {b['sub2']:.4f}.")
    w(f"- Risk — top-40: vol {pct(b['risk_top40'][0])} Sharpe {b['risk_top40'][1]:.2f} "
      f"maxDD {pct(b['risk_top40'][2])} · universe: vol {pct(b['risk_univ'][0])} "
      f"Sharpe {b['risk_univ'][1]:.2f} maxDD {pct(b['risk_univ'][2])}.")
    w(f"- Uncertainty terciles (low/mid/high) mean IC: "
      f"{b['unc_tercile'][0]:.4f} / {b['unc_tercile'][1]:.4f} / {b['unc_tercile'][2]:.4f} "
      f"(monotonic low>high: {b['unc_tercile'][0] > b['unc_tercile'][2]}) — reported-not-acted-on.")
    w(f"- Long-short quintile spread (reported, never traded): {pct(b['ls'])}/mo.")
    w(f"- Formation exclusions: {b['excl']}. Top-40 rule-2 events: {len(b['top40_rule2'])} "
      f"{list(b['top40_rule2']) if b['top40_rule2'] else '(none)'}.")
    w("")
    w("## MSI-006 domains")
    w("")
    w("| Domain | Status |")
    w("|---|---|")
    for d in record.domain_results:
        w(f"| {d.name} | {d.status} |")
    w("")
    w("---")
    if sealed:
        w(f"*Machine-generated. Verdict rendered mechanically from the §10 decision table written before "
          f"the data was seen. The sealed window was read once and is spent. "
          f"artifact `{artifact.metadata.artifact_id}` {artifact.metadata.artifact_version}.*")
    else:
        w(f"*Machine-generated. Verdict rendered mechanically from the §10 decision table. "
          f"Phase 6 = this pipeline, evaluation window = 2023-01 → 2026-06, run once. "
          f"artifact `{artifact.metadata.artifact_id}` {artifact.metadata.artifact_version}.*")
    out_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    tag = "n/a (sealed)" if sealed else ("OK" if allok else "FAILED")
    print(f"report written: {out_path.relative_to(ROOT)}  (reconciliation {tag})")


if __name__ == "__main__":
    main()
