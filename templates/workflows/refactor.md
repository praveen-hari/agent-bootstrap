# Workflow: refactor — structure changes, behaviour does not

**Binding policies:** `no-behaviour-change` · `never-weaken` · `evidence-before-done`

**The defining constraint: a refactor that changes behaviour is not a refactor.**

If behaviour must change, that is a `feature` or `bugfix`. Reclassify and spec it.

## 1. ESTABLISH THE BASELINE

Run the full test suite. Record the result in `## Log`.

**If the code being refactored is not covered by tests — stop.** Refactoring untested code is rewriting it and hoping. Add characterisation tests first (tests that pin current behaviour, whatever it is) before proceeding.

## 2. STATE THE OBSERVABLE GOAL

In `## What`, state the goal as something measurable:

| Goal | Observable |
|---|---|
| Remove duplication | N call sites collapse to one |
| Reduce coupling | dependency rule now passes |
| Improve testability | a seam exists for a test double |
| Reduce complexity | cyclomatic complexity below threshold |
| Enable planned work | task T-XXX becomes possible |

"Make the code cleaner" is not a goal. If you cannot name the observable, the refactor has no success condition.

## 3. TRANSFORM INCREMENTALLY

One transformation per commit. Run the tests after each. Never batch multiple transformations.

**Do not change tests.** A test that must change means behaviour changed — stop and reclassify the task.

## 4. VERIFY

- Full suite green with tests unmodified
- `git diff` on test files is empty (or any change is whitespace-only and is stated)
- Public API unchanged — if it changed, this needs the `api-change` workflow

## Definition of done

- [ ] Full suite was green before the refactor started (recorded in `## Log`)
- [ ] Full suite is green after — tests unmodified
- [ ] `git diff` on test files is empty or whitespace-only
- [ ] Observable goal stated in `## What` and confirmed achieved
- [ ] Public API unchanged (or `api-change` workflow followed)
- [ ] No gate weakened, skipped, or deleted
