# PTMS — Gann Stage-1 closure entries — DRAFT FOR THE OPERATOR

**Status: DRAFT. Nothing here has been applied.** This file proposes the wording for two edits that
close Stage 1: one to the freeze checklist (research-owned, but the closing verdict is the operator's
call) and one to the exposure register (**operator-owned — research does not edit the register**).
The frozen document is not touched by either, and must never be edited.

**Facts these entries rest on** — all script-generated, none retyped by hand:

| Item | Value |
|---|---|
| Freeze document | `docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_DOCUMENT_DRAFT_2026-09-19.md` |
| Freeze commit | `2f5655b` |
| SHA-256 | `27640c87020e48add18f05e7c27a12517fb4648e5724648380874c2af3d1822a` |
| G-S1 appended | `cabaeba`, 2026-09-19 |
| Size-check record | `docs/reports/ptms/PTMS_GANN_STAGE1_SIZE_CHECK.json`, commit `9382720` |
| Screen results + report | commit `2de0548` |
| Code at the read | `scripts/ptms/gann/` unchanged from `357174a` (freeze §14) |
| Panel SHA-256 | `06b375ef9385a8d20c1d41be02d84f32c30755eac16db7dd0c635961de3a35fd` |

---

## A. Freeze checklist — `docs/reports/ptms/PTMS_GANN_STAGE1_FREEZE_CHECKLIST_2026-09-15.md`

### A.1 New row 20, after row 19 in §3

```
| 20 | Blind size check recorded, then the screen run and both results committed | **DONE 2026-09-24.** Size check: 200 pseudo-real panels, rejections GF-1 3, GF-4T/R8 0, GF-10 6, all within 2α = 0.0333, so all three were screened (`PTMS_GANN_STAGE1_SIZE_CHECK.json`, commit `9382720`, recorded before unblinding). Screen: `PTMS_GANN_STAGE1_SCREEN_RESULTS.json` + `PTMS_GANN_STAGE1_SCREEN_REPORT.md`, commit `2de0548`, run at head `9382720` with the guard passing and the code identical to `357174a`. **All three primaries retired on the surrogate leg** (A.2 row 0) | R-12 screen | Research |
```

### A.2 Replacement for the paragraph that follows the §3 table

The current text reads "**Screen preconditions (R-12), all unmet:** …". Proposed replacement:

```
**Screen preconditions (R-12), all met and now consumed:** items 1–19 SATISFIED, including R-11
frozen after its audit, R-13 complete and R-14 finalized; G-S1 appended by the operator at `cabaeba`
before any read; the blind size check recorded at `9382720` before unblinding. The screen ran on
2026-09-24 (row 20). **These preconditions cannot be met a second time for this hypothesis set** —
the panel has been read at signal level under GR-1.4, and the three constructs are retired.
```

### A.3 New block at the top of §6 Verdict

```
> **STAGE 1 COMPLETE — 2026-09-24. All three primaries retired.** The screen ran once, under the
> frozen protocol, with the guard passing and no protocol change of any kind. Results at `2de0548`:
>
> | Construct | T_c | p_sur | α | Outcome |
> |---|--:|--:|--:|---|
> | GF-1 | −0.0101 | 0.9530 | 0.0167 | Retired on the surrogate leg |
> | GF-4T/R8 | +0.0334 | 0.9800 | 0.0167 | Retired on the surrogate leg |
> | GF-10 | +0.0473 | 0.2140 | 0.0167 | Retired on the surrogate leg |
>
> The frozen wording applies to each: *"No evidence, against a surrogate null, of an effect of the
> optimistic size that confirmation would need."* **Never** "Gann's rule is false". Under G-1, a
> construct retired here may not proceed to a confirmatory test.
>
> **Two findings recorded for any successor, neither acted on** (Stage 1 forbids respecification):
>
> 1. **GF-4T/R8's surrogate null sits above its own real statistic.** The real T_c is +0.0334; the
>    2.5th percentile of its surrogate distribution is +0.0339. In the size check, 139 of the first
>    153 pseudo-real panels returned p ≥ 0.95. A one-sided upper test could not plausibly have been
>    passed by this construct whatever the data showed, so its retirement carries little information
>    about the hypothesis. The size check cannot detect this, because it counts only false positives.
>    A successor that reuses this surrogate construction should check the **upper** tail as well.
> 2. **GF-10 was evaluated on roughly half its calendar.** 272 of its formation dates were dropped
>    for an undefined per-date IC, leaving 320. This is structural, not anomalous — the surrogate
>    median is 264 — but it is the sample the p-value rests on. Its specificity contrast also runs
>    against the time reading: T(price) +0.1265 against T(time) +0.0086, Δ = −0.1179 on about 50
>    dates. That leg does not bear on the outcome, since the primary leg already failed.
>
> The N-SZ placebo returned no qualifying dates (n = 0, T_c undefined) and so was not evaluated,
> rather than evaluated and passed.
```

### A.4 Replacement for the first and last bullets of §7 Governance

The section currently opens "No empirical test, market outcome, signal count, RFA, screen, surrogate
run, size check or optimization" and closes "The screen, if it is ever run, is never confirmation."
Both were true up to the freeze and are not now. Proposed:

```
- **Up to the freeze (2026-09-19): no empirical test, market outcome, signal count, RFA, screen,
  surrogate run, size check or optimization.** The size check and the screen ran afterwards, on
  2026-09-19 → 2026-09-24, under the frozen protocol and after G-S1 was appended.
```

and

```
- The screen has now been run, and **it is not confirmation.** Its report is labelled
  NON-CONFIRMATORY and feeds no gate. No Arm-2 variant result is evidence that Gann's documented
  method worked. All three primaries are retired, and under G-1 none may proceed to a confirmatory
  test.
```

The middle bullets of §7 stand unchanged, including "The exposure register was not edited. G-S1 is
operator-owned."

---

## B. Exposure register — `governance/exposure/RESEARCH_EXPOSURE_REGISTER.md` — OPERATOR ONLY

### B.1 Closing note, appended at the end of §10

**Do not add a second table row.** The screen's guard requires exactly one line in the committed
register beginning `| G-S1 |`, and a second such line makes it refuse. The note below is prose for
exactly that reason. The existing G-S1 row is left byte-for-byte as it is.

```
**The G-S1 read is complete — 2026-09-24.** The screen ran once, under the frozen protocol, with the
guard passing and the code identical to `357174a`. Panel content SHA-256
`06b375ef9385a8d20c1d41be02d84f32c30755eac16db7dd0c635961de3a35fd`. Evidence: blind size check
`docs/reports/ptms/PTMS_GANN_STAGE1_SIZE_CHECK.json` at `9382720` (recorded before unblinding), and
`docs/reports/ptms/PTMS_GANN_STAGE1_SCREEN_RESULTS.json` + `PTMS_GANN_STAGE1_SCREEN_REPORT.md` at
`2de0548`. Outcome: all three primaries — GF-1, GF-4T/R8, GF-10 — retired on the surrogate leg; the
report is labelled NON-CONFIRMATORY and feeds no gate.

**What this spends.** The equity EOD panel over 2011-03-25 → 2022-12-30 was already signal-spent for
this family before the read; it is now also spent by the Stage-1 hypotheses themselves, which were
fresh at the freeze and are not any more. 2023-01-02 → 2026-09-11 was **not** read by this screen; the
R-11 audit (2026-09-15) found it signal-spent for other reasons and the operator ruled it so on
2026-09-19. **No unread confirmatory window was opened or consumed here**, and none remains for this
construct family: under G-1 a construct retired on the surrogate leg may not proceed to a
confirmatory test.
```

### B.2 Header line

`**Last appended:** 2026-09-12 (P0.2–P0.4 complete)` is now two appends stale — it was not updated
when G-S1 went in at `cabaeba`. Proposed:

```
**Status:** v2 · **Opened:** 2026-09-12 · **Last appended:** 2026-09-24 (G-S1 read complete) · **Authority:** operator ruling
```

---

## C. What this draft deliberately does not do

- **It does not touch the freeze document.** Any edit to that file voids the SHA-256 recorded in
  checklist item 18 and in G-S1.
- **It proposes no protocol, code or statistic change.** The GF-4T/R8 calibration finding is recorded
  as a finding. Acting on it inside Stage 1 would be respecification after seeing results.
- **It opens no successor.** Whether anything follows Stage 1 is the operator's decision, and a
  successor would start its own pre-registration, disclose this screen as prior exposure under
  GR-1.5 (freeze §16), and face the fact that this family has no unread confirmatory window.
