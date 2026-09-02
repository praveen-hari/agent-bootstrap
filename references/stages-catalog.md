# Stages Catalog — Skill Mapping

Each loop stage has a mandatory skill file that the orchestrator MUST read and follow. Skills are required process steps, not optional enhancers.

## Where Skills Live

Skill files are **bundled inside the project harness** at `.codestudio/skills/`. They are copied from `./templates/skills/` during bootstrap and are always present. No global install, no external path, no network required.

```
.codestudio/
  skills/
    spec.md         ← SPEC stage
    plan.md         ← PLAN and DECOMPOSE stages
    tdd.md          ← BUILD stage
    debugging.md    ← VERIFY stage (on failure)
    commit.md       ← COMMIT stage
    review.md       ← REVIEW stage
```

## Stage → Skill File Mapping

| Stage | Skill File | When |
|-------|-----------|------|
| DECOMPOSE | `.codestudio/skills/plan.md` | Breaking user goals into tasks |
| SPEC | `.codestudio/skills/spec.md` | Every task — no exceptions |
| PLAN | `.codestudio/skills/plan.md` | Every task — no exceptions |
| BUILD | `.codestudio/skills/tdd.md` | Every subtask — no exceptions |
| VERIFY (failure) | `.codestudio/skills/debugging.md` | On any gate failure |
| COMMIT | `.codestudio/skills/commit.md` | Every verified subtask |
| REVIEW | `.codestudio/skills/review.md` | Every task — no exceptions |

## How Skills Are Invoked

The orchestrator reads the skill file using `read_file` at the start of each stage and follows every step. The read is mandatory and happens before any work begins at that stage.

```markdown
### 2. SPEC
Read `.codestudio/skills/spec.md` now. Follow every step in that file.
```

There are no fallbacks. There is no "if it exists" guard. The file is always present after bootstrap.

## Customising Skills

Skill files inside `.codestudio/skills/` are project-owned. Teams can edit them to match their conventions (e.g. a different commit format, project-specific review axes, stricter acceptance criteria rules). Bootstrap preserves existing skill files on upgrade — it never overwrites them.

## INTERVIEW Stage (bootstrap only)

The interview stage runs during `@agent-bootstrap` for empty repos. It is not part of the ongoing orchestrator loop. Bootstrap handles this directly — it does not depend on a skill file for interview.

## Context-Specific Additions

For tasks touching specific areas, the orchestrator extends its review checklist:

| Area | Trigger | Extra check |
|------|---------|-------------|
| UI components / pages | `src/**/*.tsx`, `src/**/*.vue`, `components/` | States: loading skeleton, empty, error (see `tdd.md` and `review.md`) |
| Auth / security paths | `**/auth/**`, `**/.env*` | Security axis in `review.md` — flag for human review |
| Database migrations | `**/migration*/**` | Risk-gated — flag for human review |
| Architectural decisions | New services, API contracts | Log decision in `progress.md`, update `project-context.md` |
