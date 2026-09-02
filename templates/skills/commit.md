# SKILL: Git Commit Discipline

Every verified subtask gets one atomic commit. Commit messages are permanent documentation.

## Commit Format (Mandatory)

```
<type>(<scope>): <short imperative description>

<optional body: what changed and WHY — context not visible in the diff>
```

**Short description rules:**
- Imperative mood: "add", "fix", "remove" — not "added", "fixing", "removes"
- ≤ 72 characters
- Standalone: someone reading git log should understand the change without opening the diff

**Types:**
| Type | When to use |
|------|------------|
| `feat` | New behaviour visible to the user or API consumer |
| `fix` | Corrects wrong behaviour |
| `test` | Adds or updates tests only |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `docs` | Documentation only |
| `chore` | Tooling, dependencies, config — no production code change |
| `ci` | CI pipeline changes |
| `style` | Formatting, whitespace — no behaviour change |
| `perf` | Performance improvement |

**Examples:**
```
feat(orders): add validation returning 400 when orderId is malformed
fix(auth): prevent session token reuse after logout
test(tasks): add coverage for concurrent task creation
refactor(utils): extract date formatting into shared helper
```

**Anti-patterns — these are useless in history:**
- `"Fix bug"` · `"Add patch"` · `"Update stuff"` · `"Phase 1"` · `"WIP"`

## Atomic Commit Rules

1. **One subtask = one commit.** Never combine unrelated changes.
2. **Separate refactoring from feature work.** They are two different commits, even if done in the same session.
3. **Never commit a failing test, broken build, or passing-but-weakened gate.** Gates must pass before committing.
4. **Keep commits small (~100 lines changed).** Changes over ~1000 lines should be split into multiple commits.
5. **Commit immediately after verify passes.** Do not accumulate multiple verified subtasks before committing.

## Body (When to Write One)
Write a body when:
- The reason for the change is not obvious from the description
- You made a non-obvious design decision
- The change fixes a subtle bug that needs context to understand
- There are known limitations or follow-up work

The body explains the *why*. The diff shows the *what*.

## Size Guidelines
```
~100 lines changed  → Good. Easy to review and revert.
~300 lines changed  → Acceptable for a single logical change.
~1000 lines changed → Too large. Split into multiple commits.
```
