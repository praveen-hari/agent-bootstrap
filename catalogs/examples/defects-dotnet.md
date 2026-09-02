# .NET / ASP.NET Core Defect Catalog

Use during REVIEW stage. For each finding: name the rule, check if it's enforced in config, prefer the config-level fix.

| # | Defect | What goes wrong | Verify |
|---|--------|----------------|--------|
| N01 | **Captive dependency** | Singleton holds a reference to a scoped service → stale data, memory leak | Enable `ValidateScopes` in development; scoped services never injected into singletons |
| N02 | **N+1 query** | Loop issues one query per item instead of batch | Check EF includes: `.Include()` or `.AsSplitQuery()` for collections |
| N03 | **Missing AsNoTracking** | Read-only queries track entities → memory pressure | Read-only endpoints use `.AsNoTracking()` or `.AsNoTrackingWithIdentityResolution()` |
| N04 | **Disposed DbContext** | DbContext used after scope ends (async fire-and-forget) | DbContext must not outlive its scope; use IDbContextFactory for background work |
| N05 | **Sync over async** | `.Result` or `.Wait()` on async call → thread starvation, deadlock | Async all the way; no `.Result`, `.Wait()`, or `.GetAwaiter().GetResult()` in request path |
| N06 | **Missing cancellation token** | Async endpoint ignores `CancellationToken` → wasted work on cancelled requests | Pass `CancellationToken` from controller to all async calls |
| N07 | **Unvalidated input at boundary** | Controller accepts model without validation → injection, invalid state | Use `[Required]`, `FluentValidation`, or `Zod`-style validation at API boundary |
| N08 | **Hardcoded connection string** | Connection string in source code instead of configuration/secrets | Use `IConfiguration`, user-secrets in dev, Key Vault in prod |
| N09 | **Missing anti-forgery** | POST/PUT/DELETE form endpoints without `[ValidateAntiForgeryToken]` | CSRF protection on all state-changing form endpoints |
| N10 | **Unbounded collection return** | API returns `IEnumerable<T>` without paging → OOM on large datasets | All collection endpoints must accept `skip`/`take` or cursor pagination |
| N11 | **Exception in constructor** | Exception in DI-registered constructor crashes startup silently | Constructors should not throw; use factory pattern for fallible initialization |
| N12 | **Missing HTTPS redirect** | App serves over HTTP without redirect → credentials in cleartext | `app.UseHttpsRedirection()` in pipeline |
| N13 | **Open redirect** | `Redirect(returnUrl)` without validation → phishing | Validate return URLs with `Url.IsLocalUrl()` |
| N14 | **Missing Dispose** | `HttpClient`, `DbContext`, streams not disposed → resource leak | Use `using`, `IAsyncDisposable`, or DI lifetime management |
| N15 | **Logging PII** | User email, IP, or tokens written to logs | Audit log statements for personal data; use structured logging with redaction |
