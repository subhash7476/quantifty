# JEV-NMS-1 — Amendment 3: L3 Operator Ruling (A3)

**Status: FROZEN.** This record amends nothing sealed at F₁ or A2. It freezes the operator's
ruling on the two questions that `JEV_NMS_1_L3_REPORT.md` §4.3 and §4.4 left open.

- L3 is accepted as complete and is not re-run.
- The L3 run record and the L3 report are unchanged.
- No Jev call was made for this amendment.

## 1. Operator ruling (verbatim)
> 1. Exact argmax ties are resolved using the frozen §8 class order.
> 2. The L3 repeatability baseline is the full 50-state D5 agreement, not the 20-state D6
>    subset.
>
> Therefore freeze:
> - L3 baseline = 46/50 = 0.92
> - L5 halt threshold = 0.82 (baseline minus 10 percentage points)
> - D6 20/20 remains recorded descriptively, but is not the L3 baseline.

## 2. Frozen wording
**A3-1. Arg-max tie rule.**
- Exact argmax ties are resolved using the frozen §8 class order, `trending_up`,
  `trending_down`, `range_bound`, `disorderly`. This is the F₁ configuration's
  `labels.classes_order`; the same order is fixed by §11A item 2 and the template criteria.
- The arg-max of a Jev probability vector is the **first class in that order whose
  probability equals the maximum probability**.
- The order is always taken from this list. It is never taken from the key order of a stored
  or parsed JSON object.

**A3-2. L3 baseline.**
- The L3 repeatability baseline is the full 50-state D5 argmax agreement under A3-1:
  **46/50 = 0.92**.
- The 20-state D6 canary subset agreement, **20/20**, remains recorded descriptively. It is
  not the L3 baseline.

**A3-3. L5 halt threshold.**
- The threshold is 46/50 − 10/100 = **41/50 = 0.82**.
- L5 halts (INVALID) if and only if L5 argmax agreement is **strictly less than 41/50**. L5
  argmax agreement means the canaries' agreement with their L3 replicate-0 arg-max, each taken
  under A3-1.
- The comparison uses exact fractions. In binary floating point, 0.92 − 0.10 evaluates to
  0.8200000000000001, which is why exact fractions are used.
- For the 20-canary L5 replay, this halts at 16/20 = 0.80 or fewer. It does not halt at 17/20
  = 0.85.

## 3. Rationale and how the ruling binds
- **Why the configuration's class order:** "§8 class order" is bound to
  `labels.classes_order`, the sealed class order in the configuration's §8 (`labels`) block.
  The block's `precedence` list (`disorderly`, `trending`, `range_bound`) is not a total order
  over the four classes, because it does not rank `trending_up` against `trending_down`. It
  therefore cannot resolve every tie.
- **Effect on the recorded L3 tie:** state 2023-05-02 12:30, replicate 1, has `trending_down`
  = `range_bound` = 0.42. Under A3-1 it resolves to `trending_down`, which disagrees with
  replicate 0's `range_bound`. This reproduces the recorded 46/50 exactly, and it matches the
  response's own `choice`. The precedence list would also have given `trending_down` here.
- **A hazard A3-1 closes:** `l3_step5.json` stores probabilities with alphabetically sorted
  keys. A naive `max(dict)` on the stored artifact therefore breaks this tie toward
  `range_bound`, which would give 47/50. A3-1 excludes that reading, and the tests assert it.

## 4. Sealed addendum and references
- The machine-readable delta is `governance/jev_nms_1/config_amendment_3.json`, SHA-256
  **`d4dfe8614326aca885efdd978f28c3c366c29127d3edf20c230ef071c6455e63`**.
- This hash is pinned in `scripts/jev_nms_1/rulings.py` (`EXPECTED_A3_SHA256`).
- `load_a3()` refuses the addendum if its hash differs, or if any file it references differs:

| Reference | File | SHA-256 (unchanged) |
|---|---|---|
| F₁ configuration | `governance/jev_nms_1/config.json` | `9ed5dcaec115a93afbbc6d0edb51295efeea2966fe1fb49701d3aec59f967fee` |
| A2 addendum | `governance/jev_nms_1/config_amendment_2.json` | `b9640bf22d2f1d53ca913654863280fa54087db00c2cd26675c1343ca9395484` |
| Protocol | `docs/reports/jev/JEV_NMS_1_PROTOCOL.md` | `7e7f848d1f1664a34213dad8cb84c0e98a72833e621f719e64007a6f3af036a3` |
| Amendment 2 | `docs/reports/jev/JEV_NMS_1_AMENDMENT_2.md` | `2731a6254521520034e97fc542fa2253cc1a92713fed170cd46d0a58fbde40ae` |
| L3 run record | `data/jev_market_state/l3_step5.json` | `cb67b5551371ce5d85c4085cff004c0a70b557d411654f309605f0a90fc72c35` |
| L3 report | `docs/reports/jev/JEV_NMS_1_L3_REPORT.md` | `286317a3827f43c8c8e516824fcd3a7c3ffcbe3a2e2279d0a2405b171bc9f0f2` |

Also unchanged:
- F₁ freeze record: `d051b538…`.
- A2 freeze record: `eb5d7003…`.
- The four templates.
- The existing A2 seal check, `load_seal()`, which still passes.

The authoritative sealed set is now the F₁ protocol and configuration, plus Amendment 2 and
its addendum, plus this A3 record and its addendum.

## 5. Tests
`tests/jev_nms_1/test_a3_ruling.py` has 13 deterministic tests:
- the tie order equals the sealed `labels.classes_order`, the transport classes and the
  ruling's order;
- every two-way tie, and the four-way tie, resolves to the first class in that order;
- a vector with no tie returns its maximum;
- the recorded L3 tie state resolves to `trending_down`, where dict order would give
  `range_bound`;
- recomputing the recorded L3 run under A3-1 gives 46/50 overall and 20/20 on the canaries;
- the threshold equals exactly 41/50 = 0.82;
- the halt boundary is strict and exact: 41/50 does not halt, 40/50 halts, 17/20 does not,
  16/20 does;
- a tampered addendum is refused.

Full relevant suite (`tests/jev_nms_1`, `tests/market`, `test_market_session_cas.py`,
`test_cas_rules.py`, `-W error`): **240 passed, 1 skipped, 0 failed**. The skip is the CSMP
calendar conformance test, whose store is absent from this worktree.

## 6. Ledger
An `a3_ruling` event is appended to `ledger.jsonl`, recording the addendum's and this
record's SHA-256 values and the frozen baseline and threshold. No earlier line is changed.

## 7. Scope
- **Not done:** no Jev call, no development, P or L5 call, no fit and no ΔLL.
- **Unchanged:** the protocol, the F₁ configuration, the A2 artifacts, the templates, the
  features, the draws, the cache and every stage artifact.
- **Next step:** development needs separate operator authorization.
