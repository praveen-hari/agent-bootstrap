# SKILL: Spec-Driven Development

Write a structured specification before writing any code. Code without a spec is guessing.

## Mandatory Steps

### Step 1 — Surface Assumptions First
Before writing any spec content, list every assumption you are making:
```
ASSUMPTIONS I'M MAKING:
1. [assumption about tech, scope, users, etc.]
2. [assumption]
→ Correct me now or I'll proceed with these.
```
Do not silently fill in ambiguous requirements. Assumptions are the most dangerous form of misunderstanding.

### Step 2 — Write `## What` in the Task File

The spec has four required parts. All four are mandatory — missing any one makes the spec incomplete.

**a) Behaviour**
What the system does that it did not do before. One sentence per distinct behaviour change.

**b) Out of scope**
What this task explicitly does NOT cover. List at least two things. If you cannot name what is out, the scope is not defined yet — define it before proceeding.

**c) Acceptance criteria**
Each criterion must be verifiable by a tool or a test. If you cannot name how it will be verified, rewrite it.
- ❌ `"Handles errors gracefully"` — not verifiable
- ✅ `"Returns HTTP 400 with ProblemDetails body when orderId is malformed — covered by test OrderController_Create_Returns400_WhenOrderIdMalformed"`

**d) Open questions**
Anything unresolved that needs human input before implementation begins. If empty, confirm you have no unresolved questions — do not silently assume answers.

### Step 3 — Template to Write

```markdown
## What

**Behaviour:**
[What the system does that it didn't before — one sentence per change]

**Out of scope:**
- [Thing explicitly not covered]
- [Thing explicitly not covered]

**Acceptance criteria:**
- [ ] [Specific testable condition] — verified by `[test name or exact gate command]`
- [ ] [Specific testable condition] — verified by `[test name or exact gate command]`

**Open questions:**
- [Anything needing human input, or "None — all clear"]
```

### Step 4 — Gate: Present and Wait
**Present the completed spec to the user. Do not proceed to PLAN until the user confirms.** This is the checkpoint that prevents building the wrong thing.

## Quality Bar

A spec is done when:
- Every acceptance criterion names its verification method (test name or gate command)
- Scope boundary lists at least two explicit exclusions
- No criterion says "should" or "gracefully" without a measurable definition
- Open questions are resolved or flagged for human review
