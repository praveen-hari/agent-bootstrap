# React Defect Catalog

Use during REVIEW stage. For each finding: name the rule, check if it's enforced in config, prefer the config-level fix.

| # | Defect | What goes wrong | Verify |
|---|--------|----------------|--------|
| R01 | **Stale closure** | Event handler or effect captures old state via closure | Check if handler references state that changes; use functional updater or ref |
| R02 | **Missing cleanup** | useEffect subscribes/timers without return cleanup | `useEffect` with addEventListener/setInterval must return cleanup |
| R03 | **Key as array index** | `key={index}` causes wrong DOM reuse on reorder/delete | Keys must be stable IDs, not array indices |
| R04 | **Unbounded re-render** | State set inside render or useEffect without deps causes infinite loop | Every setState must be inside an event handler or effect with correct deps |
| R05 | **Missing dependency** | useEffect/useCallback deps array omits a referenced value | Enable `react-hooks/exhaustive-deps` rule (config fix) |
| R06 | **Prop drilling > 3 levels** | Props passed through intermediary components that don't use them | Extract to context or composition pattern |
| R07 | **Direct DOM mutation** | `document.getElementById` / `innerHTML` instead of refs | Use `useRef` + `ref` prop |
| R08 | **Async state on unmount** | setState called after component unmounts | Use abort controller or cleanup flag in useEffect |
| R09 | **Object/array in deps** | `useEffect([{...}])` — new reference every render, infinite loop | Memoize with useMemo or extract stable values |
| R10 | **Missing error boundary** | Unhandled throw in render crashes the entire app | Wrap route-level components in ErrorBoundary |
| R11 | **Uncontrolled → controlled** | Input switches between controlled and uncontrolled | Initialize state to `""` not `undefined` for text inputs |
| R12 | **Missing Suspense boundary** | Lazy-loaded components throw without fallback | Wrap `React.lazy()` with `<Suspense fallback={...}>` |
| R13 | **XSS via dangerouslySetInnerHTML** | User input rendered as HTML without sanitization | Sanitize with DOMPurify before setting innerHTML |
| R14 | **Large bundle from barrel exports** | `import { x } from './components'` pulls entire directory | Import directly from the specific file |
| R15 | **Missing accessible name** | Interactive elements without aria-label or visible text | Every button/link/input needs an accessible name |
