# MM11 — Removal Ledger

**Governing document:** `docs/reports/MM11_IMPLEMENTATION_SPECIFICATION.md` §1.5 (Governance Model — Controlled Decommissioning)
**Purpose:** item-level audit trail for every deletion, relocation, or retention-with-justification decision made during MM11. This is the evidentiary basis for the Platform v1.0 declaration (spec §4, item 12) — not a summary, the source the summary is built from.

**Rule:** an entry is added *at the time* an item is removed, not reconstructed afterward. A slice is not complete if code was deleted but no entry exists here for it, regardless of test status. See spec §1.5 for the four-part proof each entry must satisfy before it is written.

**Status:** empty — MM11 execution has not started. Slices append entries below as they run.

---

## How to file an entry

Copy this template per deletion target (one item — one file, one class, one function, one DDL table — per entry; do not batch unrelated items into one entry even if removed in the same commit):

```
### <slice id> — <item name> (<file(s) or table name>)

- **What it was:** <one line — what the code/table did>
- **Disposition:** REMOVED | RELOCATED | RETAINED-WITH-JUSTIFICATION
- **Gate 1 — proof of non-use:**
  - Python-import grep result: <command + result, or "N/A — docs-only">
  - String-literal grep result: <command + result>
  - (If a guarded/reachable-in-principle branch, not a fully dead file: evidence the guard is always false in production, citing composition-root construction sites)
- **Gate 2 — proof of behavior preservation:**
  - Full-suite result BEFORE change: <pass count / fail count>
  - Full-suite result AFTER change: <pass count / fail count>
  - Diff: <identical pass/fail sets, or explain any change>
  - Characterization test added/pointed to (if constructor signature or reachable branch): <test name, or "N/A — provably dead file">
- **Gate 3 — full suite passes:** <confirm — same numbers as Gate 2 "AFTER">
- **Gate 4 — why:** <one sentence: which Planned item / spec finding justified this>
- **Change reference:** <commit hash / PR, once available>
- **Slice:** <MM11.1 | MM11.2 | ... >
- **Date:** <YYYY-MM-DD>
```

For a **RETAINED-WITH-JUSTIFICATION** outcome (e.g. MM11.5 finding a live caller, or MM11.4b confirming `option_chain_snapshot` is options-dashboard-serving), file the same entry shape with Gates 1–3 showing *why* the item is NOT dead, and Gate 4 explaining the decision to keep it. Retention decisions are still required ledger entries — §1.5 gate 4 documents decisions, not only deletions.

---

## Entries

*(none yet — execution not started)*

---

## MM11.7 Reconciliation Record

To be completed at milestone close (spec §2, MM11.7, acceptance criterion 2): a line-for-line cross-check of the full pre-MM11 → post-MM11 tree diff against the entries above. Every deletion in the diff must have an entry; every entry must correspond to an actual change in the diff. Mismatches in either direction block the Platform v1.0 declaration until resolved.

- **Reconciliation performed:** not yet
- **Result:** —
