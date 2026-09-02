# Agent Bootstrap

A Code Studio skill that bootstraps any repository for fully autonomous AI-driven software development. One command takes a repo from zero to an agent-ready workspace with task management, evidence gates, and a loop protocol.

## What It Does

Point it at any repo (or an empty one) and it will:

1. **Scan + Assess** — detect stack, tools, conventions, and score readiness
2. **Bootstrap** — create `.codestudio/` harness with task management and orchestrator
3. **Handoff** — seed initial tasks and instruct the user to run `@orchestrator`

After bootstrap, the **orchestrator agent** takes over: creating tasks, planning features, building code, verifying with evidence gates, committing, reviewing, and repeating until the project is complete.

## How It Works

```mermaid
flowchart LR
    A["/agent-bootstrap"] --> B{"Repo empty?"}
    B -->|Yes| C["Interview\n(what to build, stack)"]
    B -->|No| D["Auto-detect\n(scan existing code)"]
    C --> E["Bootstrap\n.codestudio/"]
    D --> E
    E --> F["Seed Tasks"]
    F --> G["@orchestrator\nStarts building"]

    style A fill:#4a90d9,stroke:#2c5f8a,color:#fff
    style E fill:#27ae60,stroke:#1e8449,color:#fff
    style G fill:#e67e22,stroke:#d35400,color:#fff
```

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
    ├── task.py                            # Task manager (16 commands)
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

```mermaid
flowchart TD
    PICK["🎯 PICK\ntask.py next"] --> SPEC["📋 SPEC\nacceptance criteria"]
    SPEC --> PLAN["📐 PLAN\nsubtask checkboxes"]
    PLAN --> BUILD["🔨 BUILD\ndelegated to sub-agent\nfresh context per task"]

    BUILD --> VERIFY{{"✅ VERIFY\ntask.py verify\nlint · test · coverage-diff"}}
    VERIFY -->|fail| FIX["🔧 FIX\nmax 3 retries"]
    FIX --> VERIFY
    VERIFY -->|pass| COMMIT["💾 COMMIT\nconventional message"]

    COMMIT --> RISK{"Risk-gated\npath?"}
    RISK -->|no| REVIEW["🔍 REVIEW\ndefect catalog +\ngate evidence"]
    RISK -->|yes| REVIEW_SEC["🔒 REVIEW\n+ security audit\n+ human flag"]
    REVIEW_SEC --> LEARN
    REVIEW -->|clean| LEARN["📝 LEARN\nprogress.md\ntask.py done"]
    REVIEW -->|issues| FIX

    LEARN --> NEXT["🔄 NEXT"]
    NEXT --> PICK

    FIX -->|3 failures| BLOCK["🚫 BLOCKED\ntask.py block"]
    BLOCK --> PICK

    style BUILD fill:#e1f5fe,stroke:#0288d1
    style VERIFY fill:#e8f5e9,stroke:#2e7d32
    style BLOCK fill:#ffcdd2,stroke:#d32f2f
    style REVIEW_SEC fill:#fff3e0,stroke:#ef6c00
```

| Stage | What Happens |
|-------|-------------|
| **PICK** | `task.py next` — get next eligible task (records baseSha for diff-scoping) |
| **SPEC** | Write acceptance criteria |
| **PLAN** | Break into subtask checkboxes |
| **BUILD** | Sub-agent implements (fresh context per task) |
| **VERIFY** | `task.py verify` — runs gates in parallel with ratchet enforcement |
| **COMMIT** | Atomic commit with conventional message |
| **REVIEW** | Code review against defect catalog + gate evidence (never re-checks what gates proved) |
| **LEARN** | Log decisions, update progress.md |
| **NEXT** | Loop back to PICK |

## Task States

```mermaid
stateDiagram-v2
    [*] --> backlog : add --backlog
    [*] --> todo : add

    backlog --> todo : promote
    backlog --> deferred : defer "reason"
    todo --> active : next (records baseSha)
    active --> review : gates pass
    active --> blocked : block "reason"
    review --> done : approve
    review --> active : reject
    blocked --> todo : unblock
    done --> [*] : archive

    active --> todo : rollback --force
```

## Three Modes

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Empty repo** | No source files | Interview → setup → seed tasks |
| **Existing repo** | Source files found | Auto-detect → setup (respects existing configs) |
| **Upgrade** | `.codestudio/` exists | Update scripts, preserve tasks & progress |

## Evidence Gates

Quality gates that must pass before any task can be marked done:

- **exit-code gates**: build, lint, typecheck, format (pass/fail)
- **coverage gates**: line coverage ≥ threshold (global)
- **coverage-diff gates**: coverage of lines *this task changed* ≥ threshold (brownfield-friendly)
- **audit gates**: no high/critical vulnerabilities
- **Ratchet enforcement**: quality thresholds can never go down

### Diff-Scoped Coverage

The most important feature for existing repos. Instead of measuring global coverage (often 4% on legacy codebases), `coverage-diff` measures only the lines this task changed — enforceable at 80% from day one.

```
FAIL coverage-diff  diffLineRate=44.44%
     Add tests covering these changed lines:
         src/calc.py:12
         src/calc.py:16
```

## Autonomy Boundary

The orchestrator follows three decision lanes:

```mermaid
flowchart TD
    Q["Agent hits a decision"] --> C1{"Sources answer\nit outright?"}
    C1 -->|yes| A["✅ DECIDE ALONE\ninternal design, naming,\nalgorithms, refactors"]
    C1 -->|no| C2{"Major scope, public API,\nsecurity, or legal?"}
    C2 -->|yes| P["🅿️ PARK FOR HUMAN\nwrite recommendation,\nblock affected tasks,\ncontinue other work"]
    C2 -->|no| B["⚠️ ASSUME + PIN\nchoose, write assumption,\nadd pinning test, log it"]

    style A fill:#e8f5e9,stroke:#2e7d32
    style B fill:#fff3e0,stroke:#ef6c00
    style P fill:#e3f2fd,stroke:#1565c0
```

## The One Rule With No Exceptions

> **NEVER disable, weaken, skip, or delete a test, gate, or threshold to make a gate pass.**

This is the cheapest path for an agent told to make things green. The ratchet blocks threshold changes. This rule blocks everything else.

## SDLC Skills

The orchestrator uses SDLC skills from `~/.agents/skills/` at each loop stage (TDD, code review, security, etc.).

**During bootstrap**, the skill checks if these are installed and offers to auto-install them:

```mermaid
flowchart TD
    A["Check ~/.agents/skills/"] --> B{"Skills\ninstalled?"}
    B -->|Yes| C["✅ Continue bootstrap"]
    B -->|No| D["Ask user:\nInstall now?"]
    D -->|Yes| E["git clone agent-skills\n→ ~/.agents/skills/"]
    D -->|No| F["⚠️ Continue with\nbuilt-in fallback guidance"]
    E --> C

    style C fill:#e8f5e9,stroke:#2e7d32
    style F fill:#fff3e0,stroke:#ef6c00
```

If skills are not installed, the orchestrator uses **built-in fallback guidance** — less detailed but functional. You can install skills anytime:

```bash
git clone https://github.com/addyosmani/agent-skills.git ~/.agents/skills
```

## Task Manager

```bash
python3 .codestudio/task.py next              # pick next task (records baseSha)
python3 .codestudio/task.py verify            # run gates, capture evidence
python3 .codestudio/task.py done              # mark complete (requires evidence)
python3 .codestudio/task.py add "title"       # new task
python3 .codestudio/task.py add "t" --needs T-001  # with dependency
python3 .codestudio/task.py block "reason"    # can't proceed
python3 .codestudio/task.py defer T-XXX "why" # defer backlog item with reason
python3 .codestudio/task.py rollback T-XXX    # dry run: show what's lost
python3 .codestudio/task.py rollback T-XXX --force  # execute rollback to baseSha
python3 .codestudio/task.py status            # project summary
python3 .codestudio/task.py list              # list all tasks
```
