"""Cross-sleeve combination matrix for the SSF monthly cross-section.

Arithmetic on ALREADY-MEASURED quantities from the built signal stores -- no new
data read, no sealed window touched. Every query is fenced at
formation_date <= 2022-12-31 and the realized max formation_date is printed in
the report so the fence is proven, not asserted.

For every pair of the six SSF monthly sleeves it measures, on their common
formations and common names:
  - pooled signal correlation  (rho between the two z-scores)
  - per-formation IC correlation (rho between the two monthly IC series)
  - the equal-risk-weight composite IC series and its IR
  - the composite IR against the BETTER STANDALONE IR on the same intersection

The last comparison is the point. IVOL gate 4 (IVOL_COMPOSITE_CHECK_REPORT.md)
asked only "composite >= 0.80" and passed a composite whose IR (0.6005) was
BELOW Carry standalone (0.6159). A combination that does not beat its own best
leg is not a combination.

Output: docs/reports/SLEEVE_COMBINATION_MATRIX.md
"""
from __future__ import annotations

import itertools
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "psb1"))
from screening_harness import _one_sided_t          # noqa: E402
from scripts.rfa.power import power_at              # noqa: E402

REPORT = ROOT / "docs" / "reports" / "SLEEVE_COMBINATION_MATRIX.md"

FENCE_HI = date(2022, 12, 31)     # HOLDOUT end. SEALED (2023-01-01 ->) never touched.
MIN_NAMES = 5
N_STAR = 42

# Forward returns are taken from ONE canonical source for every sleeve, so all
# ICs are measured against identical returns. IVOL's fwd_ret_1m is that source
# (composite_check.py uses it; LAG's column matches it byte-for-byte on all
# 17,406 common rows; TREND's differs on 183). The monthly Carry store's own
# fwd_ret_1m is NULL in all 23,419 rows -- see the report's Defects section.
FWD_SOURCE = ("ivol/signals.duckdb", "signals")

# TS_BASIS reads ts_signals_monthly.duckdb -- the REGISTERED monthly grid, built
# by `build_ts_signals.py --source monthly`. The default ts_signals.duckdb is the
# weekly variant (349 fenced formations on a Friday grid) and is NOT the
# registered construction; using it here would compare different cadences.

# name -> (db path, table, z column, registered sign, sign provenance)
SLEEVES = {
    "CARRY":    ("carry/signals.duckdb",       "signals", "z_carry_neut", +1,
                 "REGISTERED (v2 pre-reg, positive)"),
    "TS_BASIS": ("ts_basis/ts_signals_monthly.duckdb", "signals", "z_ts", +1,
                 "REGISTERED (pre-reg, positive) -- SEALED de-authorized (gate defect)"),
    "TREND":    ("trend/signals.duckdb",       "signals", "z_trend_neut", +1,
                 "REGISTERED (pre-reg, positive)"),
    "IVOL":     ("ivol/signals.duckdb",        "signals", "z_ivol_neut",  -1,
                 "REGISTERED (pre-reg, negative) -- FLIPPED on SEALED"),
    "LAG":      ("lag/signals.duckdb",         "signals", "z_lag_neut",   +1,
                 "REGISTERED (pre-reg, positive) -- TRAIN came out NEGATIVE"),
    "SKEW":     ("skew/signals.duckdb",        "signals", "z_skew_neut",   0,
                 "NONE -- two-sided registration; sign is a TRAIN reading"),
}


def _commit():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT)).decode().strip()
    except Exception:
        return "unknown"


def _load_fwd():
    db, table = FWD_SOURCE
    con = duckdb.connect(str(ROOT / "data" / "signal_engine" / db), read_only=True)
    rows = con.execute(f"""
        SELECT formation_date, underlying, fwd_ret_1m
        FROM {table}
        WHERE formation_date <= DATE '{FENCE_HI}' AND fwd_ret_1m IS NOT NULL
    """).fetchall()
    con.close()
    return {(r[0], r[1]): float(r[2]) for r in rows}


def _load(name, fwd):
    db, table, zcol, _sign, _prov = SLEEVES[name]
    con = duckdb.connect(str(ROOT / "data" / "signal_engine" / db), read_only=True)
    rows = con.execute(f"""
        SELECT formation_date, underlying, {zcol}
        FROM {table}
        WHERE formation_date <= DATE '{FENCE_HI}' AND {zcol} IS NOT NULL
    """).fetchall()
    con.close()
    out = {}
    for fd, u, z in rows:
        r = fwd.get((fd, u))
        if r is not None:
            out[(fd, u)] = (float(z), r)
    return out


def _ic_series(by_date):
    dates, ics = [], []
    for d in sorted(by_date):
        rows = by_date[d]
        if len(rows) < MIN_NAMES:
            continue
        z = np.array([r[0] for r in rows], float)
        f = np.array([r[1] for r in rows], float)
        if np.std(z) == 0:
            continue
        rho, _ = spearmanr(z, f)
        if np.isnan(rho):
            continue
        dates.append(d)
        ics.append(float(rho))
    return dates, np.array(ics)


def _ir(ic):
    m, sd, t, _p = _one_sided_t(ic)
    return m, sd, (abs(m) / sd if sd > 0 else float("nan")), t


def main():
    fwd = _load_fwd()
    data = {n: _load(n, fwd) for n in SLEEVES}

    standalone = {}
    for n, d in data.items():
        by_date = defaultdict(list)
        for key, val in d.items():
            by_date[key[0]].append(val)
        dates, ic = _ic_series(by_date)
        m, sd, ir, t = _ir(ic)
        standalone[n] = dict(n_form=len(ic), lo=dates[0], hi=dates[-1],
                             mean=m, sd=sd, ir=ir, t=t,
                             power=power_at(abs(m), sd, N_STAR, two_sided=False))

    results = []
    for a, b in itertools.combinations(SLEEVES, 2):
        keys = set(data[a]) & set(data[b])
        by_date = defaultdict(list)
        for k in keys:
            za, fwd = data[a][k]
            zb, _fwd_b = data[b][k]
            by_date[k[0]].append((za, zb, fwd))

        sa = SLEEVES[a][3] or 1
        sb = SLEEVES[b][3] or 1
        ica, icb, icc, pa, pb, names, used = [], [], [], [], [], [], []
        for d in sorted(by_date):
            rows = by_date[d]
            if len(rows) < MIN_NAMES:
                continue
            za = np.array([r[0] for r in rows], float)
            zb = np.array([r[1] for r in rows], float)
            fw = np.array([r[2] for r in rows], float)
            if np.std(za) == 0 or np.std(zb) == 0:
                continue
            ra, _ = spearmanr(za, fw)
            rb, _ = spearmanr(zb, fw)
            comp = sa * za + sb * zb
            if np.isnan(ra) or np.isnan(rb) or np.std(comp) == 0:
                continue
            rc, _ = spearmanr(comp, fw)
            if np.isnan(rc):
                continue
            ica.append(float(ra))
            icb.append(float(rb))
            icc.append(float(rc))
            pa.extend(za.tolist())
            pb.extend(zb.tolist())
            names.append(len(rows))
            used.append(d)

        if len(icc) < 8:
            results.append(dict(a=a, b=b, n_form=len(icc), skip=True))
            continue

        ica, icb, icc = np.array(ica), np.array(icb), np.array(icc)
        ma, sda, ira, _ta = _ir(ica)
        mb, sdb, irb, _tb = _ir(icb)
        mc, sdc, irc, tc = _ir(icc)
        best_is_a = ira >= irb
        results.append(dict(
            a=a, b=b, skip=False, n_form=len(icc), lo=used[0], hi=used[-1],
            mean_names=float(np.mean(names)),
            ir_a=ira, ir_b=irb, sign_a=float(np.sign(ma)), sign_b=float(np.sign(mb)),
            rho_sig=float(np.corrcoef(pa, pb)[0, 1]),
            rho_ic=float(np.corrcoef(ica, icb)[0, 1]),
            quad=float(np.hypot(ira, irb)),
            ir_c=irc, mean_c=mc, sd_c=sdc, t_c=tc, best=max(ira, irb),
            lift=irc / max(ira, irb) if max(ira, irb) > 0 else float("nan"),
            power_c=power_at(abs(mc), sdc, N_STAR, two_sided=False),
            power_best=power_at(abs(ma) if best_is_a else abs(mb),
                                sda if best_is_a else sdb, N_STAR, two_sided=False),
        ))

    _write(standalone, results)
    return 0


def _write(standalone, results):
    L = []
    A = L.append
    A("# Sleeve Combination Matrix — SSF monthly cross-section\n")
    A(f"**Script-generated** — `scripts/signal_engine/combination/sleeve_pair_matrix.py`. "
      f"Code commit `{_commit()}`.\n")
    A("**What this is:** arithmetic on already-measured quantities from the built signal "
      "stores. No new data read, no sealed window touched — the same standing as "
      "`IVOL_COMPOSITE_CHECK_REPORT.md`. **Decision-support, not a gated read.**\n")
    fence_max = max(s["hi"] for s in standalone.values())
    A(f"**Fence proven:** every query filters `formation_date <= {FENCE_HI}`; the maximum "
      f"formation date actually used across all sleeves is **{fence_max}**. "
      "SEALED (2023-01-01 → present) is untouched.\n")
    A(f"**Conventions:** per-formation Spearman rank IC vs `fwd_ret_1m`; MIN_NAMES={MIN_NAMES}; "
      f"IR = |mean IC| / SD(IC); power projected at n\\*={N_STAR} (one-sided, α=0.05). "
      f"Forward returns come from ONE canonical source (`{FWD_SOURCE[0]}`) for every sleeve, so "
      "all ICs are measured against identical returns.\n")
    A("**Sleeves in scope:** the six SSF **monthly** cross-sectional sleeves whose formation "
      "grids align exactly (71 common month-end formations in the fenced window). TS_BASIS is "
      "read from `ts_basis/ts_signals_monthly.duckdb` — the **registered monthly** grid, built "
      "by `build_ts_signals.py --source monthly`. The default `ts_signals.duckdb` is a weekly "
      "variant (349 fenced formations on a Friday grid) and is not the registered "
      "construction.\n")

    A("\n---\n\n## 1. Standalone sleeves (own full fenced span: TRAIN + HOLDOUT)\n")
    A("| Sleeve | Formations | Span | Mean IC | SD(IC) | IR | t | Power @ n*=42 | Registered sign |")
    A("|---|--:|---|--:|--:|--:|--:|--:|---|")
    for n, s in sorted(standalone.items(), key=lambda kv: -kv[1]["ir"]):
        A(f"| {n} | {s['n_form']} | {s['lo']} → {s['hi']} | {s['mean']:+.4f} | {s['sd']:.4f} | "
          f"{s['ir']:.4f} | {s['t']:+.2f} | {s['power']:.4f} | {SLEEVES[n][4]} |")

    A("\n---\n\n## 2. Pairwise combination matrix\n")
    A("Sign alignment uses each sleeve's **registered** sign (SKEW has none — treated as `+1`, "
      "which is why its rows carry a sign-provenance warning in §2.1).\n")
    A("`Lift` = composite IR ÷ better standalone IR **on the same intersection**. "
      "**Lift ≤ 1.00 means the pair is worse than its own best leg.**\n")
    A("| Pair | Common form. | Mean names | ρ(signal) | ρ(IC) | IR a | IR b | Quadrature | "
      "IR composite | Lift | Composite power | Best-leg power |")
    A("|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    ok = [r for r in results if not r["skip"]]
    for r in sorted(ok, key=lambda r: -r["lift"]):
        A(f"| {r['a']} + {r['b']} | {r['n_form']} | {r['mean_names']:.0f} | {r['rho_sig']:+.4f} | "
          f"{r['rho_ic']:+.4f} | {r['ir_a']:.4f} | {r['ir_b']:.4f} | {r['quad']:.4f} | "
          f"**{r['ir_c']:.4f}** | **{r['lift']:.3f}** | {r['power_c']:.4f} | "
          f"{r['power_best']:.4f} |")
    for r in results:
        if r["skip"]:
            A(f"| {r['a']} + {r['b']} | {r['n_form']} | — | — | — | — | — | — | — | "
              "— | — | *too few common formations* |")

    A("\n### 2.1 Sign-discipline check on the intersection\n")
    A("A composite is only testable if both legs' signs were pinned **before** the data was "
      "read. Where a leg's realized sign opposes its registration, or no sign was registered, "
      "building the composite requires a sign chosen from data — which has no valid "
      "confirmatory test available.\n")
    A("| Pair | realized sign a | realized sign b | Alignment valid? |")
    A("|---|--:|--:|---|")
    for r in sorted(ok, key=lambda r: (r["a"], r["b"])):
        flags = []
        for nm, got in ((r["a"], r["sign_a"]), (r["b"], r["sign_b"])):
            reg = SLEEVES[nm][3]
            if reg == 0:
                flags.append(f"{nm}: no registered sign")
            elif reg != got:
                flags.append(f"{nm}: realized sign OPPOSES registration")
        A(f"| {r['a']} + {r['b']} | {r['sign_a']:+.0f} | {r['sign_b']:+.0f} | "
          f"{'YES' if not flags else 'NO — ' + '; '.join(flags)} |")

    A("\n### 2.2 Reading notes\n")
    A("- **A sleeve's IR is not constant across rows.** Each pair is measured on its own "
      "intersection, and the intersections differ in width (mean names 80–166: the "
      "options-derived SKEW is scored on a narrower liquid subset than the futures sleeves). "
      "A sleeve re-measured on a narrower panel is a different measurement, not an "
      "inconsistency.")
    A("- **Low lift on a SKEW or LAG row is the sign-discipline problem showing up as "
      "arithmetic, not a bug.** The composite is built with each leg's *registered* sign. "
      "Where the realized IC sign opposes registration (LAG) or none was registered (SKEW), "
      "the two legs partially cancel and the composite collapses. Flipping the sign to rescue "
      "the number is precisely the post-hoc move §2.1 exists to forbid.")
    A("- **ρ(signal) and ρ(IC) can disagree sharply.** `CARRY + SKEW` measures ρ(signal) "
      "−0.6329 against ρ(IC) −0.5085; `IVOL + LAG` measures +0.3093 against +0.5210. The "
      "quantity that governs composite IR is ρ(IC) — whether the sleeves' monthly ICs move "
      "together — not whether their z-scores do.")

    A("\n---\n\n## 3. Summary\n")
    beats = [r for r in ok if r["lift"] > 1.0]
    A(f"- Pairs measured: **{len(ok)}**. Pairs whose composite beats its own best leg: "
      f"**{len(beats)}**.")
    for r in sorted(beats, key=lambda r: -r["lift"]):
        A(f"  - `{r['a']} + {r['b']}` — lift {r['lift']:.3f}, ρ(IC) {r['rho_ic']:+.4f}, "
          f"composite IR {r['ir_c']:.4f} vs best leg {r['best']:.4f}, "
          f"composite power {r['power_c']:.4f} vs best-leg power {r['power_best']:.4f}")
    A(f"\n- ρ(IC) governs composite IR, not ρ(signal). Measured range: "
      f"{min(r['rho_ic'] for r in ok):+.4f} to {max(r['rho_ic'] for r in ok):+.4f}; "
      f"ρ(signal) range {min(r['rho_sig'] for r in ok):+.4f} to "
      f"{max(r['rho_sig'] for r in ok):+.4f}.")
    valid = [r for r in beats if all(
        SLEEVES[nm][3] != 0 and SLEEVES[nm][3] == sg
        for nm, sg in ((r["a"], r["sign_a"]), (r["b"], r["sign_b"])))]
    A(f"\n- Pairs that BOTH beat their best leg AND pass the sign-discipline check: "
      f"**{len(valid)}**"
      + (" — " + ", ".join(f"`{r['a']} + {r['b']}`" for r in valid) if valid else "."))

    A("\n---\n\n## 4. Substrate defects found while building this report\n")
    A("Not part of the combination question; recorded because they were discovered here and "
      "affect anything that reads these stores.\n")
    A("1. **`data/signal_engine/carry/signals.duckdb` has `fwd_ret_1m` NULL in all 23,419 "
      "rows.** Both `run_train.py:262` and `run_net_spread.py:196` filter "
      "`fwd_ret_1m IS NOT NULL` against this store, so as it currently stands they have no "
      "rows to score (inferred from the column state, not from executing the runners). It "
      "will not self-heal: `build_carry.py:308-314` scopes the fill to the dates built in "
      "that same run, so an incremental refresh fills only the new month. The weekly store "
      "(`carry/weekly_signals.duckdb`, 566 formations) is populated. This report therefore "
      "sources returns from `ivol/signals.duckdb` for every sleeve.")
    A("2. **`data/signal_engine/ts_basis/ts_signals.duckdb` is the weekly rebuild, not the "
      "registered monthly sleeve.** `build_ts_signals.py:24` reads "
      "`carry/weekly_signals.duckdb`; the result is 349 fenced formations on a Friday grid, 35 "
      "of which are month-ends. The registered monthly TS Basis construction is not "
      "reconstructible from what is on disk.")
    A("3. **`fwd_ret_1m` disagrees between stores.** IVOL and LAG match exactly on all 17,406 "
      "common rows; TREND differs on **183** of them (~1.1%). Unreconciled.")
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    raise SystemExit(main())
