// Generic CRUD API on Cloudflare Workers + D1 (serverless SQLite).
// Collections + items, common flags (seen/fav/deleted), timestamps. Bearer-secret auth.
//
// Routes (JSON in/out):
//   GET    /api/:collection            list items (?since=ISO, ?deleted=1, ?limit=N default 200 max 1000)
//   POST   /api/:collection            create one item (body = your fields; optional "id")
//   POST   /api/:collection/bulk       upsert many (body {items:[...]}); ?replace=1 replaces the whole feed
//   PATCH  /api/:collection/:id         update fields and/or flags (seen/fav/deleted)
//   DELETE /api/:collection/:id         soft-delete (sets deleted=1)
//   GET    /health                      no auth; returns {ok:true}
//
// Auth: header `Authorization: Bearer <API_SECRET>`  (set with: wrangler secret put API_SECRET)

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type,Authorization",
};
const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { "Content-Type": "application/json", ...CORS } });

const nowISO = () => new Date().toISOString();
const rowOut = (r) => ({ id: r.id, ...(JSON.parse(r.data || "{}")), seen: !!r.seen, fav: !!r.fav,
                         deleted: !!r.deleted, created: r.created, updated: r.updated });

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const url = new URL(request.url);
    const parts = url.pathname.replace(/^\/+|\/+$/g, "").split("/"); // ["api",":c",...]

    if (parts[0] === "health") return json({ ok: true });

    // Non-API paths -> serve the static frontend (launcher + app configs) from ./public
    if (parts[0] !== "api") {
      return env.ASSETS ? env.ASSETS.fetch(request) : json({ error: "not found" }, 404);
    }

    // --- auth ---
    const auth = request.headers.get("Authorization") || "";
    if (!env.API_SECRET || auth !== "Bearer " + env.API_SECRET)
      return json({ error: "unauthorized" }, 401);

    if (parts[0] !== "api" || !parts[1]) return json({ error: "not found" }, 404);
    const collection = parts[1];
    const sub = parts[2];           // undefined | "bulk" | ":id"
    let body = {};
    if (request.method === "POST" || request.method === "PATCH") {
      try { body = await request.json(); } catch { body = {}; }
    }

    try {
      // LIST
      if (request.method === "GET" && !sub) {
        const includeDeleted = url.searchParams.get("deleted") === "1";
        const since = url.searchParams.get("since");
        let q = "SELECT * FROM items WHERE collection=?";
        const args = [collection];
        if (!includeDeleted) q += " AND deleted=0";
        if (since) { q += " AND updated>?"; args.push(since); }
        q += " ORDER BY updated DESC";
        let lim = parseInt(url.searchParams.get("limit") || "200", 10);
        if (!(lim > 0)) lim = 200; if (lim > 1000) lim = 1000;   // protect the glasses' 128MB budget
        q += " LIMIT " + lim;
        const { results } = await env.DB.prepare(q).bind(...args).all();
        return json({ items: (results || []).map(rowOut) });
      }

      // BULK UPSERT (bulk import / feed a read-only list)
      if (request.method === "POST" && sub === "bulk") {
        const replace = url.searchParams.get("replace") === "1";  // replace the whole feed (drop stale rows)
        const items = Array.isArray(body.items) ? body.items : [];
        const t = nowISO();
        // Run DELETE (if replacing) + all upserts as one ordered, atomic batch — separate
        // awaited statements can lose rows on some D1 backends (e.g. local miniflare).
        const stmts = [];
        if (replace) stmts.push(env.DB.prepare("DELETE FROM items WHERE collection=?").bind(collection));
        for (const it of items) {
          const id = String(it.id || it.url || crypto.randomUUID());
          const { seen, fav, deleted, id: _i, ...data } = it;
          stmts.push(env.DB.prepare(
            `INSERT INTO items (id,collection,data,seen,fav,deleted,created,updated)
             VALUES (?,?,?,?,?,?,?,?)
             ON CONFLICT(id) DO UPDATE SET data=excluded.data, seen=excluded.seen,
               fav=excluded.fav, deleted=excluded.deleted, updated=excluded.updated`
          ).bind(id, collection, JSON.stringify(data), seen ? 1 : 0, fav ? 1 : 0,
                 deleted ? 1 : 0, t, t));
        }
        if (stmts.length) await env.DB.batch(stmts);
        return json({ ok: true, upserted: items.length, replaced: replace });
      }

      // CREATE
      if (request.method === "POST" && !sub) {
        const id = String(body.id || crypto.randomUUID());
        const { seen, fav, deleted, id: _i, ...data } = body;
        const t = nowISO();
        await env.DB.prepare(
          `INSERT INTO items (id,collection,data,seen,fav,deleted,created,updated) VALUES (?,?,?,?,?,?,?,?)`
        ).bind(id, collection, JSON.stringify(data), seen ? 1 : 0, fav ? 1 : 0, deleted ? 1 : 0, t, t).run();
        return json({ ok: true, id });
      }

      // UPDATE (fields and/or flags)
      if (request.method === "PATCH" && sub) {
        const row = await env.DB.prepare("SELECT * FROM items WHERE id=? AND collection=?").bind(sub, collection).first();
        if (!row) return json({ error: "not found" }, 404);
        const data = JSON.parse(row.data || "{}");
        const { seen, fav, deleted, ...fields } = body;
        Object.assign(data, fields);
        await env.DB.prepare(
          "UPDATE items SET data=?, seen=?, fav=?, deleted=?, updated=? WHERE id=? AND collection=?"
        ).bind(JSON.stringify(data),
               seen === undefined ? row.seen : (seen ? 1 : 0),
               fav === undefined ? row.fav : (fav ? 1 : 0),
               deleted === undefined ? row.deleted : (deleted ? 1 : 0),
               nowISO(), sub, collection).run();
        return json({ ok: true });
      }

      // SOFT DELETE
      if (request.method === "DELETE" && sub) {
        await env.DB.prepare("UPDATE items SET deleted=1, updated=? WHERE id=? AND collection=?")
          .bind(nowISO(), sub, collection).run();
        return json({ ok: true });
      }

      return json({ error: "method not allowed" }, 405);
    } catch (e) {
      return json({ error: String(e && e.message || e) }, 500);
    }
  },
};
