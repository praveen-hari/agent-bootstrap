# Detection Rules

Rules for auto-detecting project characteristics during Phase 1 (SCAN + ASSESS).

## Language / Framework Detection

| Signal | Detected As | Default Gate Commands |
|--------|------------|----------------------|
| `package.json` | Node.js | `npm run lint`, `npm test` |
| `package.json` + `next.config.*` | Next.js | `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build` |
| `package.json` + `vite.config.*` | Vite | `npm run lint`, `npx tsc --noEmit`, `npm test` |
| `package.json` + `nuxt.config.*` | Nuxt | `npm run lint`, `npx tsc --noEmit`, `npm test`, `npm run build` |
| `requirements.txt` or `pyproject.toml` or `setup.py` | Python | `ruff check .`, `pytest` |
| `Cargo.toml` | Rust | `cargo clippy -- -D warnings`, `cargo test` |
| `*.csproj` or `*.sln` | .NET | `dotnet build`, `dotnet test` |
| `go.mod` | Go | `go vet ./...`, `go test ./...` |
| `Makefile` | Make-based | `make test` |
| `build.gradle` or `pom.xml` | Java/Kotlin | `./gradlew test` or `mvn test` |
| `mix.exs` | Elixir | `mix test` |
| `Gemfile` | Ruby | `bundle exec rspec` |
| `composer.json` | PHP | `composer test` |

**Package manager detection:**
| Signal | Package Manager |
|--------|----------------|
| `pnpm-lock.yaml` | pnpm |
| `yarn.lock` | yarn |
| `bun.lockb` | bun |
| `package-lock.json` | npm |

Use the detected package manager in gate commands (e.g., `pnpm test` not `npm test`).

**For existing repos**: Check `package.json` `scripts` section for actual command names. Use THEIR script names (e.g., `pnpm lint` if they have a `lint` script, not `npx eslint .`).

If multiple signals exist (monorepo), prefer the root-level manifest or primary build file.

## Default Gates by Stack

Each detected stack produces gates for `.codestudio/gates.yaml`. These are starting points — adjust based on what's actually installed.

### Node.js / Next.js / Vite (TypeScript)
```yaml
gates:
  - id: lint
    command: "npm run lint"
    type: exit-code
    threshold: 0
    ratchet: false
  - id: typecheck
    command: "npx tsc --noEmit"
    type: exit-code
    threshold: 0
    ratchet: false
  - id: test
    command: "npm test"
    type: exit-code
    threshold: 0
    ratchet: true
  - id: build
    command: "npm run build"
    type: exit-code
    threshold: 0
    ratchet: false
  - id: coverage
    command: "npx jest --coverage --coverageReporters=json-summary"
    type: coverage
    threshold: 80
    ratchet: true
```

### Python
```yaml
gates:
  - id: lint
    command: "ruff check ."
    type: exit-code
    threshold: 0
    ratchet: false
  - id: typecheck
    command: "mypy ."
    type: exit-code
    threshold: 0
    ratchet: false
  - id: test
    command: "pytest"
    type: exit-code
    threshold: 0
    ratchet: true
  - id: coverage
    command: "pytest --cov --cov-report=json"
    type: coverage
    threshold: 80
    ratchet: true
```

### Rust
```yaml
gates:
  - id: lint
    command: "cargo clippy -- -D warnings"
    type: exit-code
    threshold: 0
    ratchet: false
  - id: test
    command: "cargo test"
    type: exit-code
    threshold: 0
    ratchet: true
```

### .NET
```yaml
gates:
  - id: build
    command: "dotnet build"
    type: exit-code
    threshold: 0
    ratchet: false
  - id: test
    command: "dotnet test"
    type: exit-code
    threshold: 0
    ratchet: true
  - id: format
    command: "dotnet format --verify-no-changes"
    type: exit-code
    threshold: 0
    ratchet: false
  - id: coverage
    command: "dotnet test --collect:\"XPlat Code Coverage\""
    type: coverage
    threshold: 80
    ratchet: true
```

### Go
```yaml
gates:
  - id: vet
    command: "go vet ./..."
    type: exit-code
    threshold: 0
    ratchet: false
  - id: test
    command: "go test ./..."
    type: exit-code
    threshold: 0
    ratchet: true
  - id: coverage
    command: "go test -coverprofile=cover.out ./..."
    type: coverage
    threshold: 80
    ratchet: true
```

Only include gates for tools that are **actually detected** in the project.

### Diff-Scoped Coverage (coverage-diff gate type)

For existing repos, prefer `coverage-diff` over `coverage`. This measures only lines changed by the current task, not the entire codebase.

**Why this matters:** Global coverage on a 15-year-old codebase might be 4%. Setting a global threshold is either unreachable (gate disabled) or meaningless (set to 4%). Diff coverage at 80% is enforceable from day one because it only concerns code just written.

```yaml
  - id: coverage-diff
    command: "npm test -- --coverage"    # YOUR coverage command
    type: coverage-diff                   # diff-scoped, not global
    threshold: 80                         # of lines this task changed
    ratchet: true
```

`task.py` intersects coverage data with `git diff <baseSha>..HEAD` to compute diff coverage. On failure, it names the exact uncovered lines:

```
FAIL coverage-diff  diffLineRate=44.44%
     Add tests covering these changed lines:
         src/calc.py:12
         src/calc.py:16
```

Use `coverage-diff` at L1+. Use `coverage` (global) only at L2+ on projects with good baseline coverage.

## Project Structure Signals

| Signal | Effect |
|--------|--------|
| `.git` exists | COMMIT stage enabled |
| No `.git` | Skip COMMIT stage. Note: "Initialize git when ready." |
| `src/` or `lib/` present | Standard project layout |
| No source files | **Empty repo** → enter interview mode |
| > 10 source files | Complex project — deep scan for patterns |
| ≤ 10 source files | Small project — lightweight context |

## Security Signals

| Pattern | Effect |
|---------|--------|
| `auth`, `login`, `password`, `session` in filenames/imports | Flag SECURITY |
| `jwt`, `token`, `oauth` in dependencies | Flag SECURITY |
| `crypto`, `encrypt`, `hash` in source | Flag SECURITY |
| `.env` file present | Note: "Secrets management in use." |
| `api/`, `routes/`, `endpoints/` directories | Flag: "API endpoints — validate input." |

## UI Detection

| Signal | Effect |
|--------|--------|
| `*.tsx`, `*.jsx`, `*.vue`, `*.svelte` files | Flag UI project |
| `components/`, `pages/`, `views/` directories | Flag UI structure |
| CSS/SCSS/Tailwind config present | Note styling framework |

## Test Framework Detection

| Signal | Framework | Command |
|--------|----------|---------|
| `jest.config.*` or `"jest"` in package.json | Jest | `npx jest` |
| `vitest.config.*` | Vitest | `npx vitest run` |
| `pytest.ini` or `conftest.py` | pytest | `pytest` |
| `*.test.rs` or `#[cfg(test)]` | Rust tests | `cargo test` |
| `*_test.go` | Go tests | `go test ./...` |
| `*.spec.ts` + `cypress.config.*` | Cypress | `npx cypress run` |
| `playwright.config.*` | Playwright | `npx playwright test` |

## Coverage Tool Detection

| Signal | Tool | Coverage Command |
|--------|------|-----------------|
| `jest.config.*` with `coverageReporters` | Jest/c8 | `npx jest --coverage --coverageReporters=json-summary` |
| `vitest.config.*` with `coverage` | c8/istanbul | `npx vitest run --coverage` |
| `pytest-cov` in requirements | pytest-cov | `pytest --cov --cov-report=json` |
| `coverlet` in .csproj | Coverlet | `dotnet test --collect:"XPlat Code Coverage"` |
| Go project | go cover | `go test -coverprofile=cover.out ./...` |
