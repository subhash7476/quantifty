from datetime import date

from core.scheduler.eod_telegram import (
    TELEGRAM_LIMIT,
    format_chain_failure,
    format_download_success,
    format_options_book,
    format_stopped,
    truncate,
)

TODAY = date(2026, 7, 31)


def test_truncate_leaves_short_text_untouched():
    assert truncate("hello") == "hello"


def test_truncate_caps_at_telegram_limit_with_marker():
    out = truncate("x" * 5000)
    assert len(out) <= TELEGRAM_LIMIT
    assert out.endswith("… truncated")


def test_download_success_names_fresh_feeds():
    msg = format_download_success(
        {"equity": TODAY, "futures": TODAY, "stock_options": date(2026, 7, 30), "index": TODAY},
        TODAY, attempt=2)
    assert "2026-07-31" in msg
    assert "futures" in msg
    assert "stock_options" in msg  # stale feeds are reported too


def test_options_book_renders_each_contract_at_its_eod_close():
    contracts = [
        {"ticker": "RELIANCE", "direction": "LONG", "opt_type": "CE", "expiry": date(2026, 8, 27),
         "strike": 1500.0, "premium": 42.5, "premium_cost": 21250.0, "lot_size": 500},
        {"ticker": "INOXWIND", "direction": "SHORT", "opt_type": "PE", "expiry": date(2026, 8, 27),
         "strike": 72.5, "premium": 4.62, "premium_cost": 20790.0, "lot_size": 4500},
    ]
    msg = format_options_book(TODAY, contracts)
    assert "|z| = 3" in msg and "EOD close 2026-07-31" in msg
    assert "RELIANCE LONG CE 1500 exp 2026-08-27" in msg
    assert "close 42.50 x 500 = 21,250" in msg
    assert "INOXWIND SHORT PE 72.5 exp" in msg          # half strikes are not rounded away
    assert "Live prices" not in msg
    assert len(msg) <= TELEGRAM_LIMIT


def test_options_book_marks_skipped_contracts_with_the_reason():
    contracts = [{"ticker": "IDEA", "direction": "LONG", "opt_type": "CE", "expiry": None,
                  "strike": None, "premium": None, "premium_cost": None, "lot_size": None,
                  "screen_reason": "no trades within 3 strikes of ATM on 2026-07-31"}]
    msg = format_options_book(TODAY, contracts)
    assert "IDEA LONG CE — SKIP (no trades within 3 strikes of ATM on 2026-07-31)" in msg


def test_options_book_without_clamp_signals_says_so():
    assert format_options_book(TODAY, []) == "TS BASIS DAILY — 2026-07-31: no signals at |z| = 3"


def test_formatters_never_emit_markdown_control_chars_unescaped():
    # Plain-text mode: underscores in tickers must survive verbatim.
    contracts = [{"ticker": "M_M", "direction": "LONG", "opt_type": "CE", "expiry": date(2026, 8, 27),
                  "strike": 100.0, "premium": 1.0, "premium_cost": 100.0, "lot_size": 100}]
    assert "M_M" in format_options_book(TODAY, contracts)


def test_chain_failure_includes_step_and_tail():
    msg = format_chain_failure("refresh_all_strategies.py", "Traceback\nBoomError")
    assert "refresh_all_strategies.py" in msg
    assert "BoomError" in msg


def test_stopped_message_includes_outcome_and_reason():
    msg = format_stopped("holiday", "no feed published 2026-07-31", attempt=3)
    assert "holiday" in msg.lower()
    assert "no feed published" in msg
