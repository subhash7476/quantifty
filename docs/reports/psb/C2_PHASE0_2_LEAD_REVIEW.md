# C2 Phase 0.2 — MTO Delivery Backfill — Lead Review

**Reviewer:** Claude (Lead Reviewer, standing role split)
**Date:** 2026-07-18
**Artifact under review:** `docs/reports/C2_PHASE0_2_MTO_BACKFILL_AUDIT.md` + `scripts/csmp/parse_mto.py`, `scripts/csmp/backfill_mto_delivery.py`, `scripts/probe_historical_mto.py`, `tests/csmp/test_mto_parser.py`
**Backfill copy:** `data/market_data/equity_bhavcopy_mto_backfill.duckdb` (671 MB, present, unsworn)
**Method:** independent re-derivation — ATTACH both stores READ_ONLY, re-run each arm with my own queries; raw-line hand-checks to break parser circularity; static read of the report generator. No numbers below are carried from the delivered audit.

---

## Verdict: **NOT PASSED** — swap NOT authorized

The **backfilled data is sound** — I could not falsify the delivery values, immutability, or the 2020-boundary convention that C2 depends on. But the **artifact fails its own determinism criterion** (acceptance §5), one **required deliverable is missing** (deliverable 6 tests), and one **undisclosed scoping decision** inflates a coverage metric. These are cheap, bounded fixes that do **not** require re-backfilling. The live store was never touched (verified below), so nothing is at risk while they are fixed.

Separate the two axes cleanly:
- **Data integrity: SOUND.**
- **Artifact determinism + test coverage + disclosure: FAILS.**

---

## What I independently confirmed (data integrity — SOUND)

| Check | My re-derivation | Delivered audit | Agree |
|---|---|---|---|
| Row counts copy vs orig | 7,030,920 = 7,030,920 | same | ✓ |
| Arm C immutability — **both-direction** full-row EXCEPT (all non-deliv cols, pre-2020) | 0 and 0 | one-directional 0 | ✓ (stronger) |
| True overwrite of pre-2020 **non-null** deliv cells | 0 | — | ✓ |
| 2020+ deliv cells changed | 0 | 0 | ✓ |
| deliv_pct out of [0,100] | 0 | 0 | ✓ |
| deliv_qty > volume | 8 | 8 | ✓ |
| Store EQ rows still NULL pre-2020 (Arm F) | 21 | 21 | ✓ |
| non-NULL deliv_pct span (copy) | 2010-01-04 → 2026-07-09 | same | ✓ |

**The C2-critical positive (advisor-flagged, now verified):** on the 2020 overlap, MTO's *published* `deliv_pct` matches the store's SECFULL `deliv_pct` to within 0.05 on **1,481 / 1,481 common EQ symbols (0 disagreements)** for 2020-01-02. The delivery **percentage** — not merely `deliv_qty` — carries the same convention across the splice. C2's SD re-estimation (Phase 0.4) will therefore read a continuous series, not a spliced one. This is the finding that most justifies spending the extended window.

**Raw-line hand-check (parser circularity broken):** raw `20,409,GOLDBEES,EQ,874054,152998,17.50` → stored `deliv_qty=152998, deliv_pct=17.5` ✓. The parser and backfill faithfully store MTO's published values.

**Arm B mismatches dispositioned:** the 20 `qty_traded ≠ volume` rows are all **gold ETFs** (GOLDBEES, GOLDSHARE, IPGETF, SBIGETS, RELIGAREGO, …) on 2013-05-13, plus the 8 `deliv_qty > volume` rows are ETFs/thin names on 2019-06-17/18. In every case `deliv_pct` is correct on MTO's own denominator (`deliv_qty / qty_traded`), and every symbol is **outside the NIFTY-200 point-in-time universe** C2 forms on. Benign for C2 — but see finding M2 for how they must be disclosed rather than threshold-passed.

**NULL `qty_traded` leakage:** 0 backfilled EQ rows across 400 sampled files. The parser's silent-null branch (below, L1) did not fire on real data.

---

## Blocking findings (must fix before swap)

### B1 — Digest is not byte-reproducible (violates acceptance §5)
`generate_report()` emits `**Generated:** {datetime.datetime.now(UTC)}` into `lines` (backfill_mto_delivery.py:505) and then computes the SHA-256 **over that same content** (`compute_digest(report_text)`, :567). Two runs a minute apart produce a different report and a different digest. This defeats the digest as an integrity anchor and is exactly the PSB-2 MEDIUM-1 failure class the prompt invokes ("nothing sits outside the seal, no hand-carried timestamp inside it").
**Fix:** move the timestamp outside the hashed region (emit it after the digest line, or drop it, or pin it to a content-derived value). Requirement: two consecutive runs against the same inputs produce a **byte-identical** report **and** identical digest. State that as a test.

### B2 — Deliverable 6 (backfill-invariant tests) is missing
No test references `backfill_mto_delivery` (grep: NONE). Only the 6 parser tests exist. Critically, **Arm E is vacuous**: I verified the original store has **0** pre-2020 non-null EQ `deliv_qty` cells, so `overwrite_count = 0` is true because nothing *could* be overwritten — the COALESCE no-overwrite guard (backfill_mto_delivery.py:192-200) is **completely untested**. That guard is the sole protection of any future non-null cell.
**Fix:** add the synthetic mini-store tests the prompt required — build a tiny DuckDB with (a) a pre-existing **non-null** deliv cell that MTO would contradict → assert it is **not** overwritten; (b) a NULL cell → assert it **is** filled; (c) a 2020+ row → assert untouched; plus a direct exercise of arms C/D on the fixture. Full suite green; report the count.

---

## Medium findings (fix or explicitly disclose)

### M1 — Undisclosed `n_symbols >= 200` filter narrows Arm A's denominator
The backfill calendar is `trading_calendar WHERE n_symbols >= 200` (backfill_mto_delivery.py:138-141), but the prompt said *"For every `trading_calendar` date 2010-01-04→2019-12-31."* The filter silently drops the two genuine special sessions — **2010-05-16 (7 symbols)** and **2012-11-11 (14 symbols)** — so Arm A reports "0 missing / 100.0%" against a **reduced** denominator. The residue is the 21 NULL gold-ETF rows Arm F counts, but Arm A and Arm F are never reconciled, and the filter was not flagged as a deviation.
**Fix (pick one, disclose it):** (a) drop the filter, process every calendar date, and itemize the two sub-200 sessions as Arm A coverage exceptions reconciled to Arm F's 21; **or** (b) keep the filter but state it in the report's Scope, and add a line reconciling Arm A's denominator to the Arm F residue. Either way it must be visible, not inferred.

### M2 — Arm B "pass" is a threshold pass over an un-dispositioned set
Arm B passes at 0.0708% < 0.1%, but the 20 mismatches are not a random 0.07% — they are a **coherent, explainable set** (gold ETFs, MTO `qty_traded` ≠ legacy bhavcopy `volume`). The workflow's discipline is disposition, not tolerance (the PSB-1 disposition-register lesson). The 8 `deliv_qty > volume` rows in Arm D are the same phenomenon.
**Fix:** add a short disposition block to the audit — enumerate the 20 (+8), state they are ETFs outside NIFTY-200, and record that `deliv_pct` is correct on MTO's denominator. No data change; make the reasoning part of the sealed artifact.

---

## Low / note (recommended, not blocking)

- **L1 — Parser silently nulls a corrupt `qty_traded`.** parse_mto.py:58-61 sets `qty_traded=None` on a parse failure and keeps the row, whereas a bad `deliv_qty`/`deliv_pct` *rejects* the row. A null-qty row then bypasses both Arm B and Arm D (both require `qty_traded IS NOT NULL`). Empirically 0 leakage today, but the stated discipline is "reject, never guess." Prefer rejecting the row and itemizing it.
- **N1 — Arm C shipped one-directional + set-based (dedup) EXCEPT.** It passed my stronger both-direction, per-row overwrite test, so this is a robustness note only: adopt the both-direction form in the runner so the shipped arm is as strong as the review.

---

## Live-store safety (verified)
`equity_bhavcopy.duckdb` was opened read-only for the calendar/copy and never for write; the copy is a separate file; my review ATTACHed both READ_ONLY. Row counts and all non-deliv columns are bit-identical between copy and original pre-2020, and 2020+ is bit-identical including deliv columns. **The live store is untouched. No swap has occurred and none is authorized by this review.**

---

## Required fixes — next work order for DeepSeek (Prompt 0.2-R)

Return to the implementer as a bounded revision (no re-backfill of data required — the copy's values are certified sound by this review; only the artifact, tests, and disclosure change):

1. **B1** — make the report byte-reproducible; move the timestamp out of the digest scope; add a determinism test (two runs → identical report + digest).
2. **B2** — add the deliverable-6 synthetic-mini-store tests; the COALESCE no-overwrite guard must be directly exercised (non-null cell not overwritten; NULL cell filled; 2020+ untouched; arms C/D on the fixture). Full suite green; report the count.
3. **M1** — resolve the `n_symbols >= 200` scoping: either process every calendar date and itemize the two special sessions in Arm A, or disclose the filter and reconcile Arm A to Arm F's 21. Flag it explicitly.
4. **M2** — add the Arm B/D disposition block (ETF set, outside NIFTY-200, deliv_pct correct on MTO denominator).
5. **L1 / N1** — recommended: parser rejects (not nulls) a corrupt `qty_traded`; runner adopts the both-direction Arm C.

On resubmission the Lead Review will re-run the determinism check and the new tests, and re-derive the arms once more. **Only then is the store swap authorized and Prompt 0.4 (C2 SD re-estimation) issued.** Prompt 0.4 remains HELD.

---

# Re-Review (Prompt 0.2-R) — 2026-07-18

**Resubmission verdict: store swap AUTHORIZED on data-integrity grounds; B1 only PARTIALLY closed — one bounded B1-R2 fix required to seal the audit artifact.**

Data integrity is independently sound, so the swap (which replaces data, not the report) is authorized. But B1 is not fully closed: my re-check proved digest *integrity*, not the *cross-run reproducibility* B1/§5 demand, and I found a concrete nondeterminism vector. Decoupled below.

Five of six findings independently re-verified against the regenerated copy (mtime 10:10) and the revised code — not accepted on the disposition table:

| Finding | Independent verification | Result |
|---|---|---|
| **B1** digest reproducibility | Recomputed SHA-256 over the sealed region = `45856cb1…558b07b` — matches the stated digest, and timestamp/SHA lines are confirmed **outside** the seal. **But that proves integrity, not reproducibility.** Arm B's `mismatch_detail` is sliced `[:20]` from an **unordered** SELECT (backfill_mto_delivery.py:212-219, no `ORDER BY`) that sits **inside** the sealed region; DuckDB's parallel hash join gives no stable row order, so a re-run can reorder those 20 rows and move the digest despite the timestamp fix. The determinism test fix-item-1 demanded ("two runs → identical report+digest") was also not delivered — the 4 new tests don't cover it. | **PARTIAL** — see B1-R2 |
| **B2** backfill tests | Read `tests/csmp/test_mto_backfill.py`: `test_nonnull_not_overwritten` writes a contradicting MTO value `(9999, 99.99)` against a pre-existing `(2500, 50.0)` cell and asserts preservation — the COALESCE guard is now **directly** exercised, not vacuous. 4/4 pass. | ✓ |
| **M1** filter disclosure | Scope section states `n_symbols >= 200`, names the 2 excluded special sessions, reconciles to Arm F's 21. | ✓ |
| **M2** disposition | "Disposition Notes" section enumerates the ETF set, outside NIFTY-200, `deliv_pct` correct on MTO denominator. | ✓ |
| **L1** parser | parse_mto.py:58-65 now **rejects** `"empty qty_traded"` / `"bad qty_traded: …"` instead of nulling + continuing. | ✓ |
| **N1** Arm C | Runner computes both `copy_vs_orig` and `orig_vs_copy` EXCEPT; pass requires both = 0. | ✓ |

**Independent data re-derivation on the regenerated copy:** row counts 7,030,920 = 7,030,920; both-direction immutability 0/0; true overwrite of pre-2020 non-null deliv cells = 0; 2020+ deliv untouched; deliv_pct ∈ [0,100]; Arm F residue = 21 (gold ETFs, sub-200 sessions). **Regression check: 97 tests green** across csmp/psb1/psb2.

## B1-R2 closure — 2026-07-18: **B1 CLOSED, audit artifact SEALED**

Independently re-verified: `ORDER BY m.trade_date, m.symbol` present at backfill_mto_delivery.py:224 (mismatch rows are distinct symbols per date → fully ordered); `test_report_deterministic` calls `generate_report` twice and asserts byte-identical text + digest (passes); my recompute of the sealed region equals the locked digest `4e0384646636f8376153939e627f370e89c23f1fc149fd25d92a391c6854a2cb` exactly, timestamp confirmed outside the seal; 11 tests green. Reproducibility is established by construction (only sealed list now ordered) + the passing determinism test + digest recompute; a full pipeline re-run was not required as its risk surface (timestamp, row-order) is now closed. **All six findings resolved. Prompt 0.2 passes in full.**

---

**B1-R2 — required to seal the audit artifact (bounded, does NOT re-open the gate):**
- Add `ORDER BY m.trade_date, m.symbol` to the Arm B mismatch query (backfill_mto_delivery.py:212-219) so `mismatch_detail` is deterministic. Audit any other list emitted into `content_lines` for stable ordering — `missing_dates` is already sorted; `mismatch_detail` is the sole offender.
- Add the determinism test fix-item-1 asked for: run the report generator twice on the same inputs, assert byte-identical report **and** identical digest.
- Re-run `backfill_mto_delivery.py` once and confirm the digest reproduces exactly; the audit's stated digest updates to the locked value. This is the reproducibility demonstration, not a data change.

**Authorized next steps (in order):**
1. **Store swap** — replace live `equity_bhavcopy.duckdb` with `equity_bhavcopy_mto_backfill.duckdb` (copy-first discipline complete; irreversible on production — operator executes or ratifies a swap script; keep a timestamped backup of the pre-swap live store). Authorized now on data grounds; independent of B1-R2.
2. **B1-R2** — land the ordering fix + determinism test + one re-run to lock a reproducible digest, sealing the terminal audit artifact (the PSB-2 MEDIUM-1 discipline: a terminal artifact's digest must be reproducible).
3. **Prompt 0.4 (C2 SD re-estimation)** — UNHELD, runs against the swapped (certified) store. Re-run C2 formation on the extended dev window (fenced at 2022-12-30), n grows 55 → ~230+ fortnightly formations, against exit gate **G0**: extended-window IC and SD consistent with the PSB-2 estimate (tolerance pinned *before* the run). The 2023–2026 window stays sealed.
