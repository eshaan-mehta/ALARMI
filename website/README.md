# ALARMI — Web

Frontend for ALARMI. React + TypeScript SPA that lets users manage **projects** and their **designs** (upload, view, edit).

Talks to the ALARMI backend REST API (see `../backend`).

## Stack

- **React 19** + **TypeScript**, bundled by **Vite** (React Compiler enabled)
- **Mantine** — UI components, forms, modals, notifications, dropzone
- **TanStack Query** — server state / data fetching
- **React Router** — routing
- **Axios** — HTTP client

## Getting started

```bash
npm install
npm run dev          # http://localhost:5173
```

Start the backend first (`cd ../backend && uv run dev`). The dev server reads
`VITE_API_BASE_URL` from `.env.local` (already set to `http://localhost:8000/api`).

| Var | Default | Purpose |
|-----|---------|---------|
| `VITE_API_BASE_URL` | `/api` | Backend REST base URL (set to `http://localhost:8000/api` for local dev) |

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
  lib/              # env + formatting helpers
  index.css
public/             # static assets + MSW worker
```

### Routes

| Path | View |
|------|------|
| `/` | Landing |
| `/projects` | Projects dashboard |
| `/projects/:projectId` | Project detail (its designs) |
| `*` | Not found |

## Data layer

Each domain (`projects`, `designs`) has the same shape: `api.ts` (raw calls), `hooks.ts` (TanStack Query wrappers), `types.ts`. Components use hooks only. Requests go to the backend REST API at `VITE_API_BASE_URL`.
