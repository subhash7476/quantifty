# Keel — Jev Decision-Harness Review (external, 2026-09-25)

**Source.** Promoted by @leopardracer (x.com, 2026-09-24) quoting @Av1dlive's article
"How to Build Agentic Harness using Jev (Builder's Guide)" (2026-09-23, ~590K views).
Repo: `github.com/codejunkie99/keel`, article snapshot `3fc24b0e` (Keel 0.2.0).
Repo facts at read time: created 2026-09-22, 3 commits on main, 116 stars, MIT, Rust/GPUI,
macOS 15 / Apple Silicon only. Read-only review: nothing was cloned or run; key files
(`jev_routing.rs`, `decision_mode.rs`, `dsh/agent-loop/src/agent.rs`, `jev-core/src/lib.rs`,
`docs/decision-architecture.md`, `docs/build-report.md`) fetched via `gh api`.

## What it is

A fork of an existing coding workspace ("Avid") that adds a **selector** — local Laya
(Core ML, default) or hosted TypeSafe Jev (`jev-1.13.0`, opt-in) — at exactly two points:

1. **Intake routing** (`jev_routing.rs`). For a *new, unpinned* task only, the host builds
   ≤16 eligible provider/model routes (≤8 for Laya), gives them opaque ids `route_N`, and
   asks the selector for one id or abstention. Pinned routes, resumed sessions, and any
   request carrying provider-specific options bypass it.
2. **Per-step focus** in the embedded DeepSeek loop (`agent.rs`). Four fixed choices —
   `inspect` (read/grep/glob), `implement` (+write/edit, no shell), `verify` (+bash, no
   write/edit), `answer` (no tools). The chosen id maps to a host-owned tool bundle; the
   step's schema list is filtered to that bundle.

## What the code actually enforces (verified in source)

| Claim in the posts | In code? |
|---|---|
| Selector returns only an id from a host list | Yes — unknown id → `Rejected`, "Unknown route ID", original harness kept |
| Host rechecks before running | Yes — route list re-probed, fingerprint compared, provider still installed+enabled, model still listed, reasoning level still supported; 45 s expiry on prepared actions |
| Stale bundle falls back | Yes — bundle recomputed against current tool schemas; mismatch → `stale_tool_bundle`, step runs with the full tool set |
| A pick never grants permission | Yes — shell permissions / user approval path unchanged |
| Fail closed | Yes — unreadable/malformed mode file → `Normal` (no selector); Jev key missing → no Jev |
| Abstention thresholds | Jev: `min_confidence 0.35`, `min_fit 0.8`; call budget 1 at intake, 8 per agent loop |
| Decision receipts | Yes — versioned `DecisionEvent`: candidates, result, confidence/fit, validation, fallback, observed outcome |
| "Self-improving" | **No.** No replay, scenario, or eval code exists in the tree. The article itself says it is "a proposed evaluation design"; receipts are just logged |
| Cost/speed ("200x faster, 400x cheaper", @cyrilXBT) | **Not in this repo.** Build report: "did not make a paid live TypeSafe call"; article: "we haven't demonstrated that payoff" |

## Assessment

- **Engineering is honest and conservative.** The article and docs are more careful than
  the promotional quote-tweets — every performance claim is explicitly disclaimed. The
  guard pattern (opaque id → re-validate against a freshness fingerprint → fallback that is
  recorded as a fallback, not a win) is sound and well tested (1,477 tests claimed).
- **The selector's value is unmeasured.** No evidence that Laya/Jev routing or focus
  selection beats "Normal" mode on any task. The notable weakness: when focus selection
  abstains or goes stale, the step runs with *all* tools — so the safety property is
  "never more than before", not "narrower".
- **Not usable here.** macOS-only GUI app; this platform is Windows/Python. Nothing to install.

## Relevance to this platform

The pattern is already ours, in a different domain — it is essentially the platform's
execution contract restated for LLMs:

| Keel | This repo |
|---|---|
| Selector picks id; host owns execution | Strategies emit `SignalEvent`; `core/execution/` owns sizing/risk/broker (Principle 1, 3) |
| Recheck freshness before acting | Stale-mark / stale-fact guards, preflight BLOCK checks |
| Fallback recorded, not counted as a win | RFA/gate discipline: abstentions and fallbacks are reported, not hidden |
| Receipts → replay → human-approved change | Audit-first (Principle 5); frozen declarations; operator approval |

**If an LLM/Jev layer is ever added** (e.g. an explainer or a triage step), copy three
concrete mechanics: (1) opaque ids with a fingerprint + expiry on each prepared action,
re-validated after the model responds; (2) a single enum of validation outcomes
(`Accepted / Rejected / Stale / Expired / Unauthorized`) written to an audit table;
(3) a call budget reserved atomically before the network call. None of this justifies
building such a layer now — consistent with JEV-NMS-1's DEVELOPMENT NULL and the
no-speculative-abstraction rule.

**Verdict:** worth reading as a reference for guarding model decisions; no edge, no tool,
no evidence for the cost/performance claims made in the promoting posts.
