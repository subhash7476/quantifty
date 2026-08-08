"""NiftyShield — DS2-4 journaled publish hook (E007 E7-2).

Wraps `make_driver_hook` (the live 13:00 fact publisher) so a not-ready /
skipped-session outcome becomes a DURABLE journal line instead of a silently
dropped entry. Claude's E006 review note #2: the driver *discards* the hook's
return dict, so the wrapper owns journaling.

The driver stays journal-agnostic; this wrapper inspects the returned dict and
records `FACT_PUBLISH_SKIPPED` on `{"ready": False}` (F2 NULL-VIX skip, DS2-4)
and on a raised publish (the session produces no entry either way; the failure
is visible, not hidden). A raised hook is re-raised so the driver's own
best-effort logging still runs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from core.runtime.event_journal import EventType, RuntimeEventJournal
from scripts.daytype.publish_live_fact import make_driver_hook


def journaled_publish_hook_factory(
    journal: RuntimeEventJournal,
    facts_db_path: str,
) -> Callable[[Any], Callable[[datetime], Optional[dict]]]:
    """Return the `publish_hook_factory` seam for `fno_runner.build_runner`.

    The factory receives the execution handler (unused here) and returns the
    wrapped per-session hook.
    """

    def factory(execution: Any) -> Callable[[datetime], Optional[dict]]:
        inner = make_driver_hook(facts_db_path)

        def hook(timestamp: datetime) -> Optional[dict]:
            try:
                result = inner(timestamp)
            except Exception as exc:
                _record(journal, timestamp,
                        f"live 13:00 fact publish raised: {exc}",
                        {"error": str(exc)})
                raise
            if result is not None and not result.get("ready"):
                _record(journal, timestamp,
                        f"live 13:00 fact not ready: {result.get('reason')}",
                        {"reason": result.get("reason"),
                         "session": str(result.get("session"))})
            return result

        return hook

    return factory


def _record(journal: RuntimeEventJournal, timestamp: datetime,
            message: str, metadata: Dict[str, Any]) -> None:
    try:
        journal.record(
            EventType.FACT_PUBLISH_SKIPPED, message,
            source_component="NiftyShieldPaperRunner",
            metadata={"session": timestamp.date().isoformat(), **metadata},
        )
    except Exception:
        pass
