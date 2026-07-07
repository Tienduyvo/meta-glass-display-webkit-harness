# Backend — Cloudflare Worker + D1 (generic CRUD API)

A tiny serverless CRUD API for list apps. **Why D1 (not KV):** lists need querying, ordering
and per‑item flags (seen/fav/soft‑delete) — that's relational, so **D1 (serverless SQLite)**
fits far better than KV's plain key→blob store. The same Worker also serves the frontend
(`worker/public`) on the same origin.

## What you need (one‑time)
1. A free **Cloudflare account**.
2. Node.js installed (for `npx wrangler`).

## Deploy (or just double‑click `runners/deploy_worker.bat`)
```bash
cd worker
npx wrangler login                     # opens browser, authorizes
npx wrangler d1 create glass_crud      # -> copy the database_id it prints
#   paste that id into wrangler.toml -> d1_databases.database_id
npx wrangler d1 execute glass_crud --remote --file=schema.sql
npx wrangler secret put API_SECRET     # set your APP PASSWORD; you type it once in the launcher
npx wrangler deploy                    # -> prints https://glass-crud-api.<you>.workers.dev
```
Health check: `GET https://…workers.dev/health` → `{"ok":true}`.

## API
Auth on every request: `Authorization: Bearer <API_SECRET>`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/:collection` | list items (`?since=ISO`, `?deleted=1` to include soft‑deleted) |
| POST | `/api/:collection` | create one item (body = your fields; optional `id`) |
| POST | `/api/:collection/bulk` | upsert many (`{items:[...]}`) — bulk import / feed a read-only list |
| PATCH | `/api/:collection/:id` | update fields and/or flags `{seen,fav,deleted, …}` |
| DELETE | `/api/:collection/:id` | soft‑delete |

Items are `{id, …your fields…, seen, fav, deleted, created, updated}`. Domain fields are stored
in a JSON `data` column, so **no schema migration** is needed when your app's fields change.

## Security
- The `API_SECRET` is a Wrangler **secret** — never in `wrangler.toml`, never committed.
- The frontend stores the password in the browser's `localStorage` (entered once by you), so it is
  **not** baked into the served page.
