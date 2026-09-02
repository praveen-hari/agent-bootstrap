# Python Defect Catalog

Use during REVIEW stage. For each finding: name the rule, check if it's enforced in config, prefer the config-level fix.

| # | Defect | What goes wrong | Verify |
|---|--------|----------------|--------|
| P01 | **Mutable default argument** | `def f(items=[])` — shared list across calls, silent data corruption | Default args must be `None`; assign inside function body |
| P02 | **Bare except** | `except:` or `except Exception:` catches `KeyboardInterrupt`, `SystemExit` | Catch specific exceptions; enable `ruff` rule `E722` (config fix) |
| P03 | **Unparameterized SQL** | `f"SELECT * FROM x WHERE id={id}"` → SQL injection | Use parameterized queries: `cursor.execute("... WHERE id = %s", (id,))` |
| P04 | **Missing type hints on public API** | Public functions without type hints → callers guess at contracts | All public functions and methods need parameter + return type hints |
| P05 | **assert in production** | `assert x > 0` is removed by `python -O` → silent logic removal | Use `if not x: raise ValueError()` for runtime checks |
| P06 | **Global state mutation** | Module-level mutable (dict/list) modified at runtime → thread safety | Use thread-local, contextvars, or pass state explicitly |
| P07 | **Unhandled async exception** | `asyncio.create_task()` without storing reference → exception silently lost | Store task reference and await or add done callback |
| P08 | **Resource leak (no context manager)** | `f = open(...)` without `with` → file handle leak on exception | Always use `with open(...)` or `contextlib.closing()` |
| P09 | **Import side effects** | Module-level code that hits DB, network, or prints → breaks testing | Side effects only in `if __name__ == "__main__"` or explicit init functions |
| P10 | **Floating point comparison** | `if total == 0.3` → fails due to IEEE 754 representation | Use `math.isclose()` or `decimal.Decimal` for money |
| P11 | **Pickle deserialization** | `pickle.loads(user_input)` → arbitrary code execution | Never unpickle untrusted data; use JSON or validated schemas |
| P12 | **Missing __init__.py** | Package directory without `__init__.py` → import fails in some configurations | Every package directory needs `__init__.py` (can be empty) |
| P13 | **Secrets in source** | API keys, tokens, passwords hardcoded in `.py` files | Use environment variables, `.env` files (gitignored), or secret managers |
| P14 | **Unbounded memory (generator vs list)** | `[x for x in huge_file]` loads everything into memory | Use generators for large data: `(x for x in huge_file)` |
| P15 | **Missing retry on network calls** | HTTP/DB calls without retry → transient failures crash the app | Use `tenacity` or `urllib3.util.retry` for external calls |
