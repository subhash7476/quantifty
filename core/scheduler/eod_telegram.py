"""Telegram delivery for the EOD job.

Deliberately does NOT use TelegramNotifier.send_message: that dispatches on a
daemon thread and returns, so a message sent just before process exit can be
killed mid-flight. It also hardcodes Markdown parse mode, which returns HTTP
400 for tickers containing `_` or `*` — losing the message silently.
"""
from __future__ import annotations

import logging
import os
from datetime import date

import requests

logger = logging.getLogger(__name__)

TELEGRAM_LIMIT = 4096
_MARKER = "… truncated"


def truncate(text: str) -> str:
    if len(text) <= TELEGRAM_LIMIT:
        return text
    return text[: TELEGRAM_LIMIT - len(_MARKER)] + _MARKER


def send_sync(text: str) -> bool:
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        logger.warning("TELEGRAM_TOKEN/TELEGRAM_CHAT_ID not set — message not sent")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": truncate(text)},  # plain text, no parse_mode
            timeout=20,
        )
    except requests.RequestException as e:
        logger.error(f"Telegram send failed: {e}")
        return False
    if resp.status_code != 200:
        logger.error(f"Telegram send failed: HTTP {resp.status_code} {resp.text[:200]}")
        return False
    return True


def format_download_success(feeds: dict[str, date | None], today: date, attempt: int) -> str:
    lines = [f"DATA DOWNLOADED — {today}", f"attempt {attempt}", ""]
    for name in sorted(feeds):
        d = feeds[name]
        mark = "OK  " if d == today else "old "
        lines.append(f"  {mark}{name}: {d if d else 'no data'}")
    return truncate("\n".join(lines))


def format_options_book(target: date, contracts: list[dict]) -> str:
    if not contracts:
        return f"TS BASIS DAILY — {target}: no signals at |z| = 3"
    lines = [f"TS BASIS DAILY — |z| = 3 SIGNALS {target}",
             f"Option prices: EOD close {target}, traded strikes only", ""]
    for c in contracts:
        if c.get("strike") is None:
            lines.append(f"{c['ticker']} {c['direction']} {c['opt_type']} — SKIP "
                         f"({c.get('screen_reason') or 'no chain'})")
            continue
        lines.append(f"{c['ticker']} {c['direction']} {c['opt_type']} {c['strike']:g} exp {c['expiry']}")
        if c.get("lot_size"):
            lines.append(f"   close {c['premium']:.2f} x {c['lot_size']} = {c['premium_cost']:,.0f}")
        else:
            lines.append(f"   close {c['premium']:.2f} (lot size not in instrument master)")
    return truncate("\n".join(lines))


def format_book_suppressed(stale: dict[str, date | None], today: date) -> str:
    lines = [f"BOOK SUPPRESSED — {today}", "",
             "The options book was withheld: the data below is not current for",
             "today, so any book built from it would be stale.", ""]
    for name in sorted(stale):
        d = stale[name]
        lines.append(f"  stale {name}: {d if d else 'no data'}")
    lines.append("")
    lines.append("Download and strategy refresh completed normally.")
    return truncate("\n".join(lines))


def format_chain_failure(step: str, tail: str) -> str:
    return truncate(f"CHAIN FAILED — {step}\n\n{tail}")


def format_stopped(outcome: str, reason: str, attempt: int) -> str:
    return truncate(f"EOD STOPPED — {outcome}\nattempts: {attempt}\n{reason}")
