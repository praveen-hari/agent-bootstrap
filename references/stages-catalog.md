# Stages Catalog — Skill Mapping

Each loop stage has mandatory skills that the orchestrator MUST read and follow. Skills are required process steps, not optional enhancers.

Skills live at `~/.agents/skills/<name>/SKILL.md`.

## Stage → Skill Mapping

| Stage | Primary Skill | Secondary Skill | When |
|-------|--------------|-----------------|------|
| INTERVIEW | `interview-me` | — | Empty repos — extracting user intent |
| DECOMPOSE | `planning-and-task-breakdown` | — | Breaking user goals into tasks |
| SPEC | `spec-driven-development` | — | Complex or unclear tasks |
| PLAN | `planning-and-task-breakdown` | — | Multi-step tasks |
| BUILD | `incremental-implementation` | `test-driven-development` | Always |
| VERIFY | `debugging-and-error-recovery` | — | On failure (up to 3 retries) |
| REVIEW | `code-review-and-quality` | `security-and-hardening` | >10 files changed or sensitive task |
| COMMIT | `git-workflow-and-versioning` | — | Always (if .git exists) |

## Context-Specific Skills

Activate based on what the task touches:

| Skill | Trigger |
|-------|---------|
| `frontend-ui-engineering` | Task involves UI components, pages, layouts |
| `frontend-design-system` | Task involves design tokens, themes, styles |
| `context-engineering` | Task involves configuring agent rules or context |
| `documentation-and-adrs` | Task involves architectural decisions or public APIs |
| `shipping-and-launch` | Task involves deployment or production readiness |

## How Skills Are Invoked

The orchestrator names each skill at the relevant stage in its agent file:

```markdown
### 4. BUILD
Read and follow `~/.agents/skills/test-driven-development/SKILL.md`: RED → GREEN → REFACTOR.
```

The agent reads the skill file using `read_file` and follows its instructions. Skills are mandatory — the agent must not skip them.

## Skill Detection

During bootstrap, check for installed skills:
```
~/.agents/skills/<name>/SKILL.md
```

Required skills:
- `interview-me`
- `spec-driven-development`
- `planning-and-task-breakdown`
- `test-driven-development`
- `incremental-implementation`
- `debugging-and-error-recovery`
- `code-review-and-quality`
- `security-and-hardening`
- `git-workflow-and-versioning`

Conditional:
- `frontend-ui-engineering` (if UI_PROJECT is true)

If missing, warn the user during bootstrap. The orchestrator falls back to inline guidance but this is degraded mode.

Install all skills with:
```bash
git clone https://github.com/addyosmani/agent-skills.git ~/.agents/skills
```
