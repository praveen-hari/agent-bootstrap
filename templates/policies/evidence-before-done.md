---
id: evidence-before-done
severity: blocking
appliesTo: [all]
---

# evidence-before-done — a task is done when tools say so

## Rule

A task reaches `done` only when:
1. `.codestudio/evidence/<TASK>/gate-summary.json` has `verdict: pass`
2. The recorded commit in the evidence matches the current HEAD

## Why

An agent's report that work is complete is an assertion. The evidence file is a measurement. The commit match matters as much as the verdict — without it, an agent can run gates early and keep committing after.

"The tests pass" asserted by the agent that wrote the tests proves nothing. A `gate-summary.json` produced by running the gate command proves the output existed at a specific commit.

## Enforced by

`task.py done` refuses and exits non-zero without passing, current evidence. `task.py done --skip-gates` bypasses this for genuine tooling outages and is logged.

## Violation

Run the gates with `task.py verify`. If they fail, fix the cause. `--skip-gates` is for a genuine tooling outage, not for a real gate failure.
