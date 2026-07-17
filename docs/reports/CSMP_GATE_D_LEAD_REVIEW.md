# CSMP Gate (d) — Lead Review: Delivery-equity fee model

**Date:** 2026-07-11
**Reviewer:** Claude (Lead Reviewer, per the locked CSMP role split)
**Implementer:** DeepSeek V4
**Deliverable under review:** `core/execution/equity/delivery_fees.py` (+ `__init__.py`), `tests/execution/test_delivery_fees.py`
**Verdict:** **PASS** — all seven acceptance criteria met; claims independently re-derived against the code, not taken from the implementer's report. Two LOW documented-assumption notes recorded below (non-blocking, immaterial magnitude).

---

## Independence

I did not author the deliverable. `git log -- core/execution/equity/delivery_fees.py` is empty (untracked, created by the implementer this session); my only prior involvement was a prompt-review note flagging a GST/DP ambiguity in Prompt 4 before dispatch. That flag was resolved correctly in the code (see criterion 3). Independence holds — unlike gate (b) R5, where Claude implemented and the operator waived review.

## Scope of review

Re-derived every load-bearing claim: read the module and the options module it mirrors, hand-checked the arithmetic of the full buy and sell legs and each rate era, verified the internal corroboration citation, ran the module's tests and the full execution suite, and confirmed the fence at the git level.

## Acceptance criteria — independently verified

| # | Criterion | Verdict | Evidence re-derived |
|---|-----------|---------|---------------------|
| 1 | Module exists; every rate resolved from a `trade_date`-keyed schedule; each rate cited in docstring | PASS | `_resolve()` drives `_STT_DELIVERY_SCHEDULE`, `_EXCHANGE_TXN_SCHEDULE`, `_STAMP_DUTY_SCHEDULE`, `_GST_SCHEDULE`; no rate hardcoded at a call site; docstring carries a primary source + effective date per rate. |
| 2 | Itemized breakdown; components sum to `total` | PASS | `DeliveryEquityFees.total` sums all seven fields; `test_components_sum_to_total` asserts it. |
| 3 | GST on `brokerage + exchange_txn + sebi_fee` only | PASS | `gst = g * (brokerage + exchange_txn + sebi_fee)` (line 180). Re-derived: 2025-06-02 leg gst = 0.18x(0+2.97+0.10) = **0.5526**. STT/stamp excluded; `test_gst_base_excludes_stt_and_stamp` confirms `gst < wrong_base`. DP's own GST is folded into `dp_charge` (`dp_charge_flat*(1+g)`), not double-counted in `gst` — the earlier prompt ambiguity is cleanly resolved. |
| 4 | Stamp buy-side-only post-2020; pre-2020 a single disclosed cited assumption | PASS | `stamp_duty = ... if side=="BUY" else 0.0`; schedule 0.003% (2020-07-01, central regime) / 0.01% (pre, Maharashtra-representative, disclosed in docstring lines 47-55). |
| 5 | Tests cover each component, full buy+sell, a date in **every** rate era; suite green | PASS | 28 tests: 11 schedule + 17 behavioural. Era coverage: GST 12.36/14/14.5/15/18%, stamp 2020-07, txn 2024-10. Delivery-fee suite 28 passed; **full execution suite 290 passed / 4 skipped** (re-run). Arithmetic hand-verified (buy leg total 106.6226; sell 119.5526; 2013 gst 0.43878). |
| 6 | Pure, deterministic function; same inputs -> identical output | PASS | No I/O, no clock, no network; schedule is a module constant; `test_deterministic_same_inputs_identical_output` passes; frozen dataclass. |
| 7 | No diffs outside `core/execution/equity/` and `tests/execution/` | PASS | `git status --porcelain` shows only `core/execution/equity/` and `tests/execution/test_delivery_fees.py` untracked. No frozen-component, options-module, or execution-stack diffs. |

## Corroboration checks

- **Mirror claim** (Prompt 4): structure mirrors `core/execution/options/fees.py` — effective-dated schedules, itemized frozen dataclass, `SEBI_FEE_RATE = 0.000001`, identical GST-base formula. The GST schedule is correctly **extended** (not blind-copied) to span the pre-2017 service-tax era the CSMP dev window requires.
- **Internal corroboration**: docstring cites `handler.py:1079` for the pre-2024 NSE txn rate. Verified — `handler.py:1079` uses `0.0000345`.
- **STT delivery stability**: modelled flat 0.1% both legs since 2004-10-01. Correct — the dev-window STT changes (Finance Acts 2016/2023/2024) moved derivative/intraday rates, not the delivery rate. Both-leg application verified (`stt` computed regardless of side).
- **`[VERIFY]` disclosure**: post-2024-10 NSE txn = 0.00297% is honestly flagged as best-documented-not-circular-confirmed. The value matches the SEBI MII rationalization figure; the era boundary (2024-10-01) is certain. This is exactly the gate-(a)/(b) discipline — a disclosed uncertainty, not a silent guess.

## Findings (LOW — documented, non-blocking)

- **N1 (LOW) — early-window flatness of the SEBI fee and pre-2024 NSE txn charge is asserted "stable," corroborated only for the recent era.** `SEBI_FEE_RATE` (Rs 10/crore) and pre-2024 NSE txn (0.00345%) are keyed from 1900-01-01 with no intra-window era check for 2012-2018; the only corroboration (`handler.py`, `options/fees.py`) is recent. Impact is immaterial: SEBI fee is Rs 0.10 per Rs 1 lakh and the txn charge Rs 3.45 per Rs 1 lakh, versus STT at Rs 100 per Rs 1 lakh per leg — a worst-case early-era error here is <0.2% of a leg's total cost and cannot bias a net-of-fee ranking. Recommend the same explicit `[VERIFY]`/assumption tag these already-disclosed items (pre-2020 stamp, post-2024 txn) carry, rather than an unqualified "stable."
- **N2 (LOW) — no paise rounding.** The model returns raw floats; real contract notes round each component to paise. For a deterministic research aggregate this is preferable (rounding would accumulate bias over ~30-40 names/month), so this is noted, not a defect.

## Verdict

**PASS.** The model is deterministic, era-aware, every rate cited, the GST base and both-leg STT / buy-side stamp / flat-DP semantics are correct, and the honest `[VERIFY]` and assumption disclosures meet gate discipline. Findings N1/N2 are immaterial and recorded for forward awareness. Gate (e) (transmission triage) is unlocked; Prompt 5's pre-committed stop rule must be frozen in the prompt before any run.
