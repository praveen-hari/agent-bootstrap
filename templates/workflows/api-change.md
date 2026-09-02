# Workflow: api-change — a public signature changes

**Binding policies:** `public-api-is-a-contract` · `never-weaken` · `evidence-before-done`

**This workflow always touches the autonomy boundary. An irreversible public API change is a Lane-3 decision — park it for a human.**

## What counts as public

| Project type | Public surface |
|---|---|
| Component library | Every exported type, prop, event, slot, CSS custom property |
| Service / API | Every route, request/response shape, status code, header |
| Internal package | Everything importable across a package boundary |
| Application | URLs, persisted data shapes, config keys, CLI flags |

## 1. CLASSIFY

| Class | Definition | Path |
|---|---|---|
| **Additive** | New optional surface; every existing caller still compiles and behaves | Proceed |
| **Behavioural** | Signature identical, semantics differ | **Park — most dangerous class, invisible to callers** |
| **Breaking** | An existing caller stops working | **Park** |

## 2. ANALYSE IMPACT

- Count call sites in-repo
- Name the migration path for each affected caller
- Estimate blast radius honestly — "probably fine" is not an estimate

## 3. PARK (if breaking or behavioural)

Write a `DECISIONS-REQUIRED.md` entry with: the change, its class, the impact, **your recommendation**, alternatives considered, and the cost of deferring.

Mark affected tasks blocked. Pick the next ready task. Do not stall the loop waiting for the decision.

## 4. AFTER APPROVAL — implement with a migration path

- Additive first wherever possible: add new surface, deprecate old, remove in a later version
- Deprecation message names the replacement and the removal version
- Update the API baseline (`PublicAPI.Shipped.txt`, api-extractor report, OpenAPI doc) **in the same commit** — a baseline updated separately is a baseline that drifts
- Write the migration note in the same change set

## 5. VERIFY

All gates pass including any API baseline gate.

## Definition of done

- [ ] Change classified (additive / behavioural / breaking) — stated in `## What`
- [ ] Breaking or behavioural change approved by a named human (recorded in `## Log`)
- [ ] API baseline updated in the same commit
- [ ] Migration path documented with before/after
- [ ] All gates pass
