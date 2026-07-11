# [Milestone] Technical Review Report Template

**Milestone:** [Milestone ID] — [Milestone Name]

**Review Date:** [Date]

**Reviewer:** [Reviewer Name]

**Review Type:** Independent Technical Review

**Commit Under Review:** [git hash — or "uncommitted working tree"]

**Implementation Report:** [path to implementation report reviewed]

**Ledger Event:** [event # in `IMPLEMENTATION_LEDGER.md` recording this review]

---

## Executive Summary

[Brief summary of implementation scope, review findings, and final recommendation]

---

## Verification Performed

### Independent Verification Activities

List all verification activities that were independently executed by the reviewer:

- **Source code inspection:** [Description of files reviewed and scope]
- **Architecture compliance review:** [Description of specifications cross-referenced]
- **Documentation review:** [Description of documentation reviewed]
- **Import verification:** [Description of import verification performed]
- **Static analysis:** [Tools used or manual analysis performed]
- **Linting:** [Tools used and results]
- **Type checking:** [Tools used and results]
- **Test suite execution:** [Command executed + result] - OR mark as NOT performed
- [Other verification activities]

### Observed from Implementation Report

List all information that was observed from reports rather than independently verified:

- **Test suite execution:** NOT independently executed by reviewer. Test results observed from implementation report
- **Import behavior:** NOT independently executed. Observed from implementation report
- **Runtime behavior:** NOT independently executed. Observed from implementation report or test source code
- [Other observed information]

### Activities NOT Performed

List any verification activities that were NOT performed and the reason:

- **Independent test suite execution:** Tests not run by reviewer (reason if applicable)
- **Automated static analysis tools:** No tools run, manual inspection only
- **Linting:** No linting performed (reason if applicable)
- **Type checking:** No mypy or similar tool executed (reason if applicable)
- [Other activities not performed]

**Verification Methodology:** [Statement about what this review is based on]

---

## Files Reviewed

### Implementation Files

[Table or list of implementation files reviewed]

### Test Files

[Table or list of test files reviewed]

### Documentation Files

[Table or list of documentation files reviewed]

**Total:** [Total count]

---

## Findings

### Finding [N]: [Title]

**Severity:** [Critical/High/Medium/Low]

**Category:** [Category]

**Description:**

[Detailed description of the finding]

**Files Affected:**

- [File:line]
- [File:line]

**Rationale:**

[Detailed rationale explaining why this is a problem]

**Recommended Correction:**

[Specific recommended fix with code examples if applicable]

---

## What is Architecturally Correct

### [Category Name]

[Description of architectural compliance with specific component verification]

### [Category Name]

[Description of architectural compliance with specific component verification]

---

## Test Quality Assessment

### Test Coverage [If tests reviewed]

| Test Category | Tests | Status | Verification Method |
|---------------|-------|--------|---------------------|
| [Category] | [Count] | [Observed/Executed] | [Method] |
| [Category] | [Count] | [Observed/Executed] | [Method] |
| **Total** | **[Count]** | **[All Passing/Observed]** | [Method] |

### Test Quality Assessment [If tests reviewed]

[Assessment of test quality based on source code inspection]

### Test Completeness [If tests reviewed]

[Verification of test completeness against acceptance criteria]

---

## Documentation Assessment

### [Documentation Section] Review

**[Document]:** [Path]

**Assessment:** [Quality assessment]

**Strengths:**

1. [Strength]
2. [Strength]

**Weaknesses (if any):**

1. [Weakness]
2. [Weakness]

---

## Code Quality Assessment

### [Category]

[Assessment of code quality with verification method]

### Code Quality Verification

| Criterion | Verification Method | Status |
|-----------|---------------------|--------|
| [Criterion] | [Method] | [Status] |
| [Criterion] | [Method] | [Status] |

---

## Final Recommendation

**Recommendation:** [PASS / PASS WITH MINOR FIXES / FAIL — semantics defined in `IMPLEMENTATION_LEDGER.md` §Certification Verdicts; PASS WITH MINOR FIXES requires a fix-verification addendum before certification]

**Rationale:**

[Detailed rationale for recommendation]

**Certification Readiness:**

[Assessment of readiness for certification]

**Path to Certification:**

1. [Step 1]
2. [Step 2]
3. [Step 3]

---

## Summary

**Total Findings:** [Count]

**Severity Breakdown:**
- Critical: [Count]
- High: [Count]
- Medium: [Count]
- Low: [Count]

**Architectural Compliance:** [Status] [Verification method]

**Code Quality:** [Status] [Verification method]

**Test Quality:** [Status] [Verification method]

**Documentation Quality:** [Status] [Verification method]

**Recommendation:** [Final recommendation]

**Verification Scope:** [Statement about verification scope and methodology]

---

## Appendices (if applicable)

### Appendix A: [Title]

[Additional documentation if needed]

### Appendix B: [Title]

[Additional documentation if needed]

---

**End of Review Report**

---

*Template usage guidance (verification method vocabulary, verdict semantics, traceability rules) lives in `TECHNICAL_REVIEW_GUIDELINES.md`. Do not copy guidance into instantiated reports.*