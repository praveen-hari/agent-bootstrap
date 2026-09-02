# Workflow: bugfix — a defect

**Binding policies:** `reproduce-before-fix` · `root-cause-not-symptom` · `never-weaken` · `evidence-before-done`

**Hard ordering constraint: the failing test comes first. This is not reorderable.**

## 1. REPRODUCE (before anything else)

Write a test that **fails for the reported reason**. Run it. Watch it fail. Record:
- The exact reproduction steps
- The observed (wrong) behaviour
- The expected (correct) behaviour
- The failing assertion

If it will not reproduce: do not guess. Record what you tried. Block the task. Name what is needed (version, data, config, environment).

A fix without a failing test cannot be distinguished from "no longer reproduces on my machine".

## 2. DIAGNOSE — find the root cause

Record the causal chain in `## Log`, not just the symptom.

Signals you have the symptom, not the cause:
- The fix is a null-check at the crash site
- The fix is a `try/catch` around the failing call
- You cannot explain why the bug appeared when it did
- The fix works but you cannot say which input class it covers

## 3. ASSESS BLAST RADIUS

Does the same root cause exist elsewhere in the codebase? Search for the pattern. Other instances become **new tasks**, not additions to this one.

## 4. FIX

The smallest change that addresses the cause. A bugfix is not a refactor — if the code needs restructuring, file a `refactor` task.

## 5. VERIFY

- The reproduction test now passes
- **Every other test still passes** — a bugfix that breaks a test is a trade, and the trade must be stated explicitly, not absorbed silently
- All gates pass

## 6. REVIEW

Reviewer confirms the test fails without the fix. Reverting the source change and watching the test go red is the cheapest verification.

## Definition of done

- [ ] A test reproduces the defect and was observed failing before the fix
- [ ] Root cause recorded in `## Log` (causal chain, not just the symptom)
- [ ] Blast radius assessed; other instances filed as separate tasks
- [ ] All gates pass at the current commit
- [ ] No test weakened, skipped, or deleted to make the fix pass
- [ ] `## Review` confirms test fails without fix
