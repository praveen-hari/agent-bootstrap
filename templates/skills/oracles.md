# SKILL: Oracles — Where Truth Comes From

When making a decision about how something should behave, consult sources in order
and **cite the one that decided**. A decision recorded without naming its source is
incomplete.

## Authority precedence — for questions of correctness

| Rank | Class | Weight |
|------|-------|--------|
| 1 | Standards and normative specifications (RFC, WHATWG, ECMA, ISO) | **normative** |
| 2 | First-party vendor specification or documentation (framework docs, API reference) | **normative** |
| 3 | Machine-readable schema, type definitions, API contracts (OpenAPI, `.d.ts`, XSD) | **normative** |
| 4 | Accepted ADRs in this project | **binding** |
| 5 | This project's own technical specifications | **binding** |
| 6 | Observed behaviour of the reference implementation | evidence |
| 7 | Observed behaviour of a competing implementation | evidence |
| 8 | Community sources, blogs, forum answers, Stack Overflow | evidence — weakest |

**Ranks 1–3 are normative** — they say what must be true.
**Ranks 4–5 are binding** — this project has decided; changing it needs a new ADR.
**Ranks 6–8 are evidence only.** "The browser does it this way" is an observation, not a citation. It can inform a decision; it cannot settle one.

## How to cite in `## What`

```markdown
**Sources consulted:**
- https://react.dev/reference/react/useState — rank 2 — decided: state updates are async
- src/specs/auth.md — rank 5 — decided: session expires after 30 min idle
```

## Common rank-2 sources by stack

| Stack | Primary source |
|-------|---------------|
| React | react.dev reference docs |
| Angular | angular.dev reference docs |
| ASP.NET Core | learn.microsoft.com/aspnet/core reference |
| Blazor | learn.microsoft.com/aspnet/core/blazor |
| Python | docs.python.org official docs |
| Node.js | nodejs.org/api official docs |
| Web platform | MDN Web Docs (backed by WHATWG/W3C) |

## What to do when sources disagree

1. Higher rank wins
2. If two rank-2 sources conflict, note both, state which you followed and why, and record it as an open question for human review
3. If no source covers the case, record your assumption explicitly: `assumed: <choice> → pinned by: <test name>`

## Validation hierarchy — for questions of evidence

When deciding whether something is correct, the strength of evidence matters:

1. **Specification** — says what must be true (strongest)
2. **Independent validator** — a tool that did not produce the artifact
3. **Independent producer + consumer** — a different implementation round-trips it
4. **The code's own tests** — proves only that the code does what its author believed (weakest alone)

A system's own tests, passing, prove almost nothing about correctness in isolation. They prove the code does what its author believed — and the author was the same agent. Both can be wrong in the same direction.

This is why mutation testing (break the source, check the suite notices) is the
upgrade from "tests exist" to "tests are meaningful".
