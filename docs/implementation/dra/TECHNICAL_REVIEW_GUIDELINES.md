# Technical Review Guidelines

**Companion to:** `TECHNICAL_REVIEW_TEMPLATE.md`

These guidelines govern how the review template is used. They are reference material — do NOT copy them into instantiated review reports.

---

## Purpose of the Verification Performed Section

The Verification Performed section explicitly records what was independently verified by the reviewer versus what was observed from implementation reports. This distinction is critical for governance and auditability.

Every review report MUST include a Verification Performed section with the three subsections:

1. Independent Verification Activities
2. Observed from Implementation Report
3. Activities NOT Performed

This provides a clear audit trail of what was independently verified and what was observed.

---

## Verification Method Categories

**Reviewed:** Documentation or reports were read and assessed for completeness, accuracy, and quality.

**Inspected:** Source code was manually examined for compliance, correctness, and quality issues.

**Observed:** Information was taken from implementation reports or other documentation without independent verification.

**Verified by execution:** Activity was independently executed by the reviewer (e.g., running tests, imports, static analysis tools).

### When to Use Each Verification Method

| Activity | Verification Method |
|----------|---------------------|
| Source code review | Inspected |
| Documentation review | Reviewed |
| Test results from implementation report | Observed |
| Independent test execution | Verified by execution |
| Import verification (manual) | Inspected |
| Import verification (executed) | Verified by execution |
| Static analysis (manual) | Inspected |
| Static analysis (tools) | Verified by execution |
| Linting | Verified by execution (if performed) |
| Type checking | Verified by execution (if performed) |

---

## When Tests Are NOT Independently Executed

If tests were not independently executed by the reviewer:

1. Clearly state "NOT independently executed by reviewer" in the Observed from Implementation Report section
2. Clarify that test results are "Observed from implementation report"
3. Add a note in the Final Recommendation section: "Independent test execution should be performed as part of the certification process"
4. Do not claim that tests were "Verified" — they were "Observed"

---

## Precision in Terminology

**Verified:** Use only when the reviewer independently performed the verification activity (executed code, ran tools, performed manual inspection and confirmed correctness).

**Inspected:** Use for manual examination of source code or documentation.

**Reviewed:** Use for examination of documentation or reports.

**Observed:** Use for information taken from reports without independent verification.

---

## Activities That Should Be Executed (Preferred)

For a complete technical review, the following activities should ideally be independently executed:

- Test suite execution (run pytest and verify results)
- Import verification (execute package imports)
- Type checking (run mypy or similar)
- Linting (run flake8, pylint, or similar)
- Static analysis (run appropriate tools)

## Activities That May Be Observed

The following may be observed from reports if execution is not feasible:

- Performance benchmarks (if not environment-independent)
- Integration test results (if dependent on external systems)
- Deployment verification (if not available in test environment)

---

## Recommendation Verdicts

The Final Recommendation must be one of three verdicts. Their downstream semantics — including the fix-verification addendum process for PASS WITH MINOR FIXES — are defined authoritatively in `IMPLEMENTATION_LEDGER.md` §Certification Verdicts. In brief:

- **PASS** — certified as-is; certification event appended to the ledger.
- **PASS WITH MINOR FIXES** — non-blocking findings must be corrected; the original reviewer verifies corrections and appends a fix-verification addendum to the review report; certification follows the addendum. No full re-review.
- **FAIL** — returns to development; full re-review required after rework.

---

## Traceability

Every instantiated review report must fill in the header traceability fields (Commit Under Review, Implementation Report, Ledger Event) so the ledger, the review, and the code state cross-reference each other. If the work under review is uncommitted, state "uncommitted working tree" and record the commit hash in the fix-verification addendum or certification event once committed.

---

**End of Guidelines**
