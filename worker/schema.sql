-- D1 (serverless SQLite) schema for the generic CRUD API.
-- One row per item; domain fields live in the JSON `data` column, common flags are columns.
CREATE TABLE IF NOT EXISTS items (
  id         TEXT PRIMARY KEY,
  collection TEXT NOT NULL,
  data       TEXT NOT NULL DEFAULT '{}',   -- JSON: your schema's fields
  seen       INTEGER NOT NULL DEFAULT 0,
  fav        INTEGER NOT NULL DEFAULT 0,
  deleted    INTEGER NOT NULL DEFAULT 0,   -- soft delete
  created    TEXT NOT NULL,
  updated    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_coll ON items(collection, deleted, updated);
