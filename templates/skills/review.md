# SKILL: Code Review and Quality

Evidence-first, catalog-driven review. Every change gets reviewed before done. No exceptions.

## Step 1 — Read Gate Evidence First
Read `.codestudio/evidence/<TASK>/gate-summary.json`.
- **Do NOT re-check** what gates already proved: coverage %, lint errors, type errors, build success
- **DO focus on** what gates cannot prove: logic errors, design gaps, missing edge cases, security issues

## Step 2 — Walk the Defect Catalog
Read `.codestudio/catalogs/defects-*.md`.
Work each applicable entry against the diff. Flag any match.

## Step 3 — Review Along Five Axes

For **each file changed**, check all five:

### Axis 1 — Correctness
Does the code satisfy every acceptance criterion in `## What`?
- Are all edge cases handled? (null, empty, zero, max value, concurrent access)
- Are errors handled and propagated correctly — not swallowed?
- Does the output match the spec under all valid inputs?
- Would the tests catch a regression if the implementation changed?

### Axis 2 — Readability
Can someone unfamiliar read this code and understand it within 2 minutes?
- Names state intent, not implementation (`getUserById` not `fetchData`)
- No deeply nested conditionals (> 3 levels is a signal to extract)
- No magic numbers or unexplained constants — use named constants
- Comments explain *why*, not *what* (the code shows the what)
- Each function/method does one thing

### Axis 3 — Architecture
Does this change fit the system's existing design?
- Logic is in the right layer (no business logic in controllers, no DB queries in UI components)
- No circular dependencies introduced
- New abstractions are justified — does the abstraction reduce the concepts a reader must hold, or does it just relocate them?
- No feature-specific logic leaking into shared/general-purpose modules
- Existing canonical helpers are reused, not duplicated with slight variations

### Axis 4 — Security
For changes touching risk-gated paths (`**/auth/**`, `**/migration*/**`, `**/.env*`, `**/package.json`): document the specific risk in `## Review` and note that human review is recommended.

Check:
- User input validated and sanitized at every system boundary before use in logic or rendering
- No secrets in code, logs, or version control
- SQL queries parameterized — no string concatenation
- Outputs encoded to prevent XSS where user content is rendered
- Authentication and authorization enforced at every protected endpoint
- Dependencies from trusted sources, no known vulnerabilities

### Axis 5 — Performance
Any obvious regressions introduced?
- N+1 query patterns (loop contains a query)
- Unbounded loops or unconstrained data fetching without pagination
- Synchronous blocking operations that should be async
- Large objects created in hot paths
- Missing pagination on list endpoints

## Step 4 — Categorize Every Finding
Label every comment so the author knows what is required vs optional:

| Prefix | Meaning | Author action |
|--------|---------|---------------|
| *(none)* | Required change | Must fix before marking done |
| **Critical:** | Blocks completion | Security, data loss, broken behaviour |
| **Nit:** | Optional | Formatting, style preference |
| **Consider:** | Suggestion | Worth thinking about, not required |

**Lead with what matters.** Correctness and security first. Do not bury a real issue under nits. A few high-conviction findings beat a long list.

## Step 5 — Write `## Review` in the Task File
Each finding must state:
1. The rule or catalog entry ID
2. Whether the rule is enforced in project config (linter, type checker, analyzer)
3. If not enforced: the config-level fix that prevents this class of bug — not just this instance

## Step 6 — If Issues Found
Fix → re-run verify → re-commit → re-review. Do not mark done until review is clean.

## Quality Bar

A review is done when:
- Every acceptance criterion in `## What` is satisfied by the implementation
- All defect catalog entries have been checked against the diff
- All findings are filed with severity labels
- All Required and Critical findings are resolved
- `## Review` is written in the task file
