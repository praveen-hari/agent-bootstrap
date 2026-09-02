---
name: agent-bootstrap
description: 'Bootstrap any repo for autonomous AI development. Use when: "bootstrap project", "set up harness", "agent readiness", "initialize project", "start new project", onboarding a codebase, or preparing a repo for agent-driven development. Scans repos, assesses readiness, scaffolds task management, seeds initial tasks, and creates an orchestrator agent. Works on empty repos (interview mode), existing repos (auto-detection), and re-runs safely (upgrade mode).'
argument-hint: 'Optional: describe what you want to build or path to the project root'
---

# Agent Bootstrap

Bootstrap any repository for fully autonomous AI-driven software development. One command takes a repo from zero to an agent-ready workspace with task management, evidence gates, and a loop protocol.

## When to Use

- Starting a new project from scratch (empty repo)
- Onboarding an existing codebase for AI development
- Preparing a repo for autonomous feature development
- The user says "bootstrap", "set up harness", "agent readiness", "initialize project"
- Re-running to upgrade an existing harness

## Overview

The skill runs in 3 phases:

```
Phase 1: SCAN + ASSESS  →  Understand the repo (or interview if empty)
Phase 2: BOOTSTRAP       →  Create .codestudio/ harness + fix critical gaps
Phase 3: HANDOFF         →  Seed tasks (if known) + instruct user to run @orchestrator
```

After bootstrap completes, the **orchestrator agent** (`@orchestrator`) takes over all feature work: creating tasks, planning, building, verifying, committing, and reviewing.

---

## Phase 1 — SCAN + ASSESS

Scan the repository to detect project characteristics and assess readiness. Read the reference documents:

```
read_file: ./references/detection-rules.md
read_file: ./references/readiness-criteria.md
```

### For Empty Repos (no source files)

Enter **interview mode**. Read and follow the `interview-me` skill:

```
read_file: ~/.agents/skills/interview-me/SKILL.md
```

Use the interview-me skill's one-question-at-a-time approach to extract what the user actually wants. The interview must cover these areas (but let the skill guide the conversation flow):

1. **What are you building?** (product description — needed to understand scope and seed tasks)
2. **Who is it for?** (users, developers, internal — shapes architecture decisions)
3. **What tech stack?** (or recommend based on goal — needed for gates.yaml and project-context.md)
4. **What architecture?** (monolith, microservices, app router, etc. — needed for project-context.md)
5. **Any conventions to enforce?** (naming, patterns, linting preferences)
6. **What features do you need first?** (needed to seed initial tasks)

Don't ask all 6 as a list. Follow the interview-me skill's protocol: ask one question, probe the answer, then move to the next when confident. Stop when you have ~95% confidence about the setup AND the initial feature scope.

If the `interview-me` skill is not installed, fall back to asking the questions directly using the `ask-questions` tool (one at a time, not all at once).

Use answers to populate all template variables AND create initial tasks.

### For Existing Repos (has source files)

Run auto-detection. Inspect the project:

1. **List root directory** — find build files, configs, source directories
2. **Detect language/framework** from manifest files (package.json, requirements.txt, Cargo.toml, etc.)
3. **Detect test/lint/build tools** — for verification gates
4. **Count source files** — gauge complexity
5. **Check for .git** — enable/disable COMMIT stage
6. **Scan for security signals** — auth, JWT, crypto patterns
7. **Check for UI files** — tsx, jsx, vue, svelte, components/
8. **Check for existing `.codestudio/`** — upgrade mode

9. **Extract project context** (the critical step for existing repos):
   - Read 2-3 representative source files → detect naming conventions, patterns, error handling
   - Read directory structure → infer architecture layers (routes → services → models, etc.)
   - Read config files → identify linting rules, formatting, CI expectations
   - Read `.gitignore`, lock files → identify boundaries (don't-touch files)

Record findings:
- `PROJECT_NAME`: directory name or package name
- `TIER`: L0/L1/L2/L3 based on what testing actually exists (see detection-rules.md)
- `GATES`: ordered list of evidence gates from detected tools
- `HAS_GIT`: true/false
- `SECURITY_FLAGS`: list of detected patterns
- `UI_PROJECT`: true/false
- `SOURCE_COUNT`: number of source files
- `UPGRADE_MODE`: true if `.codestudio/` exists
- `STACK`: language, framework, key libraries
- `ARCHITECTURE`: directory layout and layer relationships
- `CONVENTIONS`: naming, patterns, error handling style
- `BOUNDARIES`: files/dirs that should not be modified
- `COVERAGE_TOOL`: detected coverage tool

### Readiness Assessment

Score the repo against these criteria (pass/fail, not complex scoring):

| Check | What | Status |
|-------|------|--------|
| Linter | Config file exists, lint command works | ✅/❌ |
| Type checker | tsconfig / mypy / type annotations | ✅/❌ |
| Formatter | Prettier / Black / rustfmt config | ✅/❌ |
| Tests | Test files exist, test command works | ✅/❌ |
| Build | Build command exists and runs | ✅/❌ |
| Coverage tool | Coverage reporter detected | ✅/❌ |
| README | Exists with setup instructions | ✅/❌ |
| AGENTS.md | Agent instructions exist | ✅/❌ |
| Git | Repository initialized | ✅/❌ |
| CI | Pipeline config exists | ✅/❌ |

### Present Proposal (never skip)

Before generating files, show the user:

1. **Detection summary** — what was found with evidence (file paths, dependency names)
2. **Tier selection** — which tier based on what actually exists:
   - **L0 Unverified**: no tests → build + lint only
   - **L1 Diff-verified**: tests exist → tests + coverage
   - **L2 Verified**: good test suite → full suite + audit
   - **L3 Hardened**: mature project → mutation + perf budgets
3. **Gate table** — each gate with command, threshold, readiness
4. **Readiness report** — what's ✅ READY, what ⚠️ WILL FIX, what 📋 RECOMMENDED (not forced)
5. **File list** — what will be created, what will be preserved

**For existing repos, explicitly show "WILL NOT TOUCH"** — list their existing configs that bootstrap respects.

Ask: `Proceed? [y / adjust tier / adjust gates / explain]`

---

## Phase 2 — BOOTSTRAP

Create the `.codestudio/` directory with all harness files.

### Read templates from:
```
./templates/
```

### Files to generate:

#### Always generate:

1. **`.codestudio/task.py`** — from `./scripts/task.py` (copy as-is)
   Task manager script. Requires Python 3.7+.
   Requires PyYAML (`pip install pyyaml`) when `gates.yaml` is present.

2. **`.codestudio/harness-lock.json`** — from `harness-lock.json.tmpl`
   Copy as-is. **Preserve existing if upgrade mode.**

3. **`.codestudio/.gitignore`** — from `gitignore.tmpl`
   Copy as-is.

4. **`.codestudio/agents/orchestrator.agent.md`** — from `orchestrator.agent.md.tmpl`
   Replace `{{PROJECT_NAME}}`.
   Add security notes if SECURITY_FLAGS detected.
   Add UI notes if UI_PROJECT is true.
   **Does NOT touch any existing `codestudio-instructions.md`.**

5. **`.codestudio/skills/`** — copy all files from `./templates/skills/` as-is:
   - `spec.md` — Spec-Driven Development procedure
   - `plan.md` — Planning and Task Breakdown procedure
   - `tdd.md` — Test-Driven Development procedure
   - `debugging.md` — Debugging and Error Recovery procedure
   - `commit.md` — Git Commit Discipline procedure
   - `review.md` — Code Review and Quality procedure

   These are the SDLC skill files the orchestrator reads at each loop stage.
   They are **self-contained inside the project harness** — no external dependency required.
   **Preserve existing if upgrade mode** (do not overwrite customised skills).

6. **`.codestudio/instructions/task-conventions.instructions.md`** — from `task-conventions.instructions.md.tmpl`
   Replace `{{PROJECT_NAME}}`.

7. **`.codestudio/catalogs/defects-{{FRAMEWORK}}.md`** — dynamically generated using `defects-catalog.tmpl`
   
   This file is NOT copied from a static catalog. Generate it at setup time:
   1. Read the template at `./templates/defects-catalog.tmpl` for format and quality criteria
   2. Read 1-2 example catalogs from `./catalogs/examples/` for quality baseline
   3. Generate 15 framework-specific defect entries for the detected stack
   4. Each entry must describe a real bug pattern with real consequences
   5. Write to `.codestudio/catalogs/defects-{{FRAMEWORK}}.md`
   
   For multi-framework projects: generate one catalog per framework.
   **Preserve existing if upgrade mode.**

8. **`.codestudio/gates.yaml`** — from `gates.yaml.tmpl`
   Source of truth for verification gates.
   Replace `{{TIER}}` with detected tier.
   Replace `{{GATES}}` with YAML gate entries from detected tools.
   
   **For existing repos**: use THEIR actual commands from package.json/Makefile/etc.
   **For coverage**: prefer `coverage-diff` type (diff-scoped) over `coverage` (global) on brownfield repos. Diff coverage measures only lines this task changed — enforceable at 80% from day one.
   **For coverage threshold**: use current coverage level (not aspirational 80%) with ratchet UP.
   Only include gates for tools that actually exist.
   **Preserve existing if upgrade mode.**

9. **`.codestudio/tasks/index.json`** — from `index.json.tmpl`
   Empty array for new projects. **Preserve existing if upgrade mode.**

10. **`.codestudio/progress.md`** — from `progress.md.tmpl`
   Replace `{{PROJECT_NAME}}`. **Preserve existing if upgrade mode.**

11. **`.codestudio/project-context.md`** — from `project-context.md.tmpl`
    
    **For existing repos**: populate from scan findings (extracted from source files, configs, directory structure).
    **For empty repos**: populate from interview answers.
    
    Replace template variables:
    - `{{PROJECT_NAME}}`, `{{STACK}}`, `{{ARCHITECTURE}}`, `{{CONVENTIONS}}`
    - `{{BOUNDARIES}}`, `{{TIER}}`, `{{TIER_DESCRIPTION}}`, `{{GATES_SUMMARY}}`
    
    **Preserve existing if upgrade mode.**

#### Create if missing (don't overwrite existing):

12. **`AGENTS.md`** (repo root) — from `AGENTS.md.tmpl`
    Agent instructions for the repo. Only create if no AGENTS.md exists.
    Replace `{{PROJECT_NAME}}`, `{{STACK}}`, `{{CONVENTIONS}}`.

### Upgrade mode behavior:

| File | Action |
|------|--------|
| `task.py` | Overwrite (latest version) |
| `harness-lock.json` | **PRESERVE** |
| `.gitignore` | Overwrite |
| `gates.yaml` | **PRESERVE** |
| `agents/orchestrator.agent.md` | Overwrite (re-detect settings) |
| `instructions/task-conventions.instructions.md` | Overwrite |
| `skills/*.md` | **PRESERVE** (keep project-customised skills) |
| `catalogs/defects-*.md` | **PRESERVE** |
| `project-context.md` | **PRESERVE** |
| `tasks/index.json` | **PRESERVE** |
| `tasks/*.md` | **PRESERVE** |
| `progress.md` | **PRESERVE** |
| `evidence/` | **PRESERVE** |
| `AGENTS.md` | **PRESERVE** |

### SDLC Skills — no external dependency required

SDLC skill files are bundled with the harness and copied from `./templates/skills/` into `.codestudio/skills/` in step 5 above. The orchestrator reads them directly from the project — no global install, no network, no `~/.agents/skills/` path needed.

The skills copied are: `spec.md`, `plan.md`, `tdd.md`, `debugging.md`, `commit.md`, `review.md`.

They are self-contained and always present after bootstrap. The orchestrator will never encounter a missing skill file.

---

## Phase 3 — HANDOFF

### For Empty Repos (user described what to build)

Seed initial tasks from the interview:

```bash
python3 .codestudio/task.py add "Initialize project with [framework]"
python3 .codestudio/task.py add "Set up database schema" --needs T-001
python3 .codestudio/task.py add "[First feature from interview]" --needs T-001
# ...etc based on what the user described
```

### For Existing Repos (user hasn't said what to build yet)

Do NOT seed tasks. The orchestrator will ask.

### For Existing Repos (user described work in the bootstrap prompt)

If the user ran `/agent-bootstrap Add Stripe billing`, seed those tasks too.

### Smoke Test

```bash
python3 .codestudio/task.py status
```

### Final Output

```
✅ Bootstrap complete — .codestudio/

  Detected:  [stack]
  Tier:      [L0-L3]
  Gates:     [count] configured
  Tasks:     [count] seeded
  Skills:    [count] available

  📋 Readiness:
     ✅ [passing checks]
     📋 Recommended: [non-blocking suggestions]

  Next: Run @orchestrator to start building.
        The orchestrator will plan features, create tasks,
        and implement them autonomously.
```

---

## Key Principles

1. **Bootstrap sets up the workshop. Orchestrator does the work.**
   Bootstrap creates harness + seeds known tasks, then exits. All ongoing feature work (creating new tasks, planning, building, reviewing) is the orchestrator's job.

2. **For empty repos, bootstrap MUST interview.**
   Can't set up gates without knowing the stack. Can't seed tasks without knowing what to build. The interview covers both setup AND initial planning.

3. **For existing repos, bootstrap adapts — never overwrites.**
   Uses their existing linter, test runner, build commands. Sets coverage ratchet at current level. Never creates configs that conflict with what exists.

4. **The agent adapts to the codebase. The codebase never adapts to the agent.**

## Reference Documents

- **Readiness criteria**: `./references/readiness-criteria.md`
- **Detection rules**: `./references/detection-rules.md`
- **Loop protocol**: `./references/loop-protocol.md`
- **Stages catalog**: `./references/stages-catalog.md`
