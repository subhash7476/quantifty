"""Manual verification harness: raw timestamps vs selected state, both eras.

SEALED dates: state construction is verified (permitted structural access),
but forward outcomes are REDACTED by default — pass --include-sealed to
print them (not for use before the methodology freeze).
"""
import argparse
from datetime import date

from scripts.analog_path import config
from scripts.analog_path.data_layer import load_session, read_day

dates = [date(2012, 6, 4), date(2016, 6, 1), date(2022, 6, 1),
         date(2023, 1, 31), date(2024, 6, 3), date(2026, 8, 4)]


def main(include_sealed: bool):
    for d in dates:
        s = load_session(d)
        sealed = config.fence_of(d) == "sealed"
        print("=" * 90)
        print(f"{d}  era={s.era}  fence={config.fence_of(d)}  valid={s.valid}  defects={s.defects}")
        bars = read_day(d)
        print(f"  bars: {len(bars)}  first={bars[0][0]}  last={bars[-1][0]}")
        for t in config.GRID_TIMES:
            hits = [b for b in bars if b[0].time() == t]
            row = f"    grid {t}: "
            row += "  ".join(f"stamp{b[0]:%H:%M} O={b[1]:.2f} C={b[2]:.2f}" for b in hits) if hits else "no direct stamp"
            print(row)
        print(f"  open(09:15)={s.open:.4f}  p_1230={s.p_1230:.4f}  R_open1230={s.open_to_1230:+.5f}")
        print(f"  path_state  = {[round(float(x), 6) for x in s.path_state]}")
        print(f"  interval_st = {[round(float(x), 6) for x in s.interval_state]}")
        if sealed and not include_sealed:
            print("  outcomes/mfe/mae: REDACTED (sealed fence)")
        else:
            for k in config.HORIZONS:
                print(f"  outcome[{k:5s}] = {s.outcomes[k]:+.6f}")
            print(f"  mfe={s.mfe:+.6f}  mae={s.mae:+.6f}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--include-sealed", action="store_true")
    args = p.parse_args()
    main(args.include_sealed)
