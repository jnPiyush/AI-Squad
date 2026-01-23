# Code Review: {{title}}

**PR:** #{{pr_number}}  
**Reviewer:** AI-Squad Reviewer  
**Date:** [Date]

---

## Summary

**What changed:**
{{description}}

**Files changed:**
{{files}}

## Review Checklist

### ✅ Code Quality

- [ ] **SOLID Principles:** Code follows SOLID principles
- [ ] **DRY:** No code duplication
- [ ] **Naming:** Clear, descriptive names
- [ ] **Error Handling:** Proper try-catch blocks
- [ ] **No Warnings:** No compiler/linter warnings

**Comments:**
[Detailed feedback]

### ✅ Testing

- [ ] **Coverage:** Test coverage ≥80%
- [ ] **Unit Tests:** Comprehensive unit tests
- [ ] **Integration Tests:** Key integration scenarios covered
- [ ] **Test Quality:** Tests follow AAA pattern
- [ ] **Edge Cases:** Edge cases and errors tested

**Test Coverage:**
```
Overall: [X]%
New code: [X]%
```

**Comments:**
[Detailed feedback]

### ✅ Security

- [ ] **Input Validation:** All inputs validated
- [ ] **SQL Injection:** Queries parameterized
- [ ] **No Secrets:** No hardcoded credentials
- [ ] **Auth/Authz:** Proper authentication/authorization
- [ ] **XSS Prevention:** User input sanitized (if web)
- [ ] **Dependencies:** No vulnerable dependencies

**Security Findings:**
[List any concerns]

### ✅ Performance

- [ ] **Async/Await:** Proper async patterns
- [ ] **No N+1:** No N+1 query problems
- [ ] **Caching:** Appropriate caching used
- [ ] **Resource Disposal:** Proper resource cleanup
- [ ] **Algorithms:** Efficient algorithms

**Performance Notes:**
[Analysis]

### ✅ Documentation

- [ ] **XML Docs/Docstrings:** All public APIs documented
- [ ] **README:** Updated if needed
- [ ] **API Docs:** Updated if API changed
- [ ] **Comments:** Complex logic explained
- [ ] **Breaking Changes:** Documented

**Documentation Notes:**
[Feedback]

### ✅ Architecture

- [ ] **Structure:** Follows project structure
- [ ] **Separation of Concerns:** Proper separation
- [ ] **Dependency Injection:** Used appropriately
- [ ] **Interfaces:** Abstractions defined
- [ ] **No Circular Dependencies:** Clean dependency graph

**Architecture Notes:**
[Analysis]

## Detailed Feedback

### File: [filename]

**Line [X]:**
```[language]
[code snippet]
```

**Issue:** [Description]

**Suggestion:**
```[language]
[suggested code]
```

**Priority:** High/Medium/Low

---

### File: [filename]

[More feedback...]

## Positive Highlights

✨ **Well done:**
- [Positive aspect 1]
- [Positive aspect 2]

## Issues Found

| Severity | File | Line | Issue | Suggestion |
|----------|------|------|-------|------------|
| 🔴 High | [file] | [line] | [issue] | [fix] |
| 🟡 Medium | [file] | [line] | [issue] | [fix] |
| 🟢 Low | [file] | [line] | [issue] | [fix] |

## Performance Analysis

**Potential Bottlenecks:**
- [Issue 1]

**Optimization Opportunities:**
- [Opportunity 1]

## Security Analysis

**Vulnerabilities:**
- None found / [List issues]

**Recommendations:**
- [Recommendation 1]

## Test Results

**Test Execution:**
```
Tests run: [X]
Passed: [X]
Failed: [X]
Skipped: [X]
```

**Failed Tests:**
- [Test name]: [Reason]

## Recommendation

**Decision:** ✅ Approve / ⚠️ Request Changes / 💬 Comment

**Reasoning:**
[Explanation of decision]

**Must Fix (Blocking):**
1. [Issue 1]
2. [Issue 2]

**Should Fix (Non-blocking):**
1. [Issue 1]
2. [Issue 2]

**Nice to Have:**
1. [Suggestion 1]

## Next Steps

1. [Action 1]
2. [Action 2]

---

**Overall Assessment:**
[Summary paragraph]

**Merge Status:** Ready / Needs Changes / Blocked
