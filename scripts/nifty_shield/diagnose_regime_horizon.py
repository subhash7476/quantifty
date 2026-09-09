"""Does the day-type regime call separate the move the strategy would hold?

Read-only. Gates the Q1(b) decision (move the entry to the open and hold the
session) BEFORE any code is changed: if the 10am/11am predicted regime does not
separate open->close direction over ~3,400 sessions, moving the trading window
is a large redesign that fixes nothing.

Also re-tests, at n~3,400 instead of the live window's n=6, the audit's finding
that the 13pm call carries no direction over its own holding window.

Outputs docs/reports/index_research/NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

DAILY = ROOT / "data" / "market_data" / "nse" / "candles" / "1d"
MIN1 = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
CHECKPOINT_MIN = {"10am": 600, "11am": 660, "13pm": 780}
PREDS = ROOT / "data" / "features" / "day_type" / "daytype_predictions.csv"
OUT = (ROOT / "docs" / "reports" / "index_research"
       / "NIFTY_SHIELD_REGIME_HORIZON_DIAGNOSTIC.md")
SYMBOL = "NSE_INDEX|Nifty 50"

# The classifier's own split (train_daytype_classifier.py): 2023-24 train,
# 2025 val, 2026 holdout. Everything before 2023 predates the training window
# and is the honest out-of-sample read.
OOS_END = date(2022, 12, 31)


def load_forward_moves():
    """Per session: the close at each checkpoint and the session close.

    The move that matters is from the checkpoint FORWARD - anything before it
    has already happened and cannot be predicted. Reading open->close for a
    10:00 entry would credit the label with 45 minutes it already observed.
    """
    rows = []
    for p in sorted(MIN1.glob("*.duckdb")):
        try:
            con = duckdb.connect(str(p), read_only=True)
            df = con.execute(
                "select timestamp, close from candles where symbol=? "
                "order by timestamp", [SYMBOL]).df()
            con.close()
        except Exception:                                   # noqa: BLE001
            continue
        if df.empty:
            continue
        df["hm"] = (pd.to_datetime(df["timestamp"]).dt.hour * 60
                    + pd.to_datetime(df["timestamp"]).dt.minute)
        rec = {"date": date.fromisoformat(p.stem),
               "session_close": float(df["close"].iloc[-1])}
        for cp, hm in CHECKPOINT_MIN.items():
            at = df[df.hm <= hm]
            rec[cp] = float(at["close"].iloc[-1]) if len(at) else np.nan
        rows.append(rec)
    return pd.DataFrame(rows)


def load_daily():
    rows = []
    for p in sorted(DAILY.glob("*.duckdb")):
        try:
            con = duckdb.connect(str(p), read_only=True)
            r = con.execute("select timestamp, open, high, low, close from candles "
                            "where symbol=? order by timestamp limit 1",
                            [SYMBOL]).fetchone()
            con.close()
        except Exception:                                   # noqa: BLE001
            continue
        if r is None or r[1] is None or r[1] <= 0:
            continue
        rows.append({"date": date.fromisoformat(p.stem), "open": float(r[1]),
                     "high": float(r[2]), "low": float(r[3]),
                     "close": float(r[4])})
    df = pd.DataFrame(rows)
    df["oc_pct"] = (df["close"] - df["open"]) / df["open"] * 100
    df["oc_pts"] = df["close"] - df["open"]
    df["range_pts"] = df["high"] - df["low"]
    return df


def separation(g, label_a, label_b, col):
    """Mean difference between two predicted classes, with a bootstrap CI."""
    a = g.get(label_a)
    b = g.get(label_b)
    if a is None or b is None or len(a) < 30 or len(b) < 30:
        return None
    diff = float(np.mean(a) - np.mean(b))
    rng = np.random.default_rng(20260908)
    boot = [float(np.mean(rng.choice(a, len(a))) - np.mean(rng.choice(b, len(b))))
            for _ in range(4000)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"diff": diff, "lo": float(lo), "hi": float(hi),
            "n_a": len(a), "n_b": len(b),
            "excludes_zero": bool(lo > 0 or hi < 0)}


def main():
    fwd = load_forward_moves()
    preds = pd.read_csv(PREDS)
    preds["date"] = pd.to_datetime(preds["date"]).dt.date
    df = preds.merge(fwd, on="date", how="inner")
    # move from THIS row's checkpoint to the session close
    cp_px = df.apply(lambda r: r.get(r["checkpoint"], np.nan), axis=1)
    df["cp_px"] = cp_px
    df = df[df["cp_px"].notna() & (df["cp_px"] > 0)]
    df["oc_pct"] = (df["session_close"] - df["cp_px"]) / df["cp_px"] * 100
    df["oc_pts"] = df["session_close"] - df["cp_px"]

    L = []
    w = L.append
    w("# NiftyShield - Regime Horizon Diagnostic")
    w("")
    w("Read-only. Run before the Q1(b) redesign to decide whether moving the "
      "entry to the open is worth doing at all.")
    w("")
    w("**Question.** The structure choice is directional: BullTrend buys a bull "
      "put spread, BearTrend a bear call spread. For that to pay, the predicted "
      "regime must separate the *direction of the move the position actually "
      "holds*. The live audit found 0 of 6 directional calls hit over the "
      "13:00-15:15 window. Six observations settle nothing. This tests the same "
      "question over every session the prediction artifact covers.")
    w("")
    w("**Method.** `daytype_predictions.csv` (%d rows, %d sessions) joined to "
      "Nifty 1m candles. The return runs from the checkpoint FORWARD to the "
      "session close - never from the open, because anything before the "
      "checkpoint has already happened and cannot be predicted. Grouped by "
      "*predicted* label. Separation is the mean "
      "difference between the BullTrend and BearTrend groups with a "
      "4,000-sample bootstrap 95%% CI. A CI excluding zero means the call "
      "carries direction; one spanning zero means it does not."
      % (len(preds), df["date"].nunique()))
    w("")
    w("**Out-of-sample split.** `train_daytype_classifier.py` trains on 2023-24 "
      "and validates on 2025. Sessions up to %s predate the training window and "
      "are the honest read; the full-sample rows are shown alongside and should "
      "be read as partly in-sample." % OOS_END)
    w("")

    for era, sub in (("Out-of-sample (through %s)" % OOS_END,
                      df[df["date"] <= OOS_END]),
                     ("Full sample", df)):
        w("## %s" % era)
        w("")
        w("| checkpoint | predicted | n | mean checkpoint->close % | median % | share closing up | mean abs move (pts) |")
        w("|---|---|---:|---:|---:|---:|---:|")
        for cp in ("10am", "11am", "13pm"):
            s = sub[sub.checkpoint == cp]
            for lab in ("BullTrend", "Choppy", "BearTrend"):
                g = s[s.pred_label == lab]
                if g.empty:
                    continue
                w("| %s | %s | %d | %+.3f | %+.3f | %.0f%% | %.0f |" % (
                    cp, lab, len(g), g["oc_pct"].mean(), g["oc_pct"].median(),
                    (g["oc_pct"] > 0).mean() * 100, g["oc_pts"].abs().mean()))
        w("")
        w("**Separation (BullTrend minus BearTrend, checkpoint->close %):**")
        w("")
        w("| checkpoint | mean difference | 95% CI | n Bull | n Bear | carries direction? |")
        w("|---|---:|---|---:|---:|---|")
        for cp in ("10am", "11am", "13pm"):
            s = sub[sub.checkpoint == cp]
            g = {k: v["oc_pct"].to_numpy() for k, v in s.groupby("pred_label")}
            r = separation(g, "BullTrend", "BearTrend", "oc_pct")
            if r is None:
                w("| %s | insufficient n | | | | |" % cp)
                continue
            w("| %s | %+.4f pp | [%+.4f, %+.4f] | %d | %d | %s |" % (
                cp, r["diff"], r["lo"], r["hi"], r["n_a"], r["n_b"],
                "**YES**" if r["excludes_zero"] else "no - CI spans zero"))
        w("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L), encoding="utf-8")
    print("wrote %s" % OUT)
    print(df.groupby(["checkpoint", "pred_label"])["oc_pct"].agg(["count", "mean"]))


if __name__ == "__main__":
    main()
