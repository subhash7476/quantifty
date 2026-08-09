from datetime import datetime

from scripts.ops import preflight as pf


def _ctx(**over):
    base = dict(
        now=datetime(2026, 8, 11, 9, 30), market_open=True, stop_file_present=False,
        has_token=True, token_expired=False,
        marks_rows=120, marks_priceable=118, marks_heartbeat_age_s=5.0,
        poller_alive=True, ingestor_alive=True, vix_last_bar_age_s=30.0,
        span_present=True, master_age_days=0.2,
        feed_fresh={"equity": True, "futures": True, "stock_options": True, "index": True},
        eod_worker_alive=True,
    )
    base.update(over)
    return pf.PreflightContext(**base)


def test_token_blocks_when_expired():
    assert pf.check_token(_ctx(token_expired=True)).ok is False


def test_token_blocks_when_absent():
    assert pf.check_token(_ctx(has_token=False)).ok is False


def test_stop_file_blocks():
    assert pf.check_stop_file(_ctx(stop_file_present=True)).ok is False


def test_marks_block_when_no_priceable_rows_during_market_hours():
    # rows>0 but every ltp==0 → reader yields {} → BLOCK
    assert pf.check_marks(_ctx(marks_rows=120, marks_priceable=0)).ok is False


def test_marks_block_when_heartbeat_stale_during_market_hours():
    assert pf.check_marks(_ctx(marks_heartbeat_age_s=600.0)).ok is False


def test_marks_preopen_only_requires_poller_alive():
    ctx = _ctx(market_open=False, marks_rows=0, marks_priceable=0,
               marks_heartbeat_age_s=None, poller_alive=True)
    assert pf.check_marks(ctx).ok is True


def test_vix_blocks_when_bar_stale_during_market_hours():
    assert pf.check_vix(_ctx(vix_last_bar_age_s=900.0)).ok is False


def test_vix_preopen_only_requires_ingestor_alive():
    ctx = _ctx(market_open=False, vix_last_bar_age_s=None, ingestor_alive=True)
    assert pf.check_vix(ctx).ok is True


def test_all_block_checks_pass_on_healthy_context():
    ctx = _ctx()
    for fn in (pf.check_token, pf.check_stop_file, pf.check_marks, pf.check_vix):
        assert fn(ctx).ok is True
        assert fn(ctx).tier == "block"


def test_warn_checks_flag_but_do_not_block():
    ctx = _ctx(span_present=False, master_age_days=5.0,
               feed_fresh={"equity": False, "futures": True,
                           "stock_options": True, "index": True},
               eod_worker_alive=False)
    results = pf.run_preflight(ctx)
    # Every WARN failure is present but the verdict is still GO (blocks all pass).
    warn_fail = [r for r in results if r.tier == "warn" and not r.ok]
    assert {r.name for r in warn_fail} == {"span", "instrument_master",
                                           "eod_feeds", "eod_worker"}
    assert pf.verdict(results) == "GO"


def test_verdict_no_go_on_any_block_failure():
    results = pf.run_preflight(_ctx(token_expired=True))
    assert pf.verdict(results) == "NO-GO"


def test_run_preflight_returns_all_eight_checks():
    assert len(pf.run_preflight(_ctx())) == 8
