---
id: root-cause-not-symptom
severity: standard
appliesTo: [bugfix]
---

# root-cause-not-symptom — fix the cause, not the crash

## Rule

A defect fix addresses the root cause. The causal chain is recorded in `## Log`.

## Why

Symptom fixes accumulate. Each one makes the next defect harder to diagnose because the code now contains defensive scar tissue whose purpose nobody remembers. A null-check added at the crash site does not prevent the null from arriving; it just moves the failure downstream.

## Signals you have the symptom, not the cause

- The fix is a null-check at the crash site
- The fix is a `try/catch` around the failing call
- You cannot explain why the bug appeared when it did
- The fix works but you cannot say which input class it covers
- The fix requires explaining the old behaviour as "an unrelated legacy issue"

## Enforced by

The `bugfix` workflow requires the causal chain in `## Log`. The reviewer checks it is present and plausible — "fixed the null ref" is not a causal chain.

## Violation

Diagnose further. If the root cause is out of scope (belongs to another system, another team, a larger architectural change), fix the symptom deliberately, say so explicitly in `## Log`, and file the root cause as a separate task.
