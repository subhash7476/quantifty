"""Entry-point guard, size-record gate and report rendering. No store is read: `load_panel` is replaced
by a tripwire, and the guard is exercised on the real repository (where it must refuse) and on a
throwaway git repository."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from scripts.ptms.gann import report, run_screen
from scripts.ptms.gann.constants import SIZE_CHECK_PANELS

DRAFT = Path(run_screen.ROOT) / "docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md"
FREEZE = "docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_TEST.md"


@pytest.fixture
def tripwire(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("load_panel reached")
    monkeypatch.setattr(run_screen, "load_panel", boom)


def test_guard_refuses_on_the_current_repository(tripwire):
    with pytest.raises(SystemExit, match="refuses"):
        run_screen.main(["size-check"])
    with pytest.raises(SystemExit, match="refuses"):
        run_screen.main(["screen"])


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@t", "-c",
                           "core.autocrlf=false", *args], capture_output=True, check=True).stdout.decode().strip()


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(text.encode("utf-8"))


def frozen_repo(tmp_path, register_digest=None, record=True):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    write(root, FREEZE, "frozen protocol\r\nline two\r\n")
    write(root, run_screen.CODE_DIR + "/x.py", "x = 1\n")
    write(root, run_screen.CHECKLIST, "| 18 | freeze | pending |\n")
    write(root, run_screen.REGISTER, "| # | Surface |\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "freeze")
    commit = git(root, "rev-parse", "HEAD")
    digest = hashlib.sha256((root / FREEZE).read_bytes()).hexdigest()
    if record:
        write(root, run_screen.CHECKLIST, f"| 18 | freeze | `{FREEZE}`, commit `{commit[:10]}`, SHA-256 `{digest}` |\n")
        write(root, run_screen.REGISTER, f"| # | Surface |\n| G-S1 | Equity EOD | `{FREEZE}` + SHA-256 "
                                         f"{register_digest or digest} |\n")
        git(root, "commit", "-q", "-am", "record digest and G-S1")
    return root, commit, digest


def test_guard_passes_when_everything_is_recorded(tmp_path):
    root, commit, digest = frozen_repo(tmp_path)
    fz = run_screen.guard(root)
    assert (fz.path, fz.digest, fz.commit) == (FREEZE, digest, commit[:10])
    assert fz.text == "frozen protocol\r\nline two\r\n"                       # the committed bytes
    assert fz.g_s1_date != "unknown"


def test_guard_refuses_without_a_recorded_digest(tmp_path):
    root, _, _ = frozen_repo(tmp_path, record=False)
    with pytest.raises(SystemExit, match="exactly one freeze document path"):
        run_screen.guard(root)


def test_guard_refuses_a_g_s1_row_without_the_digest(tmp_path):
    root, _, _ = frozen_repo(tmp_path, register_digest="0" * 64)
    with pytest.raises(SystemExit, match="G-S1"):
        run_screen.guard(root)


def test_guard_refuses_an_edit_to_the_frozen_document(tmp_path):
    root, _, _ = frozen_repo(tmp_path)
    write(root, FREEZE, "frozen protocol\r\nline two edited\r\n")
    git(root, "commit", "-q", "-am", "edit")
    with pytest.raises(SystemExit, match="changed after the freeze"):
        run_screen.guard(root)


def test_guard_refuses_a_wrong_digest(tmp_path):
    root, commit, digest = frozen_repo(tmp_path)
    bad = "f" * 64
    write(root, run_screen.CHECKLIST, f"| 18 | freeze | `{FREEZE}`, commit `{commit}`, SHA-256 `{bad}` |\n")
    write(root, run_screen.REGISTER, f"| G-S1 | x | SHA-256 {bad} |\n")
    git(root, "commit", "-q", "-am", "wrong digest")
    with pytest.raises(SystemExit, match="does not match"):
        run_screen.guard(root)


def test_guard_refuses_uncommitted_screen_code(tmp_path):
    root, _, _ = frozen_repo(tmp_path)
    write(root, run_screen.CODE_DIR + "/x.py", "x = 2\n")
    with pytest.raises(SystemExit, match="uncommitted"):
        run_screen.guard(root)


def test_screen_refuses_without_a_committed_complete_size_record(tmp_path):
    root, _, _ = frozen_repo(tmp_path)
    fz = run_screen.guard(root)
    with pytest.raises(SystemExit, match="not committed"):
        run_screen._committed_size_record(fz, root)
    rec = {"digest": fz.digest, "constructs": {c: {"p_values": [0.5] * (SIZE_CHECK_PANELS - 1)}
                                               for c in ("GF-1", "GF-4T/R8", "GF-10")}}
    write(root, run_screen.SIZE_RECORD, json.dumps(rec))
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "size record")
    with pytest.raises(SystemExit, match="all 200"):
        run_screen._committed_size_record(fz, root)
    for c in rec["constructs"].values():
        c["p_values"].append(0.5)
    write(root, run_screen.SIZE_RECORD, json.dumps(rec))
    with pytest.raises(SystemExit, match="uncommitted"):
        run_screen._committed_size_record(fz, root)
    git(root, "commit", "-q", "-am", "complete")
    assert run_screen._committed_size_record(fz, root)["digest"] == fz.digest


# ---- report ----

def tc(v, n=100):
    return {"value": v, "n_dates": n, "n_dropped_floor": 2, "n_dropped_undefined": 1}


def results(p_sur=0.3, spec_p=0.5, stopped=()):
    constructs, variants = {}, {}
    for c in ("GF-1", "GF-4T/R8", "GF-10"):
        if c in stopped:
            constructs[c] = {"status": "stopped", "outcome_row": 3}
            continue
        panel = {"n_obs": 5000, "n_open_m": 3, "n_g7": 40,
                 "undefined_ic": {"primary": {"real": 1, "surrogate_median": 1.0}},
                 "exclusion_loss": {"base": 6000, "limbs": {"G-7": 40, "entering": 5960},
                                    "shares": {"G-7": 40 / 6000, "entering": 5960 / 6000}}}
        constructs[c] = {"status": "screened", "T_c": tc(0.01), "p_sur": p_sur, "spec_p": spec_p, "effect": 0.002,
                         "interval": [-0.01, 0.012], "panel": panel,
                         "outcome_row": report.outcome_row(True, p_sur, spec_p)}
        variants[c] = {"V-K3": {"T_c": tc(0.0), "effect": -0.001},
                       "V-B5": {"T_c": tc(0.01), "effect": 0.001, "p_sur": 0.2}}
    if "GF-10" not in stopped:
        constructs["GF-10"]["contrast"] = {"time": tc(0.02), "price": tc(0.01), "delta": 0.01}
        constructs["GF-10"]["panel"]["n_open_n"] = 7
    return {
        "provenance": {"freeze_path": FREEZE, "digest": "a" * 64, "freeze_commit": "abc1234", "head": "def5678",
                       "g_s1_date": "2026-09-20", "script": run_screen.SCRIPT, "size_record": run_screen.SIZE_RECORD,
                       "g7_csv_sha256": "b" * 64, "p2_commit": "156a2ce", "panel_sha256": "c" * 64},
        "size_check": {c: {"n_panels": 200, "n_reject": 9 if c in stopped else 3,
                           "rate": (9 if c in stopped else 3) / 200, "passed": c not in stopped}
                       for c in ("GF-1", "GF-4T/R8", "GF-10")},
        "constructs": constructs, "variants": variants,
        "diagnostics": {"D-PL": {c: {"low": tc(0.0), "high": tc(0.01), "n_no_bar": 0} for c in variants},
                        "D-PS": {c: {"summary": {"n_stocks": 1, "n_undefined": 0, "median": 0.1, "q1": 0.1,
                                                 "q3": 0.1, "share_positive": 1.0},
                                     "stocks": [["INFY", 6, 30, 0.1]]} for c in variants},
                        "D-AA": {"< 144": tc(0.0), "144-288": tc(0.0), ">= 288": tc(0.0)}},
        "gf10_structural_zeros": {"U_T empty": 11, "after the event": 22},
    }


def fixed():
    return report.fixed_text(DRAFT.read_text(encoding="utf-8"))


def test_outcome_rule():
    a = 0.05 / 3
    assert report.outcome_row(True, a + 1e-9, 0.0) == 0
    assert report.outcome_row(True, a, a + 1e-9) == 1
    assert report.outcome_row(True, a, a) == 2
    assert report.outcome_row(False, 0.0, 0.0) == 3


def test_report_carries_the_fixed_text_verbatim_and_fills_every_placeholder():
    fx = fixed()
    text = report.render(results(), fx)
    assert "{{" not in text
    assert all(s in text for s in fx["F"])
    assert text.count(fx["A2"][0]) == 3                  # every construct retired on the surrogate leg
    assert "(`11`)" in text and "(`22`)" in text          # X-1 counts
    assert text.startswith("# PTMS")


def test_report_wording_follows_the_rule_and_stopped_constructs():
    fx = fixed()
    text = report.render(results(p_sur=0.001, spec_p=0.001, stopped=("GF-10",)), fx)
    assert text.count(fx["A2"][2]) == 2 and fx["A2"][3] in text and fx["A2"][0] not in text


def test_forbidden_phrasing_in_generated_text_fails():
    res = results()
    res["diagnostics"]["D-PS"]["GF-1"]["stocks"] = [["this works", 6, 30, 0.1]]
    with pytest.raises(AssertionError, match="A.5"):
        report.render(res, fixed())


# ---- both phases end to end, in process, on a synthetic panel with B and the panel count shrunk ----

def test_size_check_then_screen_end_to_end_on_a_synthetic_panel(tmp_path, monkeypatch):
    from tests.ptms.test_gann_robustness import synthetic_panel
    from scripts.ptms.gann import surrogate

    panel = synthetic_panel(7, T=700, N=160)
    for mod in (surrogate, run_screen):
        monkeypatch.setattr(mod, "N_SURROGATES", 4)
        monkeypatch.setattr(mod, "SIZE_CHECK_PANELS", 3)
    monkeypatch.setattr(run_screen, "load_panel", lambda: panel)
    monkeypatch.setattr(run_screen, "ROOT", tmp_path)
    monkeypatch.setattr(run_screen, "CHECKPOINTS", tmp_path / "ck")
    (tmp_path / "docs/reports/ptms").mkdir(parents=True)
    fz = run_screen.Freeze(FREEZE, "abc1234", "d" * 64, DRAFT.read_text(encoding="utf-8"), "def5678", "2026-09-20")

    run_screen.run_size_check(fz, workers=1)
    rec = json.loads((tmp_path / run_screen.SIZE_RECORD).read_text(encoding="utf-8"))
    assert all(len(rec["constructs"][c]["p_values"]) == 3 for c in rec["constructs"])
    assert not (tmp_path / run_screen.RESULTS).exists()                       # no real statistic yet

    run_screen.run_size_check(fz, workers=1)                                  # resumes from checkpoints
    assert json.loads((tmp_path / run_screen.SIZE_RECORD).read_text(encoding="utf-8")) == rec

    rec["constructs"]["GF-4T/R8"]["passed"] = False                            # G-9b: stop one construct
    monkeypatch.setattr(run_screen, "_committed_size_record", lambda fz_, root=None: rec)
    monkeypatch.setattr(run_screen, "SIZE_CHECK_MAX_REJECTION", 1.0)
    run_screen.run_screen(fz, workers=1)
    res = json.loads((tmp_path / run_screen.RESULTS).read_text(encoding="utf-8"))
    assert res["constructs"]["GF-4T/R8"] == {"status": "stopped", "outcome_row": 3}
    assert "GF-4T/R8" not in res["variants"] and "GF-4T/R8" not in res["diagnostics"]["D-PL"]
    g1 = res["constructs"]["GF-1"]
    assert g1["p_sur"] in {k / 5 for k in range(1, 6)} and 1 / 133 <= g1["spec_p"] <= 1
    assert set(res["variants"]["GF-1"]) >= {"V-B5", "V-B60", "V1-MD", "V-K3"}
    assert "contrast" in res["constructs"]["GF-10"]
    text = (tmp_path / run_screen.REPORT).read_text(encoding="utf-8")
    assert "{{" not in text and "Size check failed" in text
