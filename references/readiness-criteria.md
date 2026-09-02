# Readiness Criteria

Assessment checklist for determining if a repo is ready for autonomous AI development. Each criterion is pass/fail — no complex scoring.

## Critical (blocks the loop)

These must exist for the orchestrator to work. Bootstrap will create them if missing.

| Criterion | What to Check | How to Fix |
|-----------|--------------|------------|
| **Task system** | `.codestudio/task.py` exists | Bootstrap creates it |
| **Evidence gates** | `.codestudio/gates.yaml` with ≥1 gate | Bootstrap creates from detected tools |
| **Orchestrator** | `.codestudio/agents/orchestrator.agent.md` | Bootstrap creates it |
| **Project context** | `.codestudio/project-context.md` | Bootstrap creates from scan/interview |
| **At least one lint/build gate** | A command that catches basic errors | Detect from existing config or interview |

## Important (degrades quality without them)

These significantly improve autonomous development but aren't strict blockers.

| Criterion | What to Check | How to Fix |
|-----------|--------------|------------|
| **Linter configured** | ESLint, ruff, clippy, etc. config file exists | Note in readiness report |
| **Type checker** | tsconfig.json, mypy config, or language with static types | Note in readiness report |
| **Test runner** | Test command exists and runs successfully | Note in readiness report |
| **Coverage tool** | Coverage reporter configured (jest --coverage, pytest-cov, etc.) | Note in readiness report |
| **Git initialized** | `.git/` exists | Note in readiness report |
| **AGENTS.md** | Agent instructions at repo root | Bootstrap creates if missing |
| **README** | Exists with setup/run instructions | Note in readiness report |

## Recommended (nice to have)

These improve the overall developer/agent experience but are not required.

| Criterion | What to Check | Recommendation |
|-----------|--------------|----------------|
| **Formatter** | Prettier, Black, rustfmt config | Prevents style debates |
| **Pre-commit hooks** | .husky/, .pre-commit-config.yaml | Catches errors before commit |
| **CI pipeline** | .github/workflows/, .gitlab-ci.yml, etc. | Automated validation |
| **Devcontainer** | .devcontainer/devcontainer.json | Reproducible environment |
| **CODEOWNERS** | CODEOWNERS file | Review routing |
| **Issue templates** | .github/ISSUE_TEMPLATE/ | Structured task input |
| **PR template** | .github/pull_request_template.md | Consistent PR format |
| **Branch protection** | Protected main/master branch | Prevents direct pushes |
| **Secret scanning** | Enabled in repo settings | Prevents credential leaks |
| **Structured logging** | Logger library with structured output | Better debugging |

## Tier Determination

The tier is based on what **actually exists**, not what should exist:

| Tier | Name | Criteria | Gates |
|------|------|----------|-------|
| **L0** | Unverified | No tests, or tests don't run | build + lint only |
| **L1** | Diff-verified | Tests exist AND pass | build + lint + typecheck + test + coverage |
| **L2** | Verified | Good test suite + security scanning | L1 + audit |
| **L3** | Hardened | Mature project with performance tracking | L2 + mutation + perf budgets |

### Tier Inference Rules

- **No test files found** → L0
- **Test files exist but no test command** → L0 (note: "tests found but no runner configured")
- **Test command exists and test files exist** → L1
- **L1 + security scanner configured (npm audit, safety, etc.)** → L2
- **L2 + mutation testing or performance benchmarks** → L3

### Coverage Threshold Rules

- **New project (empty repo)**: Set coverage threshold to 80% (aspirational). Use `coverage-diff` gate type.
- **Existing project with coverage data**: Use `coverage-diff` at 80% (diff-scoped). Set global `coverage` threshold to current level with ratchet UP.
- **Existing project without coverage data**: Use `coverage-diff` at 80%. Global coverage starts at 0% with ratchet UP.

**Prefer `coverage-diff` over `coverage` for brownfield repos.** Diff coverage asks "of the lines this task changed, how many are covered?" — enforceable at 80% from day one on any codebase. Global coverage asks "what % of the entire codebase is covered?" — often unenforceable.

The ratchet means coverage can only go up from whatever it is today. We never demand instant perfection from existing codebases.

## Readiness Report Format

The assessment should produce a report like this:

```
📊 Agent Readiness Report — {{PROJECT_NAME}}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Stack: [detected stack]
Tier:  [L0-L3] ([tier name])

✅ READY (loop can use these)
   • [tool]: [description] (found [evidence])

⚠️ WILL FIX (needed for the loop)
   • [what's missing] → will create

📋 RECOMMENDED (not blocking, fix later)
   • [suggestion] ([reason])

✅ WILL NOT TOUCH (existing configs respected)
   • [their existing config files]

Proceed? [y / adjust / assess-only]
```
