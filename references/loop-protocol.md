# Loop Protocol

The orchestrator agent operates as a continuous loop over a task list using an **orchestrator/sub-agent** model. The orchestrator manages task state, specs, plans, and reviews. Sub-agents handle the BUILD stage with fresh context windows.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  ORCHESTRATOR (@orchestrator)                       │
│  • Reads task files (~5KB per iteration)            │
│  • Runs task.py commands                            │
│  • Writes specs, plans, reviews                     │
│  • Creates new tasks when work is discovered        │
│  • Delegates BUILD to sub-agents                    │
│  • Decides when project is complete                 │
│                                                     │
│  [USER REQUEST] → DECOMPOSE → PICK → SPEC → PLAN   │
│       ↑                                   │         │
│       │    ┌──────────────────────────────▼────┐    │
│       │    │  SUB-AGENT (fresh context)        │    │
│       │    │  • Full context window             │    │
│       │    │  • Implements ## Plan               │    │
│       │    │  • Runs gate commands               │    │
│       │    │  • Returns DONE or BLOCKED          │    │
│       │    └──────────────────────────────┬────┘    │
│       │                                   │         │
│       │    REVIEW ← COMMIT ← VERIFY ←────┘         │
│       │      │                                      │
│       │    LEARN → NEXT ──────────────────┐         │
│       │                                   │         │
│       └───────────────────────────────────┘         │
└─────────────────────────────────────────────────────┘
```

### Why Sub-Agents?

- **No context exhaustion**: Each task gets a fresh context window
- **Orchestrator stays lean**: ~5KB per loop iteration
- **Failure isolation**: A sub-agent crash doesn't lose orchestrator state
- **Parallel-ready**: Multiple sub-agents could run concurrently (future)

### Project Context

Every sub-agent receives `.codestudio/project-context.md` in its prompt:
- **Stack**: Language, framework, key libraries
- **Architecture**: Directory layout, layer relationships
- **Conventions**: Naming, patterns, error handling
- **Boundaries**: Files/dirs that should not be modified
- **Gates**: What verification commands must pass

The orchestrator updates project-context.md during LEARN when architectural decisions change.

## Loop Stages

### DECOMPOSE (only when user gives a new goal)
When the user describes work ("Add Stripe billing"), the orchestrator:
1. Understands the goal in context of the existing codebase
2. Breaks it into tasks with dependencies
3. Seeds them via `task.py add`
4. Enters the PICK stage

This only happens when the user provides a new feature/goal. On session resume with existing tasks, skip directly to PICK.

### PICK
Run `python3 .codestudio/task.py next` to get the next eligible task.
- Only one active task at a time
- Dependencies are checked (a task with `needs: ["T-001"]` won't be picked until T-001 is done)
- `todo` tasks are picked before `backlog`

### SPEC
Define what to build in `## What` of the task file.
- For complex tasks: structured specification with acceptance criteria
- For trivial tasks: a single sentence suffices

### PLAN
Break into subtask checkboxes in `## Plan`.
- Each subtask should be completable in a single commit
- Order by dependency
- Skip for trivial tasks

### BUILD (delegated to sub-agent)
Delegate via `runSubagent` with:
- Task spec + plan
- project-context.md (conventions, architecture, boundaries)
- gates.yaml (verification commands)
- Skill instructions (TDD, incremental implementation)

Sub-agent implements subtasks, runs gates, reports DONE or BLOCKED.

### VERIFY
Run `python3 .codestudio/task.py verify` — executes all gates in parallel, enforces ratchet floors, writes evidence.
- On failure: fix, retry, max 3 attempts, then BLOCK
- Must pass BEFORE commit

### COMMIT
Commit after verify passes. Atomic commits with conventional messages.
- Format: `type(scope): description`
- One subtask = one commit

### REVIEW
Code review against the defect catalog.
- Read `.codestudio/catalogs/defects-*.md`
- For security-sensitive tasks, also use security skill
- If issues found: fix, re-verify, re-commit, re-review

### LEARN
1. Write `## Log` in the task file
2. Append summary to `progress.md`
3. Update `project-context.md` if architectural decisions changed
4. Run `python3 .codestudio/task.py done`

### NEXT
Return to PICK. Loop continues autonomously.

## Task Discovery

The orchestrator discovers new tasks in 3 ways:

1. **During BUILD** — Sub-agent reports blockers or missing prerequisites
2. **During REVIEW** — Code review reveals gaps (missing error handling, untested paths)
3. **During LEARN** — Realizes missing pieces needed for the original goal

New tasks are added via `task.py add` with proper dependencies.

## Autonomous Completion

The loop doesn't stop when `todo` tasks run out:
- **Auto-promotes** backlog items needed to meet the goal
- **Discovers** new tasks during build and review
- **Completes** when: all `todo` done, all `backlog` evaluated, all gates pass, original goals satisfied

## Task State Machine

```
backlog → todo → active → review → done → archive
                   │                  
                   ↓                  
                 blocked → todo (unblock)
```

- **backlog**: Ideas, future work. Not eligible for PICK.
- **todo**: Ready to work. Picked when dependencies met.
- **active**: Currently being worked on. Only one at a time.
- **review**: Submitted for review. Approved → done, rejected → active.
- **blocked**: Can't proceed. Needs action or info.
- **done**: Complete. Can be archived.

## Key Constraints

1. **Agent never edits index.json.** All state changes go through `task.py`.
2. **One active task.** Finish, block, or review before picking another.
3. **Commit per subtask.** Keeps history atomic and bisectable.
4. **VERIFY before COMMIT.** Evidence must exist before committing.
5. **Max 3 verify retries.** Block and move on if stuck.
6. **progress.md is memory.** Write what future sessions need to know.
7. **BUILD is delegated.** Orchestrator manages state, sub-agents write code.
8. **Sub-agents don't run task.py.** Only the orchestrator manages task state.
