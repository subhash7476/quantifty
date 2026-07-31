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


def test_options_book_renders_one_line_per_contract():
    contracts = [
        {"ticker": "RELIANCE", "direction": "LONG", "opt_type": "CE", "expiry": date(2026, 8, 27),
         "strike": 1500.0, "settle": 42.5, "premium_cost": 21250.0, "lot_size": 500,
         "screen": "ok", "screen_reason": "", "instrument_key": "NSE_FO|1234"},
        {"ticker": "TCS", "direction": "SHORT", "opt_type": "PE", "expiry": date(2026, 8, 27),
         "strike": 3200.0, "settle": 55.0, "premium_cost": 9350.0, "lot_size": 170,
         "screen": "ok", "screen_reason": "", "instrument_key": "NSE_FO|5678"},
    ]
    msg = format_options_book(TODAY, contracts)
    assert "RELIANCE" in msg and "TCS" in msg
    assert "CE" in msg and "PE" in msg
    assert len(msg) <= TELEGRAM_LIMIT


def test_options_book_marks_untradeable_contracts():
    contracts = [{"ticker": "IDEA", "direction": "LONG", "opt_type": "CE", "expiry": None,
                  "strike": None, "settle": None, "premium_cost": None, "lot_size": None,
                  "screen": "no_tradeable_strike", "screen_reason": "spread 12%",
                  "instrument_key": None}]
    msg = format_options_book(TODAY, contracts)
    assert "IDEA" in msg
    assert "spread 12%" in msg


def test_options_book_handles_empty_book():
    msg = format_options_book(TODAY, [])
    assert "no contracts" in msg.lower()


def test_formatters_never_emit_markdown_control_chars_unescaped():
    # Plain-text mode: underscores in tickers must survive verbatim.
    contracts = [{"ticker": "M_M", "direction": "LONG", "opt_type": "CE", "expiry": date(2026, 8, 27),
                  "strike": 100.0, "settle": 1.0, "premium_cost": 100.0, "lot_size": 100,
                  "screen": "ok", "screen_reason": "", "instrument_key": "k"}]
    assert "M_M" in format_options_book(TODAY, contracts)


def test_chain_failure_includes_step_and_tail():
    msg = format_chain_failure("refresh_all_strategies.py", "Traceback\nBoomError")
    assert "refresh_all_strategies.py" in msg
    assert "BoomError" in msg


def test_stopped_message_includes_outcome_and_reason():
    msg = format_stopped("holiday", "no feed published 2026-07-31", attempt=3)
    assert "holiday" in msg.lower()
    assert "no feed published" in msg
