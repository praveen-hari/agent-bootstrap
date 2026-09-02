---
id: reproduce-before-fix
severity: blocking
appliesTo: [bugfix]
---

# reproduce-before-fix — the failing test comes first

## Rule

Before any defect is fixed, a test exists that **fails for the reported reason**, and has been **observed failing**. The fix is written afterwards.

Where a defect cannot be reproduced, the attempts are recorded, the task is blocked, and the specific missing input is named. Guessing is not an alternative.

## Why

Without a failing test you cannot distinguish *fixed* from *no longer reproduces on my machine*, and you have no regression guard for the next change.

This matters more with agents than with people. An agent will confidently report a defect fixed after changing plausible-looking code, having never observed the original failure. The test observed going red, then green, is the only evidence that the change addressed the reported problem rather than a different one.

## Enforced by

The `bugfix` workflow orders it explicitly as step 1. The reviewer confirms: reverting the source change must make the test fail.

## Violation

Write the test. Watch it fail. Then fix. If it will not reproduce, do not guess — record what was tried, block the task, and name what is needed (version, data, configuration, environment).
