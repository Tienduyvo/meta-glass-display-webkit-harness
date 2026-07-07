# Architecture

```
  Meta glasses (600x600, keyboard)  ─┐
                                     ├─►  Cloudflare Worker  ──►  D1 (SQLite)
  phone / desktop (responsive)      ─┘   serves the frontend       generic CRUD API
                                          (worker/public) AND       Bearer-password auth
                                          the /api CRUD endpoints
```

One Worker does both jobs: it serves the static launcher + app configs from `worker/public`, and
answers the `/api/*` CRUD calls on the same origin. No separate hosting, no GitHub Pages needed.

## Components

### Launcher + runner (one HTML file)
- **Two variants, same code shape.** `worker/public/index.html` is the **production** launcher the
  Worker serves (same-origin API — it just needs the password). `app/index.html` is the **local
  dev** launcher (you type the Worker URL). They are intentionally separate; don't copy one over
  the other.
- **One credential, set once.** The app **password** (the Worker's `API_SECRET`) is stored in
  `localStorage`; it can also ride in the launcher URL hash (`#glass&t=<password>`) so the glasses
  need exactly **one** URL registered in Developer Mode. The API URL is the site's own origin.
- **Registry-driven.** The launcher lists apps from `apps/registry.json` (`name, icon, config`).
  Add an entry → it shows up automatically.
- **Schema-driven runner.** Each app is an `app.config.json` (fields, row, detail, actions, sort).
  The same file renders the glasses 600×600 additive layout (keyboard nav) and the responsive
  phone/desktop layout.
- **Offline-tolerant.** Reads are cached in `localStorage`; mutations (create/patch/delete) are
  applied optimistically and queued, then flushed when back online.

### Backend (`worker/`, Cloudflare Worker + D1)
- Generic CRUD API: collections + items, flags `seen`/`fav`/soft-delete, timestamps.
- **D1 (serverless SQLite), not KV** — lists need querying/ordering/flags, which is relational.
- Item domain fields are stored as JSON in a `data` column ⇒ **no migration** when a schema
  changes. Bearer-password auth. `POST /api/:c/bulk` upserts many items at once (bulk import / a
  read-only list fed from an external source).
- Static assets (`worker/public`) are served for every non-`/api` path via the `[assets]` binding.

## Source → served tree
The apps you edit live in `apps/`. The Worker serves `worker/public/`. `tools/sync_public.py`
mirrors `apps/` → `worker/public/apps/` (rewriting config paths to same-origin `/apps/...`) and is
run automatically by `new_app.py` and the deploy runners. `tools/status.py` warns if the two drift.

## Design principles
- **SQLite (D1) as the source of truth** over racing on JSON files; write local files atomically
  (temp + `os.replace`).
- **No build step**: one HTML file + JSON configs. No bundler, no framework.
- **Secrets never in the repo or the hosted page** — the password is a Wrangler secret + browser
  `localStorage`, never committed.
