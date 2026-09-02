# Workflow: feature — new capability

**Binding policies:** `spec-before-code` · `never-weaken` · `evidence-before-done`

A feature task runs the standard 6-stage loop with no deviations.

## Stage notes specific to this workflow

### SPEC
Write `## What` with all four required parts:
- **Behaviour** — what the system does that it did not do before
- **Explicitly out of scope** — at least two things this task does NOT cover
- **Acceptance criteria** — each one names the test or gate that verifies it
- **Sources consulted** — cite the rank-1 or rank-2 source per `.codestudio/skills/oracles.md`; do not rely on recall for framework behaviour
- **Open questions** — any ambiguity gets an assumption + pinning test, not a silent decision

### PLAN
Each subtask names the test that will verify it. If you cannot name the test, return to SPEC — the criterion is not concrete enough.

Slice vertically. One thin end-to-end path beats three horizontal layers because it can be verified incrementally.

### BUILD
Test first. The test is written from the spec, not from the implementation. A test written after the code encodes what the code does, which may not be what was asked for.

### REVIEW
Check that the diff does what `## What` says — **and nothing more**. Scope creep in implementation is a defect. Flag anything the diff introduces that no acceptance criterion covers.

## Definition of done

- [ ] `## What` has behaviour, scope boundary, acceptance criteria, sources, open questions
- [ ] Every acceptance criterion names its verification method (test or gate)
- [ ] Every `## Plan` subtask is ticked
- [ ] The diff does what `## What` says — and nothing more
- [ ] All gates pass at the current commit
- [ ] No test weakened, skipped, or deleted
- [ ] `## Review` written with findings or explicit "No issues"
- [ ] `## Log` records decisions, dead ends, reasoning
