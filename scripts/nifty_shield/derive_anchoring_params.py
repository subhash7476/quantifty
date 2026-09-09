"""Derive NiftyShield's anchoring parameters from history, ex ante.

Read-only. Produces the numbers that replace the absolute constants in
`strategies/nifty_shield_v1/config.py`, together with the derivation, so the
config carries reasoning rather than magic numbers.

Method, applied identically to all three:
  **map the existing constant onto its historical equivalent in the new,
  scale-invariant unit.** That preserves the original design intent and removes
  the arbitrariness, without fitting anything to observed P&L. Nothing here
  reads a trade, a fill, or an outcome.

  1. VIX gates 14 / 16      -> percentiles of the trailing India VIX distribution
  2. Wing offsets 150 / 100 / 50 pts -> fractions of 1 sigma to expiry
  3. Profit target 0.50 of *credit* -> 0.50 of the *modelled available decay*

Output: docs/reports/index_research/NIFTY_SHIELD_ANCHORING_DERIVATION.md
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DAILY = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
OUT = (ROOT / "docs" / "reports" / "index_research"
       / "NIFTY_SHIELD_ANCHORING_DERIVATION.md")
JSON_OUT = ROOT / "data" / "nifty_shield" / "anchoring_params.json"

NIFTY = "NSE_INDEX|Nifty 50"
VIX = "NSE_INDEX|India VIX"

# The constants being replaced, read off the config as it stands.
LEGACY = {"iron_fly_vix_above": 14.0, "vix_reduce_above": 16.0,
          "directional_wing_pts": 150, "wing_offset_pts": 100,
          "strangle_otm_pts": 50}
LOOKBACK_SESSIONS = 756          # ~3 years, the trailing window for percentiles
EXPIRY_WEEKDAY = 1               # Nifty weekly expiry: Tuesday
EXPIRY_DAYS_MIN = 2
SESSION_HOURS = 6.25             # 09:15-15:30
HOLD_HOURS = 2.5                 # 13:00 -> 15:30 of market time


def load_series():
    rows = []
    for p in sorted(DAILY.glob("*.duckdb")):
        try:
            con = duckdb.connect(str(p), read_only=True)
            df = con.execute(
                "select symbol, close from candles where symbol in (?, ?)",
                [NIFTY, VIX]).df()
            con.close()
        except Exception:                                   # noqa: BLE001
            continue
        if df.empty:
            continue
        d = dict(zip(df["symbol"], df["close"]))
        if NIFTY not in d or VIX not in d:
            continue
        rows.append({"date": date.fromisoformat(p.stem),
                     "nifty": float(d[NIFTY]), "vix": float(d[VIX])})
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def nearest_expiry(d: date) -> date:
    target = d + timedelta(days=EXPIRY_DAYS_MIN)
    return target + timedelta(days=(EXPIRY_WEEKDAY - target.weekday()) % 7)


def main():
    s = load_series()
    s = s[(s.vix > 0) & (s.nifty > 0)].reset_index(drop=True)

    # ---- 1. VIX gates as percentiles -------------------------------------
    # Trailing percentile of each legacy level, evaluated on every session that
    # has a full lookback window. The reported figure is the median over
    # sessions, i.e. "what percentile did this level typically represent".
    pct = {}
    for name, level in (("iron_fly_vix_above", LEGACY["iron_fly_vix_above"]),
                        ("vix_reduce_above", LEGACY["vix_reduce_above"])):
        vals = []
        v = s["vix"].to_numpy()
        for i in range(LOOKBACK_SESSIONS, len(v)):
            win = v[i - LOOKBACK_SESSIONS:i]
            vals.append((win < level).mean() * 100)
        pct[name] = {"median_pctile": float(np.median(vals)),
                     "p25": float(np.percentile(vals, 25)),
                     "p75": float(np.percentile(vals, 75)),
                     "n": len(vals), "level": level,
                     "current_pctile": float(vals[-1]) if vals else float("nan")}

    # ---- 2. Wing offsets as sigma fractions ------------------------------
    s["expiry"] = s["date"].map(nearest_expiry)
    s["dte"] = (s["expiry"] - s["date"]).map(lambda t: t.days)
    # 1 sigma to expiry, in index points, from the session's own VIX.
    s["sigma_pts"] = s["nifty"] * (s["vix"] / 100.0) * np.sqrt(s["dte"] / 365.0)
    s = s[s.sigma_pts > 0]
    frac = {}
    for name, pts in (("directional_wing_pts", LEGACY["directional_wing_pts"]),
                      ("wing_offset_pts", LEGACY["wing_offset_pts"]),
                      ("strangle_otm_pts", LEGACY["strangle_otm_pts"])):
        r = pts / s["sigma_pts"]
        frac[name] = {"pts": pts, "median_frac": float(r.median()),
                      "p25": float(r.quantile(0.25)),
                      "p75": float(r.quantile(0.75)),
                      "n": int(len(r))}

    # ---- 3. Profit target as a fraction of available decay ---------------
    # ATM premium scales ~ sqrt(T). Holding h of market time out of T leaves
    # sqrt((T-h)/T), so the decay available with the spot unchanged is
    # 1 - sqrt((T-h)/T). Trading-time convention: only market hours count.
    s["trading_hours_to_expiry"] = (
        (s["dte"] * 5.0 / 7.0) * SESSION_HOURS)      # calendar -> trading days
    s["avail_decay"] = 1.0 - np.sqrt(
        np.clip(s["trading_hours_to_expiry"] - HOLD_HOURS, 0, None)
        / s["trading_hours_to_expiry"])
    decay = {"median": float(s["avail_decay"].median()),
             "p10": float(s["avail_decay"].quantile(0.10)),
             "p90": float(s["avail_decay"].quantile(0.90)),
             "by_dte": {int(k): float(v) for k, v in
                        s.groupby("dte")["avail_decay"].median().items()}}

    params = {
        "derived_on": date.today().isoformat(),
        "sessions": int(len(s)),
        "span": [s["date"].min().isoformat(), s["date"].max().isoformat()],
        "vix_iron_fly_pctile": round(pct["iron_fly_vix_above"]["median_pctile"], 1),
        "vix_strangle_pctile": round(pct["vix_reduce_above"]["median_pctile"], 1),
        "vix_pctile_lookback_sessions": LOOKBACK_SESSIONS,
        "directional_wing_sigma_frac": round(frac["directional_wing_pts"]["median_frac"], 3),
        "wing_sigma_frac": round(frac["wing_offset_pts"]["median_frac"], 3),
        "strangle_otm_sigma_frac": round(frac["strangle_otm_pts"]["median_frac"], 3),
        "profit_target_decay_frac": 0.50,
        "hold_hours": HOLD_HOURS,
        "session_hours": SESSION_HOURS,
    }

    L = []
    w = L.append
    w("# NiftyShield - Anchoring Parameter Derivation")
    w("")
    w("Read-only, generated by `scripts/nifty_shield/derive_anchoring_params.py`. "
      "These are the numbers that replace the absolute constants in "
      "`strategies/nifty_shield_v1/config.py`.")
    w("")
    w("**Nothing here reads a trade, a fill, or an outcome.** The audit found "
      "the strategy's decisions were made by constants chosen once and never "
      "re-validated against the regime they now run in. Choosing replacements "
      "by what would have paid best over the 8 observed trades would repeat "
      "that error in a worse form - fitting to a sample of 8. So every "
      "parameter below is derived one way: **map the legacy constant onto its "
      "historical equivalent in a scale-invariant unit.** Design intent is "
      "preserved; only the unit changes, from one that expires to one that "
      "does not.")
    w("")
    w("Substrate: %d sessions of Nifty 50 and India VIX daily closes, %s to %s."
      % (len(s), s["date"].min(), s["date"].max()))
    w("")

    w("## 1. Vol gates: absolute VIX -> trailing percentile")
    w("")
    w("`iron_fly_vix_above = 14` and `vix_reduce_above = 16` never fired once "
      "in the live window (observed VIX 10.57-11.65), making `iron_fly` and "
      "`short_strangle` unreachable. The levels are not wrong in themselves - "
      "they encode \"unusually high vol\" - but they encode it in a unit that "
      "drifts. Below, each level is expressed as the percentile of the "
      "trailing %d-session VIX distribution it typically occupies."
      % LOOKBACK_SESSIONS)
    w("")
    w("| legacy constant | level | median trailing percentile | p25 | p75 | percentile today | sessions |")
    w("|---|---:|---:|---:|---:|---:|---:|")
    for k, v in pct.items():
        w("| `%s` | %.1f | **%.1f** | %.1f | %.1f | %.1f | %d |" % (
            k, v["level"], v["median_pctile"], v["p25"], v["p75"],
            v["current_pctile"], v["n"]))
    w("")
    w("The spread between p25 and p75 is the drift the absolute level was "
      "hiding: the same VIX number has meant materially different things about "
      "how unusual the vol is. The percentile form is what the config now "
      "carries; the gate is evaluated against the trailing window at entry, so "
      "it cannot silently expire again.")
    w("")

    w("## 2. Strike offsets: fixed points -> fractions of 1 sigma")
    w("")
    w("1 sigma to expiry is `spot x (VIX/100) x sqrt(DTE/365)` - the market's "
      "own estimate of how far the index travels before the structure expires. "
      "The audit measured it ranging 189-448 points over eight trades while the "
      "wing stayed at 150, so the same nominal structure was 0.79 sigma wide "
      "one day and 0.34 sigma the next. Each legacy offset is expressed below "
      "as the sigma fraction it has historically represented.")
    w("")
    w("| legacy constant | points | median sigma fraction | p25 | p75 | sessions |")
    w("|---|---:|---:|---:|---:|---:|")
    for k, v in frac.items():
        w("| `%s` | %d | **%.3f** | %.3f | %.3f | %d |" % (
            k, v["pts"], v["median_frac"], v["p25"], v["p75"], v["n"]))
    w("")
    w("Strikes are still rounded to the 50-point strike grid, so the realised "
      "offset is the nearest tradeable strike to `frac x sigma`, floored at one "
      "grid step.")
    w("")

    w("## 3. Profit target: fraction of credit -> fraction of available decay")
    w("")
    w("`profit_target_pct = 0.50` asked a structure to shed half its premium "
      "over a 2.5-hour hold. ATM premium scales roughly with `sqrt(T)`, so "
      "holding `h` of market time out of `T` leaves `sqrt((T-h)/T)` and the "
      "decay available with spot unchanged is `1 - sqrt((T-h)/T)`. On the "
      "trading-time convention (%.2f market hours per session, %.1f-hour hold):"
      % (SESSION_HOURS, HOLD_HOURS))
    w("")
    w("| DTE (calendar days) | median available decay |")
    w("|---:|---:|")
    for k in sorted(decay["by_dte"]):
        w("| %d | %.2f%% |" % (k, decay["by_dte"][k] * 100))
    w("")
    w("Median across all sessions: **%.2f%%** (p10 %.2f%%, p90 %.2f%%). The "
      "target asked for 50%%. It was not merely optimistic - it was outside "
      "the reachable set by an order of magnitude, which is why `time_exit` "
      "fired on every structure that was not closed by hand."
      % (decay["median"] * 100, decay["p10"] * 100, decay["p90"] * 100))
    w("")
    w("**The replacement keeps the 0.50 and fixes the denominator.** The target "
      "becomes 50%% of the decay actually available to a structure of this DTE "
      "over this hold - `profit_target_decay_frac = 0.50` - which is the "
      "original design intent (\"take half of what is there\") applied to a "
      "quantity that exists. The available-decay fraction is computed per "
      "structure at entry from its own DTE and carried on the signal, so the "
      "threshold self-scales instead of being a constant at all.")
    w("")
    w("One tension to record rather than hide: an intraday take-profit that is "
      "now actually reachable will close some structures before the session "
      "ends, forgoing the directional separation measured in "
      "`NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md` (+0.255 pp, 13:00 to close). "
      "Whether take-profit beats holding to the clock is a live question that "
      "could not be asked before, because the target never fired. It should be "
      "measured on forward paper sessions, not decided here.")
    w("")

    w("## 4. Pinned values")
    w("")
    w("```json")
    w(json.dumps(params, indent=2))
    w("```")
    w("")
    w("Re-run this script to refresh them; the config records the derivation "
      "date. A parameter here is only as current as the substrate it was "
      "derived from - that is the property the absolute constants lacked.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(params, indent=2), encoding="utf-8")
    print(json.dumps(params, indent=2))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
