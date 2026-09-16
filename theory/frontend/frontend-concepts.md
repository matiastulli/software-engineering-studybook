# Frontend & Web Vocabulary

Terms that get used in full-stack interviews without ever being defined. Each gets the short version here and links to its full explanation. Examples reference a **reference API** (Express/TypeScript) and a **reference dashboard** (Vite + React), plus a production-shaped Next.js/React/Expo/FastAPI app. All three live outside this repo.

## TL;DR

- **A React hook and a webhook share a word, nothing else.** A hook plugs into a component's render cycle; a webhook is an HTTP call between servers.
- **"Middleware" is always code in between**, but in between *what* depends on the framework: Express (request → handler), Next.js Proxy/Middleware (request → page), Redux (action → reducer).
- **CSR, SSR and SSG differ in where and when the HTML is built:** browser at runtime, server per request, or build time.
- **Props flow down, state lives where it's owned.** It's a DAG: data moves parent → child, and changes travel back up through callbacks.
- **A bundler turns many TS modules into a few files a browser loads.** Vite in dev serves native ES modules; the build bundles for production.

---

## 1. Hook vs webhook

The naming collision confuses a lot of people. Say the distinction explicitly.

| | **Hook** (React) | **Webhook** (HTTP) |
|---|---|---|
| What it is | A function that lets a component use React features (state, effects) | A URL a server calls to push an event to another system |
| Where it runs | In the browser, inside a component | Between two servers |
| Example | `useState`, `useEffect` | a per-workflow trigger URL; the dashboard's `notifyPlatform()` |
| Failure you care about | Stale closure, missing effect cleanup | Lost delivery, duplicates, forged requests |
| Full reference | [react.md §4](react.md#4-hooks) (the hooks table lives there) | [rest-apis-webhooks.md §3](../backend/rest-apis-webhooks.md#3-webhooks) |

Both use "hook" in the sense of "a place to attach your code to something that happens automatically". That's the only overlap.

---

## 2. Middleware in three frameworks

| Context | Runs in between | Example |
|---|---|---|
| **Express** (Node backend) | Incoming request → your route handler | The reference API's `requireApiKey`, `requestLogger`. See [nodejs-express.md §1](../backend/nodejs-express.md#1-middleware-the-core-mental-model) |
| **Next.js Proxy** (formerly Middleware) | Incoming request → a page or route handler, before your app code | Redirect unauthenticated users, rewrite a URL |
| **Redux middleware** | Dispatched action → reducer | Logging every action, async thunks |

Next.js 16 renamed `middleware.ts` to `proxy.ts`. Proxy runs on the Node.js runtime, and `middleware.ts` remains only for Edge-runtime use and is deprecated ([Next.js docs](https://nextjs.org/docs/messages/middleware-to-proxy), checked Sept 2026). If an interviewer says "middleware" with no context, ask which layer they mean. The shape transfers; the specifics don't.

---

## 3. Component, props, state

- **Component:** a function that returns UI. `ShipmentCard` in the `dashboard` is one.
- **Props:** data passed *into* a component by its parent, read-only inside it. In `<ShipmentCard shipment={shipment} />`, `shipment` is a prop.
- **State:** data a component owns and changes, which triggers a re-render (`useState`).

**Bridge:** the component tree is a DAG. Props are edges, always parent → child; state is a source table owned by one node. When two siblings need the same data, move the source up to their common parent ("lifting state up") instead of syncing two copies. Changing data lives as state in exactly one place; everything else receives props. Full depth in [react.md §1](react.md#1-components-jsx-props-keys) and [§3](react.md#3-state).

---

## 4. Rendering models: CSR, SSR, SSG

This is the real technical difference between "plain React" and Next.js.

| Model | Where and when HTML is built | Example |
|---|---|---|
| **CSR** (Client-Side Rendering) | In the browser: a near-empty HTML page plus a JS bundle, and React builds the UI after load | The reference dashboard (Vite + React) |
| **SSR** (Server-Side Rendering) | On the server, per request; the browser then **hydrates** it (attaches event handlers) | Next.js pages that need fresh data per request |
| **SSG** (Static Site Generation) | Once at build time, served as static files | SEO-facing listing pages built once and served static |

SSR needs a running server, and Next.js's server side *is* Node.js code. That's the "Node" in "Next.js is a Node framework". CSR and SSG output are just static files a CDN can serve.

**Decide:**
- **CSR** for an app behind a login where SEO doesn't matter and the data is per user, like a dispatcher dashboard.
- **SSR** when pages must be indexable *and* fresh per request, like a public load listing with live prices.
- **SSG** when pages must be indexable and change rarely, like carrier landing pages. Rebuild or revalidate on a schedule.

**Failure mode:** a **hydration mismatch**, where server HTML differs from the first client render (`Date.now()`, `Math.random()`, `window` checks during render). React warns and the UI can flicker or break. Keep render deterministic; read browser-only values in an effect.

---

## 5. Virtual DOM

React renders to an in-memory element tree, diffs it against the previous one, and applies only the differences to the real DOM. That's why `setState` "just works" without you finding the right element. Keys are the lever you control. Full mechanism in [react.md §2](react.md#2-rendering-virtual-dom-and-reconciliation).

---

## 6. Bundler

A bundler (Vite, webpack, Turbopack) resolves the `import` graph across your `.tsx`/`.ts` files, compiles TypeScript and JSX to JavaScript, and outputs a few optimized, cache-busted files. In the `dashboard`, `npm run dev` runs Vite's dev server (mostly unbundled, native ES modules, fast reloads) and `npm run build` produces the bundled production output.

**Bridge:** like Spark's planner, it resolves dependencies and prunes what's unused ("tree shaking", like column pruning). **Code splitting** means emitting separate chunks loaded on demand.

---

## 7. API route / Route Handler

Next.js lets you write server endpoints inside the same project as the React pages. A file like `app/api/localities/route.ts` runs on the server, not in the browser, even though it sits next to your components. The reference app uses this pattern: real server-side Node code, not a separate hand-built Express service.

**Decide:** use **route handlers** when the API only serves this Next.js front end. Use a **separate service** (Express, FastAPI) when other clients call it too, like a mobile app, voice agents or partners, or when it needs its own scaling and deploys. A separate FastAPI backend is the second case.

---

## Common wrong answers

- **"Webhooks are React hooks for the backend."** They're unrelated: one is a function call inside a render, the other an HTTP request between servers.
- **"Next.js is a backend framework, React is frontend."** Next.js is a React framework that adds server rendering and server endpoints. The UI is still React.
- **"SSR is always faster."** It usually gives faster first paint, but adds server cost and time-to-first-byte, and hydration still has to run the JS.
- **"Middleware in Next.js runs at the edge."** It historically defaulted to Edge. Next.js 16's Proxy runs on Node.js.

---

## Self-check

<details><summary><b>Q1.</b> An interviewer asks "how would you use a hook to notify the carrier's system?" What do you clarify, and what are the two possible answers?</summary>

Clarify React hook vs webhook. A React hook runs in a browser tab and can't reliably notify another system. The answer is a **webhook** from the backend: signed, retried with backoff, deduped by the receiver on event id. A React hook could only display the status.

</details>

<details><summary><b>Q2.</b> Your team's dispatcher dashboard is behind a login and shows per-user data. A PM asks for SSR "for performance". What do you answer?</summary>

Behind a login SEO is irrelevant and data is per user, so CSR is the default: static hosting, no server. SSR might improve first paint but adds a server, hydration and caching complexity. Measure LCP/INP at p75 first; if first load is the problem, try code splitting and a faster API before SSR.

</details>

<details><summary><b>Q3.</b> Two sibling components, a load list and a detail panel, both need the selected load. Where does that state live, and why?</summary>

In their nearest common parent, passed down as props, with a callback like `onSelect` passed to the list. One source of truth flowing down the tree, like moving a shared CTE upstream into one model both consumers read. Context or a global store only earns its place if many distant components need it.

</details>

<details><summary><b>Q4.</b> What does "middleware" mean in Express vs Next.js vs Redux, and what's the shared idea?</summary>

Express middleware runs between an HTTP request and the route handler (auth, logging, parsing). Next.js Proxy (formerly Middleware) runs before a request reaches a page or route handler (redirects, rewrites). Redux middleware runs between a dispatched action and the reducer (logging, async). The shared idea is an ordered chain that can inspect, transform or stop what passes through.

</details>

<details><summary><b>Q5.</b> After deploying an SSR page, users see a warning and a flicker, and a timestamp changes right after load. What happened?</summary>

A hydration mismatch. The server rendered one timestamp, the browser's first render computed another (`new Date()` during render), and React had to patch the difference. Render a stable value from the server (pass it as a prop), or compute browser-only values in an effect after hydration.

</details>

---

## Related

- [react.md](react.md): components, state, the canonical hooks table, effects and memoization
- [rest-apis-webhooks.md](../backend/rest-apis-webhooks.md): webhooks, idempotency, CORS
- [nodejs-express.md](../backend/nodejs-express.md): Express middleware in depth
- [performance-and-security.md](../backend/performance-and-security.md): Core Web Vitals, XSS, CSRF
