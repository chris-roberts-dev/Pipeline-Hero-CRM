# MyPipelineHero React Frontend — Contract-First, Mock-Driven Scaffold

This scaffold lets you **develop the tenant-facing React frontend before the Django CRM API is finished**.

It is designed around the backend requirements you already defined:

- Django remains the source of truth for auth, tenancy, RBAC, sessions, and services.
- The **root-domain login** stays server-rendered.
- The React app assumes it runs on the **tenant subdomain** after Django completes the signed handoff.
- The tenant-facing API is **internal** and thin over the Django service layer.

## What changed from the earlier scaffold

This version is now **contract-first** and **mock-driven**:

- a local OpenAPI contract lives in `contracts/internal-api.openapi.yaml`
- frontend types are generated from that contract into `src/lib/api/generated/schema.d.ts`
- browser mocks are implemented with **MSW** in `src/mocks/**`
- mock data includes multiple roles, tenants, and scenarios
- the app can run against mocks first, then later be pointed at the real Django API
- optional **Prism** support is included so you can stand up a contract-driven mock server outside the browser too

## Why this fits MyPipelineHero

Your requirements explicitly separate the future React tenant portal from the Django-owned auth/login flow and require the React layer to consume a thin internal JSON API over the same service boundary. This scaffold follows that shape directly.

It also mirrors your org/tenant/RBAC model by treating the frontend bootstrap contract as:

- authenticated session state
- active organization
- current user
- capabilities
- impersonation state

## Folder highlights

```text
contracts/
  internal-api.openapi.yaml

src/
  features/
    auth/
    organizations/
    devtools/
    tenant/
  lib/
    api/
    config/
    dev/
    query/
  mocks/
    data/
    handlers/
    browser.ts
    index.ts
```

## Install

```bash
npm install
```

## First-time mock setup

MSW needs a service worker file in `public/`.
Generate it once after install:

```bash
npm run mocks:init
```

## Run with mocks

```bash
npm run dev:mock
```

Or set this in your environment:

```bash
VITE_ENABLE_API_MOCKS=true
```

## Generate types from the local contract

This is the main contract-first workflow while the backend is still being built:

```bash
npm run openapi:types
```

That command regenerates:

```text
src/lib/api/generated/schema.d.ts
```

## Later: switch to the real Django schema

Once Django exposes the internal schema endpoint, regenerate types from the backend instead:

```bash
OPENAPI_SCHEMA_URL=http://localhost:8000/api/internal/schema/ npm run openapi:types:remote
```

At that point you can keep the same React routes, queries, and page structure and replace mocks endpoint-by-endpoint.

## Optional: run a standalone contract mock server

If you want something that behaves more like a separate backend process instead of browser interception:

```bash
npm run mock:prism
```

That serves the local OpenAPI contract via Prism.

## Mock scenarios

Use any of these in `.env.local` or via `localStorage.setItem('mph:mock-scenario', 'owner')`:

- `owner`
- `viewer`
- `impersonating`
- `logged-out`
- `organizations-empty`
- `organizations-error`
- `messages-empty`
- `messages-error`
- `notifications-empty`
- `notifications-error`

The top bar includes a small mock scenario switcher whenever API mocks are enabled.

## Current mocked endpoints

- `GET /api/internal/session/`
- `GET /api/internal/messages/summary/`
- `GET /api/internal/notifications/summary/`
- `GET /api/internal/organizations/`
- `POST /api/internal/organizations/`

## Recommended workflow while Django is still incomplete

1. Evolve `contracts/internal-api.openapi.yaml`
2. Run `npm run openapi:types`
3. Update or add MSW handlers and fixtures
4. Build pages against the contract
5. Replace mocked endpoints with real Django endpoints later
6. Run `npm run openapi:types:remote` once the backend schema is live

## Suggested next slices

After this scaffold, the next best additions are:

1. organization detail contract + page
2. contacts list/detail contract
3. reusable form error contract
4. saved filters / pagination contract
5. role-aware nav and field-level UI gating helpers

## Important naming note

Your requirements document uses **Client** as the backend customer domain, while this starter keeps **Organizations** as the frontend-first label because that was your requested first screen. You can later map `organizations` to the `clients` backend resource or rename the feature folder once the internal API naming is finalized.
