"""A test run must never be able to reach the real Telegram API."""
import os


def test_telegram_credentials_are_stripped_during_tests():
    assert os.environ.get("TELEGRAM_TOKEN") is None
    assert os.environ.get("TELEGRAM_CHAT_ID") is None


def test_the_notifier_is_inert_without_credentials():
    from core.alerts.telegram_notifier import TelegramNotifier
    assert TelegramNotifier().base_url is None
