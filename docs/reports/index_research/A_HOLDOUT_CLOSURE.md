# A — HOLDOUT Closure Record (terminal artifact)

**Date:** 2026-08-27
**Status:** CLOSED. The A construct (index intraday opening-drive continuation
on Nifty futures) is **retired at HOLDOUT** per the frozen termination mapping
(`A_PHASE0_PRE_REGISTRATION.md` §10: *HOLDOUT fail → construct retired, SEALED
untouched*). **No successor is authorized by this outcome.**

## The gate sequence (all at frozen parameters, seed 42, prereg SHA-16 `ccb32090704a3396`)

| Gate | Result | Detail |
|---|---|---|
| RFA | PROCEED (0.8720) | band S_ann [0.70, 1.45] @ cadence 237, SHA `221c6ca9…` |
| TRAIN | **PASS** | w45 qualifies (p 0.0030), family p 0.0000, mean net +1.27 bp (n=1,699) |
| HOLDOUT | **FAIL** | family book w45, mean net **−0.22 bp**, p 0.1330 / 0.1500, net not positive (n=988) |
| SEALED | **untouched** | 873 sessions (2023-01-01 → present) unread; the floor (1,270) never approached |

## The decomposition — what actually happened

| Quantity | TRAIN (2012–2018) | HOLDOUT (2019–2022) |
|---|---:|---:|
| Gross sign-applied mean (w45) | **+4.41 bp** | **+3.13 bp** |
| Fees (era-accurate) | ~1.8 bp (STT 0.01%) | ~1.95 bp (STT 0.0125% from 2019-10-01) |
| Slippage (p90, both sides) | 1.46 bp | 1.46 bp |
| **Mean net** | **+1.27 bp** | **−0.22 bp** |

The effect was real but weak in-sample (gross +4.4 bp ≈ 9% of the 48 bp mean
|move|; the strongest confirmation the repo has seen of the pair-research
trend evidence), decayed out-of-sample (+3.1 bp), and the slightly higher STT
regime ate the remainder. The net flipped on a ~1.3 bp gross decay plus a
~0.2 bp fee rise — a razor-thin edge that did not survive contact with a
different era.

## What this closes, programmatically

1. **The FTMO null is reproduced on NSE.** The quadrant test the reassessment
   memo commissioned ("does NSE index intraday differ from the FTMO corpus?")
   is answered: at the effect sizes the corpus predicts, and weaker — the
   index-level continuation evidence (pair-research slopes) did not survive
   out-of-sample. The NSE-specific hints (auction concentration, trending
   slopes) were insufficient.
2. **The ISD-program reassessment's successor ordering is superseded.** A was
   option (a) ("cost-viable today, power-clearable, falsifiable cheaply") —
   it was falsified cheaply, as designed. Option (b) (SSF multi-day carry of
   the ISD signals) remains conditional on the persistence question, which is
   still unmeasured; its negative prior (F1's CI-includes-zero) is now joined
   by A's OOS failure — the futures/derivative-horizon momentum prior has
   strengthened, not weakened.
3. **SEALED remains unspent** — 2023-01-01 → present, 873 sessions, no read.
   It is not inherited by any successor; per the closed battery's discipline,
   a successor constructs its own fences and its own sealed mechanics.
4. **No re-tuning, no re-scoping.** The freeze forbids it; the w30 cell was
   negative and the w45 margin was era-dependent — any "improvement" would be
   in-sample fitting on a closed artifact.

## Prior-exposure value for any future construct

A's full record (audit, definition, certification, RFA, TRAIN, HOLDOUT) is
disclosed prior for whatever starts next: the index 1m structural exposure
(DayType), the pair-research signal exposure, A's own TRAIN/HOLDOUT reads
(the opening-drive continuation numbers above), and the cost wall
decomposition (fees 1.9–3.8 bp by era, slippage ~0.7–0.8 bp/side, basis
dispersion 19.2 bp).

## Forward paper run — operator-commissioned (2026-08-27), pending build

The operator commissioned a **forward PAPER run of the frozen w45 family book
for ≥ 3 months** (trades recorded through Trade Intelligence; a decision to
retire permanently at the end). Recorded here so the run cannot be misread
later:

- **Framing:** forward validation of the RETIRED construct. It is **not** a
  path back to SEALED (the sealed spend gates never fire after the HOLDOUT
  fail); it is not a resurrection mechanism. Any outcome other than
  permanent retirement requires new governance (a fresh pre-registration),
  never an automatic path.
- **Mechanics (pre-reg §9 Paper gate, verbatim):** frozen w45 book, no
  parameter edits, no early abort on eyeballed P&L; any discretionary change
  restarts the 3-month clock and is logged in the trial ledger.
- **Pre-committed evaluation (fixed before the first trade):** mean net
  bp/trade vs the TRAIN (+1.27) and HOLDOUT (−0.22) benchmarks, over ≥ 3
  months of forward sessions (clock starts at the first trade); outcome =
  permanent retirement, recorded in a decision memo.
- **Accounting conventions (pre-specified):** fills at actual bar prices
  (the backtest's slippage lanes do not apply to paper fills); era-accurate
  futures fees at fills; basis mean report-only, basis dispersion (19.2 bp
  full-day p90) recorded as a standing caveat in each monthly evaluation
  (D5-consistent, no silent cost).
- **Build status:** pending operator go-ahead; the runner
  (`scripts/a_index_intraday/run_paper_forward.py`) imports branch-only
  modules (`common.py`, `core/execution/futures/futures_fees.py`) — the
  `isd-program-reassessment` merge decision precedes the build.

## Record-keeping

- Ledger: `data/a_index_intraday/trial_ledger.jsonl` (append-only; cell
  registrations precede results; both gates' events present)
- Reports: `A_TRAIN_REPORT.md`, `A_HOLDOUT_REPORT.md`
- Declaration: `governance/rfa/declarations/a_index_intraday.py` (frozen,
  SHA `221c6ca9…` — unchanged; a frozen declaration is never edited)
- Pre-registration: `A_PHASE0_PRE_REGISTRATION.md` (frozen, SHA-16
  `ccb32090704a3396` — unchanged)
