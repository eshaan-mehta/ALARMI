# ALARMI — Web

Frontend for ALARMI. React + TypeScript SPA that lets users manage **projects** and their **designs** (upload, view, edit).

Talks to the ALARMI backend REST API. In dev it defaults to an in-browser mock (MSW), so you can run it with no backend.

## Stack

- **React 19** + **TypeScript**, bundled by **Vite** (React Compiler enabled)
- **Mantine** — UI components, forms, modals, notifications, dropzone
- **TanStack Query** — server state / data fetching
- **React Router** — routing
- **Axios** — HTTP client
- **MSW** — mock backend for local dev

## Getting started

```bash
npm install
npm run dev          # http://localhost:5173, uses MSW mock backend
```

No `.env` needed for the mock. To point at a real backend:

```bash
cp .env.example .env
# set VITE_API_BASE_URL and VITE_USE_MOCKS=false
```

| Var | Default | Purpose |
|-----|---------|---------|
| `VITE_API_BASE_URL` | `/api` | Backend REST base URL |
| `VITE_USE_MOCKS` | `true` (dev only) | Start MSW mock backend; set `false` to hit a real API |

## Scripts

```bash
npm run dev       # dev server + HMR
npm run build     # typecheck (tsc -b) + production build → dist/
npm run preview   # serve the built dist/
npm run lint      # eslint
```

## Structure

```
src/
  main.tsx          # entry; boots MSW mock then renders app
  app/              # app shell: router, layout, providers, error boundary
  pages/            # route views: Landing, ProjectsDashboard, ProjectDetail, NotFound
  components/       # UI: cards, modals, nav, badges
  data/             # server state
    http.ts         #   axios instance
    queryKeys.ts    #   TanStack Query keys
    projects/       #   api + hooks + types
    designs/        #   api + hooks + types
    mocks/          #   MSW handlers + in-memory db (dev backend)
  lib/              # env + formatting helpers
  index.css
public/             # static assets + MSW worker
```

### Routes

| Path | View |
|------|------|
| `/` | Landing |
| `/projects` | Projects dashboard |
| `/projects/:projectName` | Project detail (its designs) |
| `*` | Not found |

## Data layer

Each domain (`projects`, `designs`) has the same shape: `api.ts` (raw calls), `hooks.ts` (TanStack Query wrappers), `types.ts`. Components use hooks only. In dev, requests are intercepted by MSW handlers in `data/mocks/` backed by an in-memory db — swap the mock for the real API via env vars.
