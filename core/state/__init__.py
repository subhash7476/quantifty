"""
core.state — session-state infrastructure.

Home of the DayType regime-classifier engine (daytype_engine.py), adopted as a
facts publisher. Infrastructure only — this package never emits SignalEvents
and never enters the promotion pipeline (DAYTYPE_FACTS_ADOPTION_SPEC §1).
"""
