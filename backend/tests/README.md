# Backend test suite

These tests are written against **the spec and the product behaviour we want**,
not against the current implementation. A failure here means the code disagrees
with the contract — not that the test needs adjusting.

```bash
uv run pytest                     # everything
uv run pytest tests/unit          # functions in isolation
uv run pytest tests/api           # one endpoint at a time, through the real ASGI app
uv run pytest tests/e2e           # whole journeys, incl. a real uvicorn process
uv run pytest tests/spec -rxX     # the spec surface Phase 1 hasn't built yet
uv run pytest -m "not live"       # skip the tests that spawn a server
uv run pytest -m policy           # only the product decisions listed below
```

## Where the contract comes from

| Source | What it fixes |
|---|---|
| Detailed Design Document, Table 1 (FS1–FS5) | upload + confirmation, status display, view/rename/delete, conversion & storage, metadata extraction |
| Table 2 (NFS2, NFS3, NFS8, NFS12) | plain-browser access (CORS), cloud persistence, 2-minute processing budget, 1 GB uploads |
| Table 4 | the endpoint set, including the mobile-facing routes not yet built |
| Tables 5 & 6 | which metadata exists and the Project/Module schema + keys |
| §3.2.2 | 2xx / 4xx / 5xx status-code discipline |
| `website/src/data/**` | the exact request and response shapes the web client sends and consumes |
| `website/src/lib/units.ts` | the five unit scales the client can convert and label |
| `website/src/components/*Modal.tsx` | error rendering (`err.response.data.message`) and the payloads each editor submits |

Where the design doc and the web app disagree, the web app wins for the
endpoints it owns — that divergence was a deliberate decision (ids instead of
names, `designs` instead of `files`, `PROCESSING/COMPLETE/ERROR` instead of
`NONE/IN_PROGRESS/COMPLETE`). The doc's own routes are still tracked, in
`tests/spec/`.

## Layout

```
tests/
  conftest.py       shared fixtures + the contract constants (statuses, units, field sets)
  unit/             util · config/db/errors · ifc processor · the three repositories · seed · CLI
  api/              per-endpoint behaviour and the cross-cutting error/CORS contract
  e2e/              full user journeys, persistence across a restart, and a live uvicorn server
  spec/             xfail: spec behaviour deferred to a later slice (never a regression)
```

Every test runs against a throwaway SQLite file in a temp dir — `conftest.py`
sets `DATABASE_URL` before the app is imported, so the developer's
`backend/alarmi.db` is never touched.

## Markers

- `policy` — asserts a product decision the design doc leaves open. Listed
  explicitly below so they can be argued with rather than absorbed silently.
- `deferred` — spec behaviour scheduled for a later slice; all `xfail`.
- `live` — spawns a real uvicorn process (slower than the in-process client).

## Product decisions encoded here

The doc doesn't rule on these; the suite takes a position:

1. **Project names are unique case-insensitively and ignoring padding.**
   "Clinic" and "clinic" side by side in the dashboard is a bug. Names are also
   the doc's own project handle (Table 4 keys projects by `project_name`).
2. **Zero-byte uploads are rejected.** A file with no content can never yield a
   module; failing at the door beats a design that sits there with no metadata.
3. **Module dimensions must be positive and complete (x, y, z).** They're
   physical extents — the app renders them at 1:1 and the robot marks that
   footprint.
4. **`unitScale` must be one of the five the client can convert.** Anything else
   silently breaks the dimension display and the unit-conversion editor.
5. **Whitespace-only metadata clears the field rather than being stored.**
6. **A nested list under a missing parent is a 404, not an empty list.** The
   dashboard can't otherwise distinguish "no designs yet" from "this project is
   gone".
7. **Foreign keys are enforced by the database, not only by the repository.**
   SQLite ignores them unless the pragma is on, so local dev and Azure SQL would
   otherwise disagree on what data is valid.
8. **Every error response carries `{"message": ...}`** — including the ones
   FastAPI generates itself (422 validation, 404 routing, 405 method, 500). All
   five client modals read `err.response.data.message` and show a blank error
   without it.
