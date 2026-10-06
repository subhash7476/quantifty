from datetime import date

import pytest

from scripts.gex_xs_5d import run_stage as R


def test_frozen_sha_ignores_section_14_appends_and_crlf():
    body = "# Doc\n\nrules\n\n## 14. Post-freeze change log\n\n*(empty)*\n"
    a = R.frozen_sha_of_bytes(body.encode())
    b = R.frozen_sha_of_bytes((body + "\n- 2026-10-07 fix\n").encode())
    c = R.frozen_sha_of_bytes(body.replace("\n", "\r\n").encode())
    assert a == b == c
    assert a != R.frozen_sha_of_bytes(body.replace("rules", "rulez").encode())


def test_frozen_sha_requires_section_14_heading():
    with pytest.raises(R.GuardError):
        R.frozen_sha_of_bytes(b"# Doc without the heading\n")


def test_pinned_frozen_sha_matches_the_committed_prereg():
    R.check_prereg(R.PREREG)


def test_dev_stage_refuses_sealed_dates():
    with pytest.raises(R.GuardError):
        R.check_stage_dates("dev", [date(2022, 12, 30), date(2023, 1, 2)])
    R.check_stage_dates("dev", [date(2022, 12, 30)])
    with pytest.raises(R.GuardError):
        R.check_stage_dates("sealed", [date(2022, 12, 30)])


def test_sealed_requires_dev_pass(tmp_path):
    rep = tmp_path / "dev.md"
    with pytest.raises(R.GuardError):
        R.check_dev_passed(rep)
    rep.write_text("# x\n\n**DEV verdict: FAIL**\n", encoding="utf-8")
    with pytest.raises(R.GuardError):
        R.check_dev_passed(rep)
    rep.write_text("# x\n\n**DEV verdict: PASS**\n", encoding="utf-8")
    R.check_dev_passed(rep)


def test_report_is_never_overwritten(tmp_path):
    rep = tmp_path / "r.md"
    R.check_report_absent(rep)
    rep.write_text("x", encoding="utf-8")
    with pytest.raises(R.GuardError):
        R.check_report_absent(rep)


def test_verdict_rule():
    assert R.verdict({"mean": -0.02, "p_one_sided": 0.01}) == "PASS"
    assert R.verdict({"mean": -0.02, "p_one_sided": 0.06}) == "FAIL"
    assert R.verdict({"mean": 0.02, "p_one_sided": 0.01}) == "FAIL"
