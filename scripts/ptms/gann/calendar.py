"""Session calendar 𝒟 and ISO formation weeks (freeze §6, CAL-1, OPEN-11, RR-7).

The calendar is a sorted tuple of NSE session dates. It is built by the caller from the store's
`trading_calendar` minus `constants.NON_SESSIONS`; this module does no I/O. Special sessions,
including Sunday Muhurat sessions, are ordinary members of 𝒟. The Stage-1 screen is DB-only, so only
session dates are needed, never intraday times.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from scripts.ptms.gann.constants import LOOKAHEAD_DAYS, OUTCOME_SESSIONS


@dataclass(frozen=True)
class FormationWeek:
    iso_year: int
    iso_week: int
    last_idx: int          # index of D_L in the calendar

    @property
    def key(self):
        return (self.iso_year, self.iso_week)


class Calendar:
    def __init__(self, sessions):
        sessions = tuple(sessions)
        if list(sessions) != sorted(set(sessions)):
            raise ValueError("sessions must be strictly increasing")
        self.sessions = sessions
        self.index = {d: i for i, d in enumerate(sessions)}
        self.ordinals = tuple(d.toordinal() for d in sessions)

    def __len__(self):
        return len(self.sessions)

    def formation_weeks(self):
        """One FormationWeek per ISO Monday–Sunday week that holds a session; D_L is its last session
        (CAL-1: a Sunday session is the last session of its week)."""
        last = {}
        for i, d in enumerate(self.sessions):
            y, w, _ = d.isocalendar()
            last[(y, w)] = i
        return [FormationWeek(y, w, i) for (y, w), i in sorted(last.items(), key=lambda kv: kv[1])]

    def outcome_window(self, anchor_idx):
        """Indices O_1 … O_5: the five sessions after the anchor session. None if the calendar ends
        first (the caller applies OPEN-M against Z before reading any session after Z)."""
        end = anchor_idx + OUTCOME_SESSIONS
        if end >= len(self.sessions):
            return None
        return range(anchor_idx + 1, end + 1)

    def lookahead_dates(self, d_l_idx):
        """Calendar dates cal(D_L)+1 … cal(D_L)+7 (RR-7), sessions or not."""
        d = self.sessions[d_l_idx]
        return [d + timedelta(days=k) for k in range(1, LOOKAHEAD_DAYS + 1)]


def o5_after(cal: Calendar, anchor_idx: int, z: date):
    """OPEN-M: the O_5 date for an anchor, or None if O_5 > Z. Uses the calendar only."""
    window = cal.outcome_window(anchor_idx)
    if window is None or cal.sessions[window[-1]] > z:
        return None
    return cal.sessions[window[-1]]
