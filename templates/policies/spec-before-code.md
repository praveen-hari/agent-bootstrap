---
id: spec-before-code
severity: blocking
appliesTo: [all]
---

# spec-before-code — write ## What before implementing

## Rule

No implementation begins before `## What` states:
- The **behaviour** (what the system does that it did not do before)
- The **scope boundary** (what this task explicitly does NOT cover)
- **Acceptance criteria** that a tool or a test can check
- **Sources consulted** (what was looked up, not recalled — with rank)

## Why

Without acceptance criteria, there is nothing for a gate to verify against and nothing for a reviewer to check conformance to. "Done" becomes whatever the implementer decided it meant.

The scope boundary matters as much as the criteria — it is what makes scope creep visible. A diff that does more than the spec says is a defect, not a bonus.

## Enforced by

`task stage advance` refuses to advance from SPEC until `## What` exists with real content. The reviewer flags any diff behaviour not covered by an acceptance criterion.

## Violation

Return to SPEC. Write the criterion. Even a trivial task gets one sentence — "trivial" is a judgement the spec makes explicit rather than assumes.
