# SKILL: Planning and Task Breakdown

Decompose a spec into dependency-ordered, vertically-sliced subtasks before writing any code.

## Mandatory Steps

### Step 1 — Read-Only Mode First
Before writing the plan:
- Read the spec (`## What` in the task file)
- Read relevant source files to understand existing patterns
- Map dependencies between components
- Identify risks and unknowns

**Do NOT write code during planning.** The output of this stage is a plan document, not implementation.

### Step 2 — Map the Dependency Graph
Identify what depends on what and order work bottom-up:
```
Database schema
    └── API types/models
            └── API endpoints
                    └── Frontend API client
                            └── UI components
```
Build foundations first. Never start a layer before its dependency exists.

### Step 3 — Slice Vertically, Not Horizontally
Each subtask delivers one complete end-to-end path, not a horizontal layer.

❌ **Bad (horizontal — value delayed until the end):**
```
Subtask 1: Build entire database schema
Subtask 2: Build all API endpoints
Subtask 3: Build all UI components
```

✅ **Good (vertical — value delivered per subtask):**
```
Subtask 1: User can create a task (schema + API + UI for creation)
Subtask 2: User can list tasks (query + API + UI for list)
Subtask 3: User can delete a task (delete + API + UI + confirmation)
```

### Step 4 — UI Is a First-Class Concern
If the task touches any user-facing UI, add these as the first two subtasks before any feature work:
```
Subtask 0: Set up design system tokens (colors, typography, spacing, CSS variables)
Subtask 1: Build app shell layout (navigation, header, content area, routing)
```
These are prerequisites. Every feature subtask depends on them.

For every UI subtask, acceptance criteria MUST include:
- Styled with design system tokens — no arbitrary hex values or magic pixel numbers
- Responsive: works at 320px, 768px, 1024px, 1440px
- Keyboard accessible: Tab navigation, Enter/Space activation
- Loading state: skeleton placeholder (not spinner)
- Empty state: illustration/icon + message + CTA when no data
- Error state: error message + retry action when operation fails

### Step 5 — Each Subtask Names Its Test
Every behaviour-adding subtask must name the specific test that will verify it.
If you cannot name the test, go back to SPEC — the acceptance criteria are not concrete enough.

### Step 6 — Size Each Subtask
| Size | Files touched | Action |
|------|--------------|--------|
| XS | 1 | Fine |
| S | 1–2 | Fine |
| M | 3–5 | Fine |
| L | 5–8 | Split it |
| XL | 8+ | Always split |

One subtask = one commit's worth of work (~100 lines max).

### Step 7 — Write `## Plan` in the Task File

```markdown
## Plan

- [ ] Subtask 1: [title] — verified by `[exact test name]`
- [ ] Subtask 2: [title] — verified by `[exact test name]`
- [ ] Subtask 3: [title] — verified by `[exact test name]`
```

### Step 8 — Gate: Present and Wait
**Present the completed plan to the user. Do not proceed to BUILD until the user confirms.** The plan is the contract for what gets built.

## Quality Bar

A plan is done when:
- Every subtask has a named verification test or gate command
- Subtasks are ordered by dependency (foundations before consumers)
- No subtask touches more than ~5 files or ~100 lines
- The plan slices vertically — each subtask delivers working behaviour
