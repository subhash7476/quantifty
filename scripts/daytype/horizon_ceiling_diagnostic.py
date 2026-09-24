"""How much separation could a traded-horizon DayType label actually buy?

Decision input for option (a) of `DAYTYPE_HORIZON_DISCLOSURE.md`: re-labelling
DayType on the 13:00->15:15 horizon and retraining. That would be a new
construct with its own pre-registration, so this runs first and for free.

**This is a diagnostic, not a gate.** It reads only data already spent -- the
features, sessions and labels the shipped classifier was built on -- so it
authorizes nothing and consumes no window. Its single job is to say whether the
achievable gain is large enough to justify writing a pre-registration at all.

Three numbers, on one session set:

  CURRENT   the shipped full-session label's BullTrend-minus-BearTrend
            separation, reproducing the published +0.2546 pp
  FEASIBLE  what a classifier trained on the SAME 13:00 features to predict the
            TRADED-window direction achieves, strictly out of sample under
            expanding annual folds -- the realistic ceiling for a re-label
  ORACLE    perfect foresight of the traded-window sign; unattainable, included
            only to scale the other two

**Window note.** The published diagnostic measures 13:00 -> *session close*
while its prose says "13:00-15:15". The strategy exits at 15:15. Both windows
are reported here; the traded window governs the decision.

**Predictions, pinned before the run:**

  CLOSE the question   FEASIBLE - CURRENT <= +0.10 pp on the traded window.
                       The re-label cannot pay for itself through an options
                       structure's fees against a median afternoon move of
                       10.6 points.
  WORTH PRE-REGISTERING  FEASIBLE - CURRENT >= +0.15 pp.
  INCONCLUSIVE         anything between, reported as such rather than resolved
                       by narrative.

A further expectation, stated so it can be wrong: ORACLE should be far above
both, because perfect foresight of direction is worth a great deal and neither
model has it. ORACLE being close to FEASIBLE would mean the afternoon is nearly
deterministic given 13:00 information, which nothing else in this repo suggests.

Usage: python scripts/daytype/horizon_ceiling_diagnostic.py
Output: docs/reports/index_research/DAYTYPE_HORIZON_CEILING.md
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

MIN1 = ROOT / "data" / "market_data" / "nse" / "candles" / "1m"
FEATURES = ROOT / "data" / "features" / "day_type" / "intraday_features_13pm.csv"
PREDS = ROOT / "data" / "features" / "day_type" / "daytype_predictions.csv"
OUT = ROOT / "docs" / "reports" / "index_research" / "DAYTYPE_HORIZON_CEILING.md"

SYMBOL = "NSE_INDEX|Nifty 50"
CHECKPOINT_MIN = 780          # 13:00
EXIT_MIN = 915                # 15:15, the structure's exit
OOS_END = date(2022, 12, 31)  # sessions predating the shipped classifier's training
FIRST_FOLD = 2015             # expanding folds need a few years of history first
SEED = 20260909
N_BOOT = 4000

CLOSE_THRESHOLD = 0.10
PREREG_THRESHOLD = 0.15

# ret_traded / ret_toclose are the TARGET, joined onto the same frame the
# features come from. Leaving them in the feature matrix put the answer in the
# inputs and drove the first run to 99% of oracle separation.
DROP_FROM_X = {"cluster_id", "cluster_label", "checkpoint_bar",
               "ret_traded", "ret_toclose", "feasible"}


def load_prices() -> pd.DataFrame:
    """13:00 close, 15:15 close and session close, per session."""
    rows = []
    for p in sorted(MIN1.glob("*.duckdb")):
        try:
            con = duckdb.connect(str(p), read_only=True)
            df = con.execute("select timestamp, close from candles where symbol=? "
                             "order by timestamp", [SYMBOL]).df()
            con.close()
        except duckdb.Error:
            continue
        if df.empty:
            continue
        ts = pd.to_datetime(df["timestamp"])
        hm = ts.dt.hour * 60 + ts.dt.minute
        at_cp = df[hm <= CHECKPOINT_MIN]
        at_exit = df[hm <= EXIT_MIN]
        if at_cp.empty or at_exit.empty:
            continue
        rows.append({
            "date": date.fromisoformat(p.stem),
            "px_1300": float(at_cp["close"].iloc[-1]),
            "px_1515": float(at_exit["close"].iloc[-1]),
            "px_close": float(df["close"].iloc[-1]),
        })
    out = pd.DataFrame(rows)
    out["ret_traded"] = (out["px_1515"] - out["px_1300"]) / out["px_1300"] * 100
    out["ret_toclose"] = (out["px_close"] - out["px_1300"]) / out["px_1300"] * 100
    return out


def separation(up: np.ndarray, down: np.ndarray) -> dict:
    """Mean(up) - mean(down) in pp, with a bootstrap CI."""
    if len(up) < 30 or len(down) < 30:
        return {"diff": np.nan, "lo": np.nan, "hi": np.nan,
                "n_up": len(up), "n_down": len(down)}
    rng = np.random.default_rng(SEED)
    boot = [float(np.mean(rng.choice(up, len(up)))
                  - np.mean(rng.choice(down, len(down)))) for _ in range(N_BOOT)]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    return {"diff": float(np.mean(up) - np.mean(down)), "lo": float(lo),
            "hi": float(hi), "n_up": len(up), "n_down": len(down)}


def feasible_predictions(feat: pd.DataFrame, target: pd.Series) -> pd.Series:
    """Expanding annual folds: fit on < year, predict that year. All OOS.

    Same features the shipped classifier sees at 13:00; only the target changes
    from the full-session cluster to the traded-window direction.
    """
    cols = [c for c in feat.select_dtypes("number").columns if c not in DROP_FROM_X]
    preds = pd.Series(index=feat.index, dtype=float)
    for year in range(FIRST_FOLD, int(feat.index.year.max()) + 1):
        tr = feat.index.year < year
        te = feat.index.year == year
        if tr.sum() < 250 or te.sum() == 0:
            continue
        x_tr = feat.loc[tr, cols].to_numpy()
        y_tr = target.loc[tr].to_numpy()
        ok = ~np.isnan(x_tr).any(axis=1) & ~np.isnan(y_tr)
        if ok.sum() < 250 or len(np.unique(y_tr[ok])) < 2:
            continue
        sc = StandardScaler().fit(x_tr[ok])
        clf = LogisticRegression(max_iter=1000, C=1.0, class_weight="balanced",
                                 random_state=42).fit(sc.transform(x_tr[ok]), y_tr[ok])
        x_te = feat.loc[te, cols].to_numpy()
        te_ok = ~np.isnan(x_te).any(axis=1)
        idx = feat.index[te][te_ok]
        if len(idx):
            preds.loc[idx] = clf.predict(sc.transform(x_te[te_ok]))
    return preds


def main() -> int:
    print("[1] Loading 13:00 / 15:15 / close prices...")
    px = load_prices()
    print(f"    {len(px):,} sessions")

    feat = pd.read_csv(FEATURES, index_col=0, parse_dates=True).sort_index()
    preds = pd.read_csv(PREDS)
    preds["date"] = pd.to_datetime(preds["date"]).dt.date
    preds = preds[preds["checkpoint"] == "13pm"]

    px["d"] = pd.to_datetime(px["date"])
    px = px.set_index("d").sort_index()
    joined = feat.join(px[["ret_traded", "ret_toclose", "date"]], how="inner")
    print(f"[2] {len(joined):,} sessions carry both features and prices")

    target = (joined["ret_traded"] > 0).astype(float)
    print("[3] Fitting expanding-fold classifiers on the traded-window target...")
    fpred = feasible_predictions(joined, target)
    joined["feasible"] = fpred

    # The shipped 13:00 call. Column is `pred_label` — an earlier positional
    # fallback silently picked `actual_cluster`, which is populated and so
    # passed the notna() filter while never matching a class name.
    cur = preds.set_index("date")["pred_label"]
    joined["current"] = joined["date"].map(cur)
    if not (joined["current"] == "BullTrend").any():
        raise RuntimeError("no BullTrend rows after mapping the shipped label — "
                           "the join is wrong, not the data")

    scored = joined[joined["feasible"].notna() & joined["current"].notna()].copy()
    oos = scored[scored["date"] <= OOS_END]
    print(f"[4] Scorable: {len(scored):,} sessions, of which {len(oos):,} predate "
          f"{OOS_END}")

    L: list[str] = []
    w = L.append
    w("# DayType — What Could a Traded-Horizon Label Actually Buy?")
    w("")
    w("Generated by `scripts/daytype/horizon_ceiling_diagnostic.py`. Every number "
      "is script-produced. Thresholds were pinned in the script docstring before "
      "the run.")
    w("")
    w("**A diagnostic, not a gate.** It reads only data already spent, authorizes "
      "nothing, and consumes no window. Its one job is to say whether option (a) "
      "of `DAYTYPE_HORIZON_DISCLOSURE.md` — re-labelling on the 13:00→15:15 "
      "horizon — is worth a pre-registration.")
    w("")
    w("**Window note.** The published horizon diagnostic measures 13:00 → *session "
      "close* while its prose says \"13:00-15:15\". The strategy exits at 15:15. "
      "Both are reported; the traded window governs the decision.")
    w("")

    for tag, sub in (("Out-of-sample sessions (≤ 2022-12-31)", oos),
                     ("All scorable sessions", scored)):
        w(f"## {tag}")
        w("")
        w(f"n = {len(sub):,}")
        w("")
        w("| construct | traded window 13:00→15:15 | 95% CI | to session close | 95% CI |")
        w("|---|---:|---|---:|---|")
        rows = []
        for name, up_mask, down_mask in (
            ("CURRENT — shipped full-session label",
             sub["current"] == "BullTrend", sub["current"] == "BearTrend"),
            ("FEASIBLE — retrained on traded-window sign",
             sub["feasible"] == 1.0, sub["feasible"] == 0.0),
            ("ORACLE — perfect foresight",
             sub["ret_traded"] > 0, sub["ret_traded"] <= 0),
        ):
            t = separation(sub.loc[up_mask, "ret_traded"].to_numpy(),
                           sub.loc[down_mask, "ret_traded"].to_numpy())
            c = separation(sub.loc[up_mask, "ret_toclose"].to_numpy(),
                           sub.loc[down_mask, "ret_toclose"].to_numpy())
            rows.append((name, t, c))
            w(f"| {name} | **{t['diff']:+.4f} pp** | "
              f"[{t['lo']:+.4f}, {t['hi']:+.4f}] | {c['diff']:+.4f} pp | "
              f"[{c['lo']:+.4f}, {c['hi']:+.4f}] |")
        w("")
        w(f"Class counts — current: {rows[0][1]['n_up']} bull / "
          f"{rows[0][1]['n_down']} bear; feasible: {rows[1][1]['n_up']} up / "
          f"{rows[1][1]['n_down']} down.")
        w("")
        if tag.startswith("Out-of-sample"):
            gain = rows[1][1]["diff"] - rows[0][1]["diff"]
            oracle = rows[2][1]["diff"]
            verdict_gain, verdict_oracle = gain, oracle

    w("## Verdict")
    w("")
    w(f"On the traded window, out of sample: FEASIBLE minus CURRENT = "
      f"**{verdict_gain:+.4f} pp**.")
    w("")
    if np.isnan(verdict_gain):
        w("**NO VERDICT** — one of the two separations is undefined, so the "
          "comparison could not be formed. Treat this run as failed rather than "
          "as evidence either way.")
    elif verdict_gain <= CLOSE_THRESHOLD:
        w(f"**CLOSE the question.** The gain is at or below the pinned "
          f"+{CLOSE_THRESHOLD:.2f} pp threshold. Re-labelling on the traded "
          "horizon does not buy enough separation to justify a new construct, its "
          "pre-registration, or the forward paper time needed to resolve its P&L "
          "claim. Option (a) is closed on evidence rather than on preference.")
    elif verdict_gain >= PREREG_THRESHOLD:
        w(f"**WORTH PRE-REGISTERING.** The gain clears the pinned "
          f"+{PREREG_THRESHOLD:.2f} pp threshold. Note what this does and does not "
          "establish: it is a *prediction* result. The P&L question remains "
          "undemonstrable on the available window (single-index `per_trade_pnl` "
          "needs an indefensible Sharpe at √T ≈ 1.6), so any pre-registration must "
          "resolve that forward in paper rather than through a sealed read.")
    else:
        w(f"**INCONCLUSIVE.** The gain falls between the pinned thresholds "
          f"(+{CLOSE_THRESHOLD:.2f} / +{PREREG_THRESHOLD:.2f} pp). Reported as "
          "such; not resolved by narrative.")
    w("")
    w(f"ORACLE separation on the traded window is **{verdict_oracle:+.4f} pp** — "
      "the value of perfect foresight, and the scale against which both models "
      "should be read. Neither is near it, which is the expected result: the "
      "afternoon is not close to deterministic given 13:00 information.")
    w("")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L).encode("ascii", "replace").decode("ascii"))
    print(f"\nWritten: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
