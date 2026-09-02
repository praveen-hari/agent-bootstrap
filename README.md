# Agent Bootstrap

A Code Studio skill that bootstraps any repository for fully autonomous AI-driven software development. One command takes a repo from zero to an agent-ready workspace with task management, evidence gates, and a loop protocol.

## What It Does

Point it at any repo (or an empty one) and it will:

1. **Scan + Assess** — detect stack, tools, conventions, and score readiness
2. **Bootstrap** — create `.codestudio/` harness with task management and orchestrator
3. **Handoff** — seed initial tasks and instruct the user to run `@orchestrator`

After bootstrap, the **orchestrator agent** takes over: creating tasks, planning features, building code, verifying with evidence gates, committing, reviewing, and repeating until the project is complete.

## Quick Start

```
/agent-bootstrap
```

For empty repos, the skill interviews you about what to build. For existing repos, it auto-detects everything.

After bootstrap:
```
@orchestrator Add user authentication with OAuth
```

The orchestrator decomposes the goal into tasks and builds them autonomously.

## Generated Output

```
your-project/
├── AGENTS.md                              # How AI agents work in this repo
└── .codestudio/
    ├── task.py                            # Task manager (14 commands)
    ├── gates.yaml                         # Evidence gates (lint, test, coverage)
    ├── harness-lock.json                  # Ratchet floors (quality only goes up)
    ├── .gitignore                         # Excludes evidence/ and coverage
    ├── agents/
    │   └── orchestrator.agent.md          # Development loop protocol
    ├── instructions/
    │   └── task-conventions.instructions.md
    ├── catalogs/
    │   └── defects-<framework>.md         # Framework-specific bug patterns
    ├── project-context.md                 # Stack, architecture, conventions
    ├── tasks/
    │   └── index.json                     # Task index (managed by task.py)
    ├── evidence/                          # Gate output per task (gitignored)
    └── progress.md                        # Session memory
```

## The Loop

```
PICK → SPEC → PLAN → BUILD (sub-agent) → VERIFY → COMMIT → REVIEW → LEARN → NEXT
```

| Stage | What Happens |
|-------|-------------|
| **PICK** | `task.py next` — get next eligible task |
| **SPEC** | Write acceptance criteria |
| **PLAN** | Break into subtask checkboxes |
| **BUILD** | Sub-agent implements (fresh context per task) |
| **VERIFY** | `task.py verify` — runs gates in parallel with ratchet enforcement |
| **COMMIT** | Atomic commit with conventional message |
| **REVIEW** | Code review against defect catalog |
| **LEARN** | Log decisions, update progress.md |
| **NEXT** | Loop back to PICK |

## Three Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Empty repo** | No source files | Interview → setup → seed tasks |
| **Existing repo** | Source files found | Auto-detect → setup (respects existing configs) |
| **Upgrade** | `.codestudio/` exists | Update scripts, preserve tasks & progress |

## Evidence Gates

Quality gates that must pass before any task can be marked done:

- **exit-code gates**: build, lint, typecheck, format (pass/fail)
- **coverage gates**: line coverage ≥ threshold
- **audit gates**: no high/critical vulnerabilities
- **Ratchet enforcement**: quality thresholds can never go down

## SDLC Skills

The orchestrator uses skills from `~/.agents/skills/` at each stage. Install with:

```bash
git clone https://github.com/addyosmani/agent-skills.git ~/.agents/skills
```

## Task Manager

```bash
python3 .codestudio/task.py next              # pick next task
python3 .codestudio/task.py verify            # run gates, capture evidence
python3 .codestudio/task.py done              # mark complete (requires evidence)
python3 .codestudio/task.py add "title"       # new task
python3 .codestudio/task.py add "t" --needs T-001  # with dependency
python3 .codestudio/task.py block "reason"    # can't proceed
python3 .codestudio/task.py status            # project summary
python3 .codestudio/task.py list              # list all tasks
```
