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

### Step 2 — Identify the task type and read the workflow

Every task has a type. Read the workflow file for this task's type before writing the spec:

| Type | Workflow | Key constraint |
|------|----------|---------------|
| `feature` | `.codestudio/workflows/feature.md` | spec before code |
| `bugfix` | `.codestudio/workflows/bugfix.md` | **failing test comes first** |
| `refactor` | `.codestudio/workflows/refactor.md` | behaviour must not change |
| `api-change` | `.codestudio/workflows/api-change.md` | breaking changes require human approval |

The workflow file tells you what this type of task requires beyond the standard loop.

### Step 3 — Look up framework behaviour, do not recall it

Before writing acceptance criteria that involve framework APIs, look up the relevant documentation and cite it. Read `.codestudio/skills/oracles.md` for the authority precedence ranking.

Do not rely on training memory for framework behaviour. Training data can be stale, version-specific, or wrong. A criterion built on a misremembered API is a test that passes when it shouldn't.

### Step 4 — Write `## What` in the Task File

The spec has five required parts. All five are mandatory.

**a) Behaviour**
What the system does that it did not do before. One sentence per distinct behaviour change.

**b) Out of scope**
What this task explicitly does NOT cover. List at least two things. If you cannot name what is out, the scope is not defined yet — define it before proceeding.

**c) Acceptance criteria**
Each criterion must be verifiable by a tool or a test. If you cannot name how it will be verified, rewrite it.
- ❌ `"Handles errors gracefully"` — not verifiable
- ✅ `"Returns HTTP 400 with ProblemDetails body when orderId is malformed — covered by test OrderController_Create_Returns400_WhenOrderIdMalformed"`

**d) Sources consulted**
Cite the source that decided each framework or API behaviour question. Use the rank from `oracles.md`. Do not write "per documentation" — name the URL or file.
- ❌ `"per React docs"` — not a citation
- ✅ `"https://react.dev/reference/react/useEffect — rank 2 — decided: cleanup runs before next effect"`

**e) Open questions**
Anything unresolved that needs human input before implementation begins. Each open question gets an assumption + a pinning test. Do not silently assume answers.

### Step 5 — Template to Write

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

**Sources consulted:**
- [url or file path] — rank [N] — decided: [what this source settled]

**Open questions:**
- [question] → assumed: [choice] → pinned by: [test name]
- (or: None — all clear)
```

### Step 6 — Gate: Present and Wait
**Present the completed spec to the user. Do not proceed to PLAN until the user confirms.** This is the checkpoint that prevents building the wrong thing.

## Quality Bar

A spec is done when:
- Task type identified and workflow file read
- Every acceptance criterion names its verification method (test name or gate command)
- Scope boundary lists at least two explicit exclusions
- Sources consulted lists at least one citation for any framework/API behaviour
- No criterion says "should" or "gracefully" without a measurable definition
- Open questions are resolved (with assumption + pinning test) or flagged for human review
