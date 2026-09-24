"""Frozen Stage-1 parameters, transcribed from the freeze document draft (docs/reports/ptms/
PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md). Section numbers refer to that file.
Nothing here is tunable; changing a value is a change to the frozen protocol."""

from datetime import date

WINDOW_START = date(2011, 3, 25)          # §11
SAMPLE_END_Z = date(2022, 12, 30)         # §11, OPEN-M
HF_EARLIEST = date(2023, 1, 2)            # 1m equities begin here: every screen observation is DB (§2.4)

# §6: declared calendar artifacts removed from the store's trading_calendar
NON_SESSIONS = frozenset({date(2012, 11, 11), date(2016, 4, 19)})

GF1_P4 = (36, 48, 72, 96, 108, 144)       # §2.2; repeats every 144 calendar days
GF1_CYCLE = 144
GF4_WINDOWS = ((7, 12), (18, 21), (28, 31), (42, 49), (57, 65), (85, 92), (112, 120), (150, 157),
               (175, 185))                # §2.3, inclusive calendar days
LOOKAHEAD_DAYS = 7                        # §2.2/§2.3, RR-7: cal(D_L)+1 .. cal(D_L)+7
OUTCOME_SESSIONS = 5                      # §4, R-2

K3_RUN = 3                                # §3, memo §5 rows 1, 11

N_SURROGATES = 1999                       # §8, B
SEED = 42                                 # §8, G-8
MEAN_BLOCK = 20                           # §8; 5 and 60 are V-B5 / V-B60 (§12)
ALPHA = 0.05 / 3                          # §10
MIN_NAMES = 20                            # §6, G-6b
SIZE_CHECK_PANELS = 200                   # §10, G-9
SIZE_CHECK_MAX_REJECTION = 2 * ALPHA      # §10

RATIO_ACTION_TYPES = ("BONUS", "SPLIT")   # §7: bonus, split, consolidation; special dividends are G-7
