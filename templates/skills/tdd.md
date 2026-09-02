# SKILL: Test-Driven Development

Write a failing test before writing the code that makes it pass. Tests are proof — "seems right" is not done.

## The TDD Cycle (Mandatory for Every Subtask)

```
    RED                  GREEN                REFACTOR
 Write a failing  ──→  Write minimal   ──→  Clean up the      ──→ (next subtask)
 test from spec        code to pass         implementation
      │                     │                    │
      ▼                     ▼                    ▼
  Test FAILS           Test PASSES          Tests still PASS
```

### Step 1 — RED: Write the Test First
Write the test from the acceptance criteria in `## What`. Run it. It **MUST fail**.
- A test that passes immediately proves nothing — the test is wrong, fix it before proceeding
- A test written after the code encodes what the code does, not what was asked for
- Test name must match the acceptance criterion exactly (e.g. `OrderController_Create_Returns400_WhenOrderIdMalformed`)

```typescript
// RED: This test fails because the implementation does not exist yet
it('returns 400 with ProblemDetails when orderId is malformed', async () => {
  const response = await request(app).post('/orders').send({ orderId: 'bad!' });
  expect(response.status).toBe(400);
  expect(response.body).toMatchObject({ type: expect.stringContaining('ProblemDetails') });
});
```

### Step 2 — GREEN: Write Minimum Code to Pass
Write the smallest amount of code that makes the failing test pass. No over-engineering. No code that is not required by a failing test.

### Step 3 — REFACTOR: Clean Up With Tests Green
With all tests passing, improve the implementation:
- Extract shared logic, improve naming, remove duplication
- Run tests after **every** refactor step — catch regressions immediately
- Do not change behaviour during refactor

### Step 4 — GATES: Run All Gates
After each subtask's RED→GREEN→REFACTOR cycle:
- Run ALL gate commands from `gates.yaml`
- Every gate must pass before moving to the next subtask
- **NEVER** weaken a gate, skip a test, or lower a threshold to make a gate pass

### Step 5 — CHECK: Tick the Subtask
Tick the subtask checkbox in `## Plan`. Commit (see commit skill).

## Bug Fix Variant — The Prove-It Pattern
For bug fixes, **do not start by fixing**. Start by reproducing:
```
1. Write a test that demonstrates the bug → it MUST fail (confirming the bug exists)
2. Implement the fix
3. Test PASSES (proving the fix works, not just the symptoms)
4. Run full test suite (no regressions introduced)
```

## Test Quality Rules

**Test state, not interactions.**
Assert on the outcome of an operation, not which internal methods were called.
Tests that verify method call sequences break on refactor even when behaviour is unchanged.

**DAMP over DRY.**
Each test should be self-contained and readable without tracing through shared helpers.
Duplication in tests is acceptable — it makes each test independently understandable.

**Prefer real implementations over mocks.**
Use the simplest test double that gets the job done.
The more your tests use real code, the more confidence they provide.

**Test pyramid ratios.**
- ~80% Unit: pure logic, no I/O, milliseconds each
- ~15% Integration: API boundaries, database, component interactions
- ~5% E2E: critical user flows only, real browser or full stack

## Incremental Discipline
- Implement one slice, test it, verify it, then expand — never accumulate more than ~100 lines before testing
- Each increment leaves the system in a working, testable state
- If the next change breaks something, the last commit is the safe revert point
- One subtask = one commit

## If UI Is Involved
Every UI subtask must verify all three states:
- **Loading:** skeleton placeholder (not a spinner)
- **Empty:** illustration/icon + message + CTA
- **Error:** error message + retry action
No blank screens. These are not polish — they are required behaviour.
