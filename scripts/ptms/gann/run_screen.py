"""PTMS Gann Stage-1 screen — guarded entry point (freeze §10, §13, §14, §18). NOT RUN AT COMMIT.

Two phases, in this order, each refusing to start unless the guard passes:

    python -m scripts.ptms.gann.run_screen size-check [--workers N]
    python -m scripts.ptms.gann.run_screen screen [--workers N]

Guard (both phases), all checked against **committed** content:
1. Checklist item 18 records the frozen document's path, its freeze commit and its SHA-256, written as
   `docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT….md`, commit `<hex>`, SHA-256 `<64 hex>`.
2. The SHA-256 of that file's git blob at that commit equals the recorded digest (the blob, never the
   working-tree file: line-ending conversion would change the bytes), the file is unchanged at HEAD,
   and the freeze commit is an ancestor of HEAD.
3. Register row G-S1 is present in the committed exposure register and carries the digest (§15).
4. The screen code, the checklist, the register and the frozen document are clean in the working tree.

Order (§10, G-9): `size-check` reads the real panel only to resample it. It computes no real statistic,
writes the size-check record and stops. `screen` refuses unless that record is **committed**, matches
the digest and the panel, and covers all 200 panels. A construct whose rejection rate exceeds 2α is not
screened (G-9b): none of its real statistics is computed.

Long runs checkpoint to data/ptms/gann_stage1/<digest>/. Every unit is fixed by its seed, so resuming
reproduces the same numbers. A panel on which T_c is undefined stops the run (`rank_p` raises); the
freeze does not provide for it, so it goes to the operator, not to a patch.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ptms.gann import report, robustness, surrogate  # noqa: E402
from scripts.ptms.gann.constants import (ALPHA, MEAN_BLOCK, N_SURROGATES, SIZE_CHECK_MAX_REJECTION,  # noqa: E402
                                         SIZE_CHECK_PANELS)
from scripts.ptms.gann.panel import G7_CSV, load_panel  # noqa: E402
from scripts.ptms.gann.pipeline import (CONSTRUCTS, CONTRAST_LEGS, Context, facts, gf1_obs, gf10_obs,  # noqa: E402
                                        gf4_obs, panel_stats, surrogate_stats)
from scripts.ptms.gann.scores import (gf1_placebo_residue_sets, gf1_score_fn, gf4_placebo_window_sets,  # noqa: E402
                                      window_score_fn)
from scripts.ptms.gann.stats import effect_size, rank_p, t_c  # noqa: E402

CHECKLIST = "docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md"
REGISTER = "governance/exposure/RESEARCH_EXPOSURE_REGISTER.md"
CODE_DIR = "scripts/ptms/gann"
SCRIPT = "scripts/ptms/gann/run_screen.py"
SIZE_RECORD = "docs/reports/ptms/PTMS_GANN_STAGE1_SIZE_CHECK.json"
RESULTS = "docs/reports/ptms/PTMS_GANN_STAGE1_SCREEN_RESULTS.json"
REPORT = "docs/reports/ptms/PTMS_GANN_STAGE1_SCREEN_REPORT.md"
CHECKPOINTS = ROOT / "data" / "ptms" / "gann_stage1"
P2_COMMIT = "156a2ce"
CHUNK = 25

FREEZE_PATH_RE = re.compile(r"`(docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT[^`]*\.md)`")
COMMIT_RE = re.compile(r"commit `([0-9a-f]{7,40})`")
DIGEST_RE = re.compile(r"SHA-256 `([0-9a-f]{64})`")


@dataclass(frozen=True)
class Freeze:
    path: str
    commit: str
    digest: str
    text: str
    head: str
    g_s1_date: str


def _git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout


def _refuse(msg):
    raise SystemExit(f"run_screen refuses: {msg}")


def _one(values, what):
    values = sorted(set(values))
    if len(values) != 1:
        _refuse(f"checklist item 18 must record exactly one {what}; found {len(values)}")
    return values[0]


def guard(root=ROOT):
    head = _git(root, "rev-parse", "HEAD").decode().strip()
    checklist = _git(root, "show", f"HEAD:{CHECKLIST}").decode("utf-8")
    rows = [line for line in checklist.splitlines() if line.startswith("| 18 |")]
    if len(rows) != 1:
        _refuse("checklist item 18 not found")
    path = _one(FREEZE_PATH_RE.findall(rows[0]), "freeze document path")
    commit = _one(COMMIT_RE.findall(rows[0]), "freeze commit")
    digest = _one(DIGEST_RE.findall(rows[0]), "SHA-256 digest")
    try:
        blob = _git(root, "show", f"{commit}:{path}")
    except subprocess.CalledProcessError:
        _refuse(f"{path} does not exist at commit {commit}")
    if hashlib.sha256(blob).hexdigest() != digest:
        _refuse("the frozen document's SHA-256 at the freeze commit does not match checklist item 18")
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", commit, head]).returncode:
        _refuse("the freeze commit is not an ancestor of HEAD")
    if _git(root, "rev-parse", f"HEAD:{path}") != _git(root, "rev-parse", f"{commit}:{path}"):
        _refuse("the frozen document changed after the freeze commit")
    register = _git(root, "show", f"HEAD:{REGISTER}").decode("utf-8")
    g_s1 = [line for line in register.splitlines() if line.startswith("| G-S1 |")]
    if len(g_s1) != 1 or digest not in g_s1[0]:
        _refuse("register row G-S1 is missing, duplicated, or does not carry the freeze digest")
    dirty = _git(root, "status", "--porcelain", "--", CODE_DIR, CHECKLIST, REGISTER, path).decode().strip()
    if dirty:
        _refuse(f"uncommitted changes: {dirty}")
    added = _git(root, "log", "-S", "| G-S1 |", "--reverse", "--format=%cs", "--", REGISTER).decode().split()
    return Freeze(path, commit, digest, blob.decode("utf-8"), head, added[0] if added else "unknown")


# ---------------------------------------------------------------------------------------------
# Worker processes (Windows spawn: the panel is shipped once per worker)
# ---------------------------------------------------------------------------------------------

_W = {}


def _init(ctx, high, low, close):
    _W.update(ctx=ctx, high=high, low=low, close=close)


def _tc_dict(stats):
    return {k: asdict(v) for k, v in stats.items()}


def _size_one(p):
    """Pseudo-real panel p (G-9a): drawn from the real panel with stream size[p]; its B inner surrogates
    come from size[p].spawn(B), drawn from the pseudo-real panel itself (RR-8b)."""
    seq = surrogate.streams()["size"][p]
    ph, pl, pc = surrogate.surrogate_panel(_W["high"], _W["low"], _W["close"], np.random.default_rng(seq))
    ctx = _W["ctx"]
    t_obs = panel_stats(ctx, ph, pl, keys=CONSTRUCTS)[0]
    inner = surrogate_stats(ctx, ph, pl, pc, seq.spawn(N_SURROGATES), keys=CONSTRUCTS)
    return p, {c: _p(t_obs[c].value, [s[c].value for s in inner], f"size check panel {p} {c}") for c in CONSTRUCTS}


def _sur_chunk(job):
    stream, start, stop, keys = job
    seeds = surrogate.streams()["real"] if stream == "real" else surrogate.streams()["blocks"][stream]
    mean_block = MEAN_BLOCK if stream == "real" else stream
    out = surrogate_stats(_W["ctx"], _W["high"], _W["low"], _W["close"], seeds[start:stop], mean_block, keys)
    return job, [_tc_dict(s) for s in out]


# ---------------------------------------------------------------------------------------------
# Phases
# ---------------------------------------------------------------------------------------------

def panel_sha(panel):
    h = hashlib.sha256()
    h.update(json.dumps([str(d) for d in panel.cal.sessions] + list(panel.entities)).encode())
    for a in (panel.high, panel.low, panel.close, panel.close_raw, panel.member):
        h.update(np.ascontiguousarray(a).tobytes())
    for ex in panel.g7_ord:
        h.update(ex.tobytes() + b"|")
    return h.hexdigest()


def _checkpoint_dir(fz, sha, name):
    d = CHECKPOINTS / f"{fz.digest[:16]}_{sha[:16]}" / name
    d.mkdir(parents=True, exist_ok=True)
    return d


class _InProcess:
    """--workers 1: the same jobs, run in this process."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def map(self, fn, jobs):
        return map(fn, jobs)


def _pool(panel, workers):
    args = (Context.of(panel), panel.high, panel.low, panel.close)
    if workers <= 1:
        _init(*args)
        return _InProcess()
    return ProcessPoolExecutor(workers, initializer=_init, initargs=args)


def run_size_check(fz, workers):
    panel = load_panel()
    sha = panel_sha(panel)
    ck = _checkpoint_dir(fz, sha, "size")
    todo = [p for p in range(SIZE_CHECK_PANELS) if not (ck / f"{p:03d}.json").exists()]
    with _pool(panel, workers) as ex:
        for p, pv in ex.map(_size_one, todo):
            (ck / f"{p:03d}.json").write_text(json.dumps(pv), encoding="utf-8")
            print(f"size check panel {p}: {pv}", flush=True)
    pvals = [json.loads((ck / f"{p:03d}.json").read_text(encoding="utf-8")) for p in range(SIZE_CHECK_PANELS)]
    constructs = {}
    for c in CONSTRUCTS:
        n_reject = sum(pv[c] <= ALPHA for pv in pvals)
        rate = n_reject / SIZE_CHECK_PANELS
        constructs[c] = {"n_panels": SIZE_CHECK_PANELS, "n_reject": n_reject, "rate": rate,
                         "passed": rate <= SIZE_CHECK_MAX_REJECTION, "p_values": [pv[c] for pv in pvals]}
    record = {"freeze_path": fz.path, "freeze_commit": fz.commit, "digest": fz.digest, "head": fz.head,
              "panel_sha256": sha, "constructs": constructs}
    (ROOT / SIZE_RECORD).write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"size-check record written to {SIZE_RECORD}. Commit it before running `screen`.")


def _committed_size_record(fz, root=ROOT):
    try:
        rec = json.loads(_git(root, "show", f"HEAD:{SIZE_RECORD}"))
    except subprocess.CalledProcessError:
        _refuse("the size-check record is not committed; run `size-check` and commit its record first")
    if _git(root, "status", "--porcelain", "--", SIZE_RECORD).strip():
        _refuse("the size-check record has uncommitted changes")
    if rec["digest"] != fz.digest:
        _refuse("the size-check record belongs to a different freeze digest")
    if any(len(rec["constructs"][c]["p_values"]) != SIZE_CHECK_PANELS for c in CONSTRUCTS):
        _refuse("the size-check record does not cover all 200 pseudo-real panels")
    return rec


def _surrogate_runs(fz, sha, panel, workers, keys):
    """{stream: [per-panel {key: Tc dict}]} for the real B (mean block 20) and V-B5 / V-B60."""
    ck = _checkpoint_dir(fz, sha, "surrogates")
    jobs = [(stream, s, min(s + CHUNK, N_SURROGATES), keys if stream == "real" else
             tuple(k for k in keys if k in CONSTRUCTS))
            for stream in ("real", 5, 60) for s in range(0, N_SURROGATES, CHUNK)]
    name = lambda j: ck / f"{j[0]}_{j[1]:04d}.json"
    todo = [j for j in jobs if not name(j).exists()]
    with _pool(panel, workers) as ex:
        for job, out in ex.map(_sur_chunk, todo):
            name(job).write_text(json.dumps(out), encoding="utf-8")
            print(f"surrogates {job[0]} {job[1]}-{job[2]}", flush=True)
    runs = {"real": [], 5: [], 60: []}
    for j in jobs:
        runs[j[0]] += json.loads(name(j).read_text(encoding="utf-8"))
    return runs


def _values(runs, key):
    return [s[key]["value"] for s in runs]


def _p(observed, null, what):
    try:
        return rank_p(observed, null)
    except ValueError as e:
        raise SystemExit(f"{what}: {e}. The freeze does not provide for this; stop and ask the operator.")


def run_screen(fz, workers):
    rec = _committed_size_record(fz)
    panel = load_panel()
    sha = panel_sha(panel)
    if sha != rec["panel_sha256"]:
        _refuse("the panel read now differs from the panel the size check read")
    screened = tuple(c for c in CONSTRUCTS if rec["constructs"][c]["passed"])
    keys = screened + (CONTRAST_LEGS if "GF-10" in screened else ())
    runs = _surrogate_runs(fz, sha, panel, workers, keys)

    ctx = Context.of(panel)
    H, L = panel.high, panel.low
    f = facts(H, L)
    W = ctx.n_weeks
    real = panel_stats(ctx, H, L, keys=keys)[0] if keys else {}
    first_bar = np.argmax(~np.isnan(panel.close), axis=0)
    obs = {}
    if "GF-1" in screened:
        obs["GF-1"] = gf1_obs(ctx, H, L, f)
    if "GF-4T/R8" in screened:
        obs["GF-4T/R8"] = gf4_obs(ctx, H, L, f)
    if "GF-10" in screened:
        obs["GF-10"], contrast = gf10_obs(ctx, H, L, f)

    constructs = {}
    for c in CONSTRUCTS:
        if c not in screened:
            constructs[c] = {"status": "stopped", "outcome_row": 3}
            continue
        o, tc = obs[c], real[c]
        sur = _values(runs["real"], c)
        p_sur = _p(tc.value, sur, f"{c} p_sur")
        eff, interval = effect_size(tc.value, sur)
        undefined = {"primary": {"real": tc.n_dropped_undefined,
                                 "surrogate_median": float(np.median([s[c]["n_dropped_undefined"] for s in runs["real"]]))}}
        pn = {"n_obs": int(o.week.size), "n_open_m": o.n_excluded_open_m, "n_g7": o.n_excluded_g7,
              "undefined_ic": undefined, "exclusion_loss": robustness.d_bh(o, W, gf10=c == "GF-10")}
        entry = {"status": "screened", "T_c": asdict(tc), "p_sur": p_sur, "effect": eff, "interval": interval}
        if c in ("GF-1", "GF-4T/R8"):
            plac = ([gf1_obs(ctx, H, L, f, gf1_score_fn(s)) for _, s in gf1_placebo_residue_sets()] if c == "GF-1"
                    else [gf4_obs(ctx, H, L, f, window_score_fn(s)) for _, s in gf4_placebo_window_sets()])
            plac_tc = [t_c(q.week, q.score, q.y, W) for q in plac]
            entry["spec_p"] = _p(tc.value, [q.value for q in plac_tc], f"{c} p_plac")
            undefined["placebo family (median over sets)"] = {
                "real": float(np.median([q.n_dropped_undefined for q in plac_tc])), "surrogate_median": "n/a"}
        else:
            t_time, t_price = real["GF-10 time"], real["GF-10 price"]
            delta = t_time.value - t_price.value
            null = [a - b for a, b in zip(_values(runs["real"], "GF-10 time"), _values(runs["real"], "GF-10 price"))]
            entry["spec_p"] = _p(delta, null, "GF-10 contrast")
            entry["contrast"] = {"time": asdict(t_time), "price": asdict(t_price), "delta": delta}
            pn["n_open_n"] = contrast.n_excluded_open_n
            for leg in CONTRAST_LEGS:
                undefined[leg] = {"real": real[leg].n_dropped_undefined, "surrogate_median": float(
                    np.median([s[leg]["n_dropped_undefined"] for s in runs["real"]]))}
        entry["panel"] = pn
        entry["outcome_row"] = report.outcome_row(True, p_sur, entry["spec_p"])
        constructs[c] = entry

    variants = {}
    for c, vs in robustness.variants(ctx, H, L, f, constructs=screened).items():
        med = float(np.median(_values(runs["real"], c)))
        variants[c] = {name: {"T_c": asdict(v), "effect": v.value - med} for name, v in vs.items()}
        for b in (5, 60):
            sur_b = _values(runs[b], c)
            variants[c][f"V-B{b}"] = {"T_c": asdict(real[c]), "effect": effect_size(real[c].value, sur_b)[0],
                                      "p_sur": _p(real[c].value, sur_b, f"{c} V-B{b}")}

    diagnostics = {"D-PL": {}, "D-PS": {}}
    for c, o in obs.items():
        pl = robustness.d_pl(o, ctx.week_last_idx, panel.close_raw, W)
        diagnostics["D-PL"][c] = {"low": asdict(pl["low"]), "high": asdict(pl["high"]), "n_no_bar": pl["n_no_bar"]}
        summary, stocks = robustness.d_ps(o, panel.entities)
        diagnostics["D-PS"][c] = {"summary": summary, "stocks": stocks}
    if "GF-1" in obs:
        diagnostics["D-AA"] = {k: asdict(v) for k, v in
                               robustness.d_aa(obs["GF-1"], ctx.ords, ctx.week_last_idx, first_bar, W).items()}

    results = {
        "provenance": {"freeze_path": fz.path, "digest": fz.digest, "freeze_commit": fz.commit, "head": fz.head,
                       "g_s1_date": fz.g_s1_date, "script": SCRIPT, "size_record": SIZE_RECORD,
                       "g7_csv_sha256": hashlib.sha256(Path(G7_CSV).read_bytes()).hexdigest(),
                       "p2_commit": P2_COMMIT, "panel_sha256": sha},
        "size_check": {c: {k: v for k, v in rec["constructs"][c].items() if k != "p_values"} for c in CONSTRUCTS},
        "constructs": constructs, "variants": variants, "diagnostics": diagnostics,
    }
    if "GF-10" in obs:
        sz = obs["GF-10"].sz
        results["gf10_structural_zeros"] = {"U_T empty": int((sz == 1).sum()), "after the event": int((sz == 2).sum())}
    (ROOT / RESULTS).write_text(json.dumps(results, indent=1, default=float), encoding="utf-8")
    (ROOT / REPORT).write_text(report.render(results, report.fixed_text(fz.text)), encoding="utf-8")
    print(f"results written to {RESULTS} and {REPORT}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("phase", choices=("size-check", "screen"))
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    fz = guard()
    (run_size_check if args.phase == "size-check" else run_screen)(fz, args.workers)


if __name__ == "__main__":
    main()
