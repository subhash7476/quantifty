# JEV-NMS-1 — Amendment 2: Reproducibility Definitions and Session-Calendar Dependency Contract

**Status:** FROZEN at the Amendment-2 seal (A2). Recorded in `JEV_NMS_1_A2_FREEZE_RECORD.md`.
**Amends:** `docs/reports/jev/JEV_NMS_1_PROTOCOL.md` (SHA-256
`7e7f848d1f1664a34213dad8cb84c0e98a72833e621f719e64007a6f3af036a3`), which stays
byte-identical. The amended protocol is **the frozen protocol + this amendment**; where this
amendment defines something the protocol left undefined, this amendment governs. It changes
no rule the protocol already defines.
**Configuration:** the F₁ configuration `governance/jev_nms_1/config.json` (SHA-256
`9ed5dcaec115a93afbbc6d0edb51295efeea2966fe1fb49701d3aec59f967fee`) stays byte-identical and
immutable. The Amendment-2 definitions are sealed in the delta addendum
`governance/jev_nms_1/config_amendment_2.json`. The authoritative post-amendment
configuration is **F₁ configuration + Amendment-2 addendum**.
**F₁:** unchanged, **2026-09-18**. The A2 seal is a new seal event. It does not move F₁,
H-exposed, the buffer or P.
**Lineage:** F₁ freeze (`1d199cb`, record `8d13bac`) → §28 step 1 stopped on platform
dependencies → blocker report → platform calendar (`b5620cd`, `02d1c87`, `8696a83`) → merge
into this branch (`a3107a3`) → operator rulings G-1..G-6, C-1..C-3, L2 overlap, F₁, L2
population, 2023-03-01 disclosure, configuration sealing (all 2026-09-18) → this amendment.

Tags: **[R]** repository convention · **[A]** approved decision · **[D]** disclosure.

---

## A2-0. Scope [A]
Amendment 2 only defines what the frozen text leaves open, so that the §23 draws and the
§4/§7 calendar lookups are deterministic. It does **not** change the research question,
the eligibility universe or its items, the timestamp grid, features, labels, templates
(text or hashes), baselines, the primary endpoint, inference, nulls, stopping rules,
failure conditions or the POSITIVE criterion. Nothing here was chosen after seeing any Jev
output, draw, eligibility list or fitted quantity: none exist.

## A2-1. G-1 — Random draws [A]
- **Generator:** Python standard-library `random.Random(42)`, under the pinned Python
  3.13.5 (the `random.sample` / `random.choice` algorithms are version-specific).
- **One stream per draw:** every draw below gets its own fresh `random.Random(42)`
  instance. No stream is shared or reused, and no draw depends on execution order.
- **Population ordering:** before sampling, every population is sorted ascending by its
  canonical key. Session populations are keyed by session date. State populations are
  keyed by (session date, slot time).
- **No other ordering source:** nothing may depend on filesystem, DuckDB, dict or set
  iteration order.
- **Seed order:** the order of the sampler's output. "First n in seed order" means the
  first n elements of that output.
- **Without replacement:** every `random.sample` draw is without replacement.
- **Manifests:** each draw's manifest (population size, population SHA-256, k, ordered
  output) is persisted and hashed before any Jev call (§28 steps 2 and 5).

| Draw | Population (sorted) | Procedure | Stream |
|---|---|---|---|
| D1 development | Otherwise-eligible D-eval sessions (§4 R-1) | `random.sample(pop, 100)` | own |
| D2 secondary-horizon subset | Derived: no new stream | First 30 of D1 output | none |
| D3 S0 | Eligible D-fit sessions | `random.sample(pop, 5)`; states = each session × {10:00, 14:30} → 10 states | own |
| D4-2023 / D4-2024 / D4-2025 L2 sessions | Eligible sessions in D-fit ∪ D-eval whose date falls in that calendar year (A2-2) | `random.sample(pop_year, 30)` per year | one per year |
| D4t L2 timestamps | The 90 L2 sessions, sorted by date | For each session in date order: `rng.choice(slots)`, slots = the ten §5 times ascending | own |
| D5 L3 | All eligible states in D-fit ∪ D-eval (eligible session × ten slots), excluding every D3 state, every D4/D4t state and every development state (each D1 session × ten slots) | `random.sample(pop, 50)`, after D1, D3, D4 and D4t are fixed | own |
| D6 canaries | Derived: no new stream | First 20 of D5 output | none |

- **Exclusions:** the only exclusions are the L3 exclusions above. L3 must not overlap S0,
  L2 or development.
- **L2 may overlap development:** L2 states may coincide with development states. No
  L2/development exclusion exists, and S0, L2 and development are not mutually excluded.
- **C-2, the L3 pool:** the "eligible development-state population" is the complete union
  of eligible states in D-fit ∪ D-eval. It is not D-eval only, and it is not only the
  100-session development sample. This is the frozen §23 / `draws.l3.pool` population.
- **"Eligible"** means eligible under §4 as bound by A2-7. **"Otherwise-eligible"** keeps
  its §4 R-1 meaning (passing every item except 7).

## A2-2. L2 population — resolution of the §10/§23 ambiguity [A]
§23 draws "30 eligible sessions per calendar year 2023, 2024, 2025". §10 places L2 draws
inside D-fit and D-eval. These are reconciled as follows:
- The L2 population is the eligible sessions within the defined development sets
  D-fit ∪ D-eval, **stratified by calendar year**.
- 2023 L2 eligibility starts at the frozen D-fit boundary, **2023-03-01**. January and
  February 2023 lie outside every defined set and are **not evaluated** for eligibility,
  for L2 or any other purpose.
- The 2023 draw takes 30 eligible sessions from the 2023 portion of D-fit. The 2024 draw
  takes 30 from D-fit's 2024 portion, and the 2025 draw takes 30 from D-eval.
- §28 step 1 evaluates eligibility only for dates inside a defined set.

This resolves an existing ambiguity. It is not a redesign, and the D-fit boundary is
unchanged.

## A2-3. G-2 — B2 selection of C [A]
- C ∈ [0.01, 0.1, 1, 10] is selected **independently for each horizon** (5, 15, 30),
  exactly as for B3.
- Selection uses the same five contiguous, date-sorted, session-grouped D-fit folds shared
  with B3 (§14).
- The criterion is mean out-of-fold log-loss (ln). Ties within 1e-12 go to the first value
  in list order.
- The selected C is refit on all of D-fit for that horizon.
- All other B2 settings are the frozen §14 settings.

## A2-4. G-3 — S0 and L3 [A]
- **S0 (C-1):** "one request using the h = 15 template" identifies the template and
  request type, not the call count. §23 stands: 5 D-fit sessions × {10:00, 14:30} = 10 S0
  requests (D3), each using the sealed **h15** template. S0 is unscored and checks parsing
  only (§11A item 9).
- **L3 template:** the sealed **h15** template.
- **L3 draw:** the unit is individual market states (session × slot), 50 states (D5).
  Each state is sent twice, as frozen.
- **L3 replicates:**
  - Replicate 0 is authoritative.
  - Replicate 1 is a deliberate, non-authoritative cache-bypass record under
    `canonical_request_hash + run_id + replicate_index` (§12).
- **Canaries:** the first 20 L3 states in seed order (D6), unchanged.
- **Templates:** no text or hash changes. This amendment only names which frozen template
  each stage uses.

## A2-5. G-4 — Quantile method [A]
Every preregistered quantile, percentile, median or quantile cut anywhere in JEV-NMS-1 is
computed with NumPy `numpy.quantile` / `numpy.percentile` using `method="linear"`, under
the pinned numpy **2.4.4**. A median is the 0.5 quantile under the same method. This
covers:
- §8: E*_h (median ER_f), Z*_h (70th percentile of |z|) and V*_h (75th percentile of v);
- §9: the 60 volatility-scale constants S_h(t) and S^trail_h(t) (medians);
- §20: the B3* maximum-probability tercile cuts (the 1/3 and 2/3 quantiles);
- §21: the coverage quantile cuts;
- any other preregistered quantile, which uses the same rule.

*Clerical note:* the operator ruling listed the ER median and the |z| and v percentiles
under "§20". The protocol defines them in §8. The ruling's "all quantiles anywhere" governs,
so the section label changes nothing.

## A2-6. G-5 — B2 standardization: CLOSED WITHOUT AMENDMENT [A][D]
The literal frozen wording stands: B2 standardizes with the full-D-fit mean and SD,
including inside cross-validation. This is recorded as a disclosed methodological choice
that affects model selection only. It is not a protocol defect.

## A2-7. G-6 — Previous trading session and the session-calendar dependency contract [A]
**G-6 ruling:** "the previous trading session" (§4 item 8; §7 C_prev) is the immediately
preceding session on which NIFTY actually traded. That includes regular weekday sessions,
Muhurat and other special sessions, disaster-recovery sessions and scheduled weekend
sessions.

**Platform implementation.** The contract binds to these commits on `main`, merged into
this branch at `a3107a32444a8cfcfbf8e2a25b78b3e3da33c436`:
- `b5620cd2190163474ec4103b23fb728da3ef914e`: ordinary NSE weekday holidays for 2023–2025
  with circular provenance;
- `02d1c87ac10fd41a8c65dd2237a9b43d651d9d6f`: the merge of those holidays into `main`;
- `8696a830790b754ffb690028ddce3eaede7dafcd`: `SPECIAL_SESSIONS`, `bar_labeling` and
  `trading_calendar`.

**Dependency contract.** JEV-NMS-1 implements no calendar logic of its own. Each item
binds as follows:

| Frozen item | Binding |
|---|---|
| §4 item 1 | The session file exists, and `d.weekday() < 5` and `d not in core.market.nse_holidays.NSE_HOLIDAYS`, read literally. `NSE_HOLIDAYS` remains the ordinary weekday-holiday source. Weekend sessions (additional sessions) therefore fail item 1 as observations, while remaining valid previous sessions. `is_session` is not an eligibility test, and no eligibility is encoded into it. |
| §4 item 3 | The first Nifty bar is stamped 09:15 **and** `core.market.bar_labeling.labeling_of(first_stamp, d) == "native"`. Any other first stamp is excluded, not converted. If `labeling_of` raises `UnknownLabeling` for a 09:15 first stamp, that case is outside this contract and stops for an operator ruling (A2-11). It is not silently treated as an exclusion. |
| §4 item 4 | `d not in core.market.session_schedule.SPECIAL_SESSIONS`. `SPECIAL_SESSIONS` controls **schedule overrides only**; it never decides whether a date is a session. |
| §4 item 8 and §7 C_prev | `p = core.market.trading_calendar.previous_session(d)`, the greatest date strictly before d on which NIFTY actually traded, including additional and special sessions. Item 8 holds iff p's 1m file has a `NSE_INDEX\|Nifty 50` bar stamped 15:29 with close > 0 (frozen wording), and C_prev is that bar's close. If the file is absent, has no Nifty bars or has no 15:29 bar, item 8 fails, mechanically. Nothing may substitute for the bar: no official or bhavcopy close, no other bar and no other date. |
| Coverage | `trading_calendar.OutsideCoverage`, from `previous_session` or `is_session`, is **fatal**. It stops the pipeline; it is never an exclusion. Declared coverage is 2023-01-01..2026-12-31. |
| Prohibited fallbacks | No weekday arithmetic, calendar-day arithmetic, previous-store-file inference, previous-eligible-session inference, or `sessions_after` in place of `previous_session`. |

**Mechanical consequences** (not rule changes):
- A Muhurat or DR predecessor has no 15:29 bar, so the next session fails item 8. This
  applies to 2023-11-13, 2024-03-04, 2024-05-21, 2024-11-04 and 2025-10-23.
- 2024-01-23 and 2025-02-03 have full-session Saturday predecessors that do have 15:29
  bars.
- 2026-02-02 fails item 8 (A2-9) and 2023-03-02 fails item 8 (A2-8).

**[D] Prospective coverage.** P runs past 2026-12-31. A P session in 2027 raises
`OutsideCoverage` until the platform calendar declares 2027 coverage: holidays, special
closures, additional sessions and special-session schedules. Extending coverage is a
platform-data change on `main`. It does not amend this protocol, and it must land before
any P session in the uncovered year.

## A2-8. Disclosure correction — 2023-03-01 [D]
Protocol §10 states "2023-03-01 is the first native session after the Feb-2023 hole". That
statement is factually incorrect:
- The 2023-03-01 1m file exists (202 symbols) but contains **no Nifty 50 bars**, so
  2023-03-01 fails eligibility mechanically.
- The first Nifty session after the hole is **2023-03-02**.
- `previous_session(2023-03-02) = 2023-03-01`, which has no Nifty 15:29 bar, so
  **2023-03-02 fails item 8**.

This is a disclosure correction only. The D-fit boundary stays **2023-03-01**. No bar is
manufactured, and item 8 is unchanged.

## A2-9. H-exposed item-8 audit [D]
This is a diagnostic, not an eligibility artifact. It was run read-only on 2026-09-18
against the 1m store with the merged `trading_calendar` (`a3107a3`).

**Scope:** every date with `is_session(d)` in 2026-01-01 → 2026-09-18: **177 sessions**,
checked for item 8 alone, independently of the other items.

**Result: exactly one item-8 failure, 2026-02-02 (Monday).**
- Its previous session is 2026-02-01 (Sunday), a member of `ADDITIONAL_SESSIONS` (not of
  `SPECIAL_SESSIONS`).
- The 2026-02-01 file holds 102 symbols, each with a 15:29 row, but **no Nifty 50 bars**,
  so there is no Nifty 15:29 bar and item 8 fails mechanically.
- 2026-02-01 is an actual NIFTY session. The missing Nifty capture is a store defect, not a
  closure.
- No synthetic or official-close replacement is made, and item 8 is unchanged.

**Context, not an item-8 failure:** the 2026-09-18 (F₁ date) 1m file was not yet present
when the audit ran. By operator ruling this does not move F₁, and no eligibility artifact
was created.

## A2-10. Environment addendum [R][A]
There are no new, changed or unverified dependency versions. The F₁ pins stand unchanged
(`governance/jev_nms_1/environment.json` `7d86acb5…84ca62`,
`requirements-jev.txt` `64b00470…b18655`):
- Python 3.13.5 (tags/v3.13.5:6cb20a2, MSC v.1943, AMD64);
- numpy 2.4.4, pandas 2.3.3, scikit-learn 1.8.0, scipy 1.17.0, duckdb 1.4.3;
- OpenSSL 3.0.16 (11 Feb 2025);
- HTTP client stdlib `http.client.HTTPSConnection`, with the TypeSafe SDK not installed;
- endpoint `POST https://api.typesafe.ai/v1/systemone`, API v1, model `jev-1.13.0`;
- 20 s timeout per attempt and the frozen transport-only retry policy.

Recorded, not pinned: Windows-11-10.0.22000-SP0, AMD64,
`C:\Program Files\Python313\python.exe`, git 2.51.2.windows.1.

The merged platform modules (`nse_holidays`, `session_schedule`, `bar_labeling`,
`trading_calendar`) import only the Python standard library and each other, and add no
third-party dependency. G-1 (`random`) and G-4 (`numpy.quantile`, `method="linear"`) bind
to the pinned Python and numpy.

## A2-11. Governance [A]
- The F₁ artifacts (protocol, F₁ configuration, the four templates, `environment.json`,
  `requirements-jev.txt`) and the F₁ freeze record are immutable. Their hashes must still
  match `JEV_NMS_1_F1_FREEZE_RECORD.md`.
- §26's configuration-seal condition applies to the F₁ configuration **and** to the
  Amendment-2 addendum.
- Implementation may implement the amended protocol but may not alter it. Any ambiguity
  found during implementation stops work and returns to the operator. Any further change
  requires a new formal amendment and a new seal.
- After the first Jev call, no D-fit fitting, hyperparameter selection, template,
  protocol, amendment or configuration modification is permitted (§26, §28).
- §28 begins only after the A2 freeze record is committed.
