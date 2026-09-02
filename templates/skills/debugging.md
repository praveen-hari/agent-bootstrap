# SKILL: Debugging and Error Recovery

Systematic root-cause debugging. When something breaks, stop adding features, preserve evidence, and follow this procedure. Guessing wastes time.

## The Stop-the-Line Rule
When anything unexpected happens:
```
1. STOP — do not add features or make more changes
2. PRESERVE — save the full error output, logs, and repro steps
3. DIAGNOSE — follow the triage steps below in order
4. FIX — address the root cause, not the symptom
5. GUARD — add a test that prevents recurrence
6. RESUME — only after the gate suite passes
```
**Do not push past a failing test or broken build to work on the next feature.** Errors compound.

## Triage Checklist (work in order, do not skip steps)

### Step 1 — Reproduce
Make the failure happen reliably. If you cannot reproduce it, you cannot fix it with confidence.
```bash
# Run the specific failing test in isolation
npm test -- --grep "exact test name"
# or
pytest tests/path/to/test.py::test_name -v
```
If non-reproducible: check for timing, environment, or state dependencies before continuing.

### Step 2 — Localize
Identify which layer is failing:
| Layer | Where to look |
|-------|--------------|
| UI/Frontend | Browser console, DOM, network tab |
| API/Backend | Server logs, request/response bodies |
| Database | Query output, schema, data integrity |
| Build tooling | Config files, dependency versions, environment variables |
| Test itself | Is the test a false negative? Is the assertion wrong? |

For regression bugs — use bisection:
```bash
git bisect start
git bisect bad                     # current commit is broken
git bisect good <known-good-sha>   # this commit worked
git bisect run npm test -- --grep "failing test"
```

### Step 3 — Reduce
Create the minimal failing case. Remove unrelated code and config until only the bug remains. Simplify input to the smallest example that triggers the failure.
A minimal reproduction makes the root cause obvious and prevents fixing symptoms instead of causes.

### Step 4 — Root Cause
Read the **full** error output — do not skim. The gate output names the exact file, line, and rule.
- The error says "undefined is not a function at line 42" → fix line 42, not a try/catch around it
- The error says "coverage dropped below 80%" → find the uncovered lines, add tests
- Fix the cause. Never suppress the error message.

### Step 5 — Fix and Guard
1. Fix the root cause
2. Confirm the originally failing test now passes
3. Run the full gate suite — no regressions
4. If this class of bug can recur: add a test or lint rule that prevents it

## After 3 Failures
If the same gate fails after 3 separate fix attempts:
```bash
python3 .codestudio/task.py block "reason — attach the full failing gate output"
```
Report BLOCKED with the complete evidence. Do not continue guessing.

## What NEVER to Do
- `# pragma: no cover` / `istanbul ignore` / `eslint-disable` to silence a gate
- Delete or skip a failing test
- Lower a coverage threshold in `gates.yaml`
- Catch an exception and swallow it to make a gate green
- Assert `True` or use an always-passing condition to fix a test

These are symptoms of fixing the measurement, not the problem.
