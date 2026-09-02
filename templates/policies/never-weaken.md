---
id: never-weaken
severity: blocking
appliesTo: [all]
---

# never-weaken — do not weaken a gate to pass it

## Rule

**Never disable, weaken, skip, narrow, or delete a test, gate, assertion, threshold, or policy in order to make a gate pass.**

This covers:
- Lowering a threshold in `gates.yaml`
- Adding `[ExcludeFromCodeCoverage]`, `# pragma: no cover`, or `istanbul ignore`
- Adding `eslint-disable`, `#pragma warning disable`, or `@ts-ignore` without a written justification
- Deleting, skipping, or marking a test as ignored
- Weakening an assertion to something that cannot fail (e.g. `assert True`, `expect(x).toBeDefined()` where x is always defined)

## Why

This is the cheapest available path for an agent instructed to make things green, so it is the one that will be taken by default. Every other guarantee in the harness rests on this rule holding.

A gate that can be adjusted by the thing it measures is not a gate.

## Enforced by

- Ratchet floor in `harness-lock.json` — `task stage advance` refuses if threshold drops
- The reviewer inspects the diff for removals, skips, and suppression additions
- `task done` refuses without passing gate evidence at HEAD

## Violation

Revert the weakening. If the gate is genuinely wrong, record it in `## Log` and report BLOCKED. Changing a gate is a human decision, not a side effect of a task.
