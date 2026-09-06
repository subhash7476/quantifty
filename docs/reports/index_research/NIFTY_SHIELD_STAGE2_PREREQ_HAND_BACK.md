# NiftyShield — Stage 2 Prerequisite Hand-back (`nifty_shield_v1`)

**For:** Operator (re-grant authority). **From:** DeepSeek V4 (implementer).
**Status:** **HAND-BACK — grants nothing.** The CONFORMANT re-grant is the operator's
decision, exactly as E005 was. This package records the new `code_ref`, the DS2-1 gate
evidence, and the proposed datasheet update the operator applies at the re-grant.
**Prompt of record:** `docs/reports/NIFTY_SHIELD_STAGE2_PREREQ_IMPLEMENTATION_PROMPT.md`
(all four §3 decisions ratified 2026-08-08 as recommended).

> **Do not start E006 from this package.** E006 does not begin until the re-grant lands
> (prompt §7 sequencing): the datasheet §10 round-trip count must accumulate against ONE
> `code_ref`. **Re-certify first, then start counting.**

---

## 1. New code_ref (recorded)

| Field | Value |
|---|---|
| `strategy_id` | `nifty_shield_v1` (unchanged — a re-cert is the *same* strategy at a new `code_ref`, never a new `strategy_id`, MM12.5 §5.2) |
| `config_hash` | **`c5b722ff204d4e434f5cbffb1674136738a79693a3ced17bf07e46676d5336c6` — UNCHANGED** (reproduces from `config.py`; verified 2026-08-08) |
| `code_ref` | **`794922a`** — commit of the re-certified package + producers on branch `feat/nifty-shield-stage2-prereq` (proposed; the operator pins the merge commit at the re-grant) |
| Identity triple | same `strategy_id` + same `config_hash` + new `code_ref` |

## 2. DS2-1 acceptance gate — evidence (state as a gate, and it holds)

At the new `code_ref`, over the **unchanged frozen corpus** (`strategies/nifty_shield_v1/corpus/`):

- **Replay-twice byte-identical 16-signal stream** — `test_replay_twice_byte_identical_streams`
  (asserts `len(first) == 16`) PASS.
- **Guard-wrapped suite green** — `test_conformant_guarded_wrapper` (full Layer 1 + Layer 2 over
  `GuardedSignalSource`) PASS, plus `test_conformant_layers_1_and_2` raw PASS.
- **`config_hash` unchanged** — `c5b722ff…536c`, reproduces from `config.py` (verified).
- **Latency budget** — `test_conformant_layers_1_and_2` runs the p99 on_bar check at 0.05 s; PASS.
- Full strategy/daytype/runtime suites: **431 tests PASS** (2026-08-08).

Because all three hold, the read-timing change is a **re-certification of the same identity at a
new `code_ref`** — a provable behavioral no-op offline. None of them moved; nothing to stop-and-report.

## 3. Deliverables implemented

| § | Deliverable | Where | Notes |
|---|---|---|---|
| A | Per-session pre-signal publish hook (DS2-2) | `core/runtime/driver.py` (additive seam) + `scripts/daytype/publish_live_fact.py:make_driver_hook` | Fires once per session, at/after the 13:00 tick, before `on_bar`, in-process. **Driver edit flagged for review** (§5 below). |
| B | Intraday VIX `vix_at_checkpoint` (DS2-3) | `scripts/daytype/publish_live_fact.py` (`vix_at_checkpoint`, India VIX 1m last close ≤ 13:00) + schema migration (`publish_facts.py`, `publish_live_fact.py`) | Live rows: `vix_close=NULL`, `vix_at_checkpoint=<13:00 VIX>`. Legacy `vix_close` keeps its EOD meaning; offline publisher unchanged. |
| C | Lazy/re-queryable reader + source gate (DS2-1) | `strategies/nifty_shield_v1/facts.py` (`fact()`, per-session cache, re-query on miss, column-shape detection) + `source.py` (`vix = fact.get("vix_at_checkpoint") or fact.get("vix_close")`) | Frozen corpus carries no `vix_at_checkpoint` → falls back to EOD `vix_close` → byte-identical. **Corpus NOT regenerated.** |
| D | Parity + determinism | `tests/daytype/test_daytype_facts.py::test_live_offline_parity_shared_columns_and_vix_per_ds2_3` + `tests/runtime/test_publish_hook_live_dry_run.py` | Live↔offline shared columns byte-identical over identical session bars; VIX per DS2-3. |
| E | Hand-back | this report | Grants nothing. |

## 4. Proposed datasheet update (operator applies at the re-grant)

`docs/strategies/nifty_shield_v1/datasheet.md` §1 (Identity) — change only the `code_ref` row:

```
| `code_ref` | **`<new code_ref>`** — commit of the re-certified package
              (Stage-2 prerequisite: DS2-1 lazy read-timing + DS2-3 VIX gate);
              re-granted at Ledger E006 (operator) |
```

The frozen `config_hash` and the rest of §1–§11 are untouched. The datasheet's §6 latency row
("fact loaded at on_start") becomes history — the fact is now queried lazily at the 13:00 bar
(measured p99 still within the 0.05 s budget; the query is one indexed SELECT per session).

## 5. Review flags (prompt §4A — clean additive seam, must be flagged)

`core/runtime/driver.py` was edited as a **clean additive seam**: two new optional constructor
parameters (`publish_hook: Optional[Callable[[datetime], Optional[dict]]]`, `publish_checkpoint_time:
Optional[time]`) and a per-session latch (`_published_sessions`), invoked between the rebalance hook
and `on_bar` in `_tick`. When neither parameter is set, the loop is byte-for-byte unchanged (the
existing `tests/runtime` driver suite passes untouched). The seam is strategy-agnostic — no
daytype/strategy knowledge lives in the driver; the composition root supplies the checkpoint time
and the publish callable.

## 6. Operator notes carried (record, not config edits)

- The certified VIX gates (`vix_skip_above` 20.0 / `vix_reduce_above` 16.0 / `iron_fly_vix_above`
  14.0) now act on a **13:00** VIX in live rows — a semantics change the `config_hash` cannot
  detect (DS2-3 operator note). It is a Stage-2 PAPER observation to record, not a config edit.
- The intraday-VIX gating is a **live-only behavior, never exercised in conformance** — it is
  validated in E006 PAPER, explicitly **not** claimed equivalent to Stage-1's EOD-VIX gating.
- Do **not** backfill `vix_at_checkpoint` into the frozen corpus — that would change the certified
  stream and void the re-cert.

## 7. Scope confirmations

- **E006 PAPER validation window: NOT started** (blocked on the re-grant, per prompt §7).
- **OSC prohibition honored:** no read of the unread index-options window 2016-02-11 → 2022-12-31.
- **No live Upstox order placement** (PAPER path only; the hook publishes facts, never orders).
- **F2 NULL-VIX skip not weakened:** VIX-less session → publisher writes nothing → source reads no
  fact → session skipped, visible to the journal via the hook's not-ready result (DS2-4).
- **No frozen platform component modified** (Feature-Frozen table untouched; the DayType model
  files, `NseMarginEngine`, and the SPAN stack were not edited).
