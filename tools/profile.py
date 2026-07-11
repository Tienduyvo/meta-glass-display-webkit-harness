# -*- coding: utf-8 -*-
"""Private user profile — the personalization store every app reads (owner 2026-07-11).

The profile lives in the Worker's D1 as the `profile` collection: behind the app
password, synced across devices, NEVER in git ("keep this config safe"). Rows are
scopes — `me` (background, who the user is) plus one row per app (`news`, `timer`, …).
It is filled by AI CONVERSATION, not forms: the setup wizard (and any chat) interviews
the user and Claude writes the rows with this tool. Apps and pipelines read their scope
and fall back to their committed, non-personal defaults when a scope is missing.

Usage (creds from push.env, same as push.py):
  python tools/profile.py get [scope]          # print one scope (or all) as JSON
  python tools/profile.py set <scope> '<json>' # upsert fields into a scope row
  python tools/profile.py delete <scope>       # remove a scope
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import push as _push  # creds loader + bulk endpoint conventions

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

COLL = "profile"


def _creds():
    _push._load_creds_file()
    api = os.environ.get("GLASS_API", "").rstrip("/")
    tok = os.environ.get("GLASS_TOKEN", "")
    if not api or not tok:
        raise SystemExit("Set GLASS_API/GLASS_TOKEN (env or push.env) first.")
    return api, tok


def _req(method, path, body=None):
    api, tok = _creds()
    req = urllib.request.Request(
        api + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok,
                 "User-Agent": "meta-glass-webkit-profile/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def get_scope(scope=None):
    items = _req("GET", "/" + COLL).get("items", [])
    if scope is None:
        return {it["id"]: it for it in items}
    return next((it for it in items if it.get("id") == scope), None)


def set_scope(scope, fields):
    row = get_scope(scope) or {"id": scope}
    row.update(fields)
    row.pop("seen", None); row.pop("fav", None)
    return _req("POST", "/%s/bulk" % COLL, {"items": [row]})


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__); return 0
    cmd = argv[0]
    if cmd == "get":
        print(json.dumps(get_scope(argv[1] if len(argv) > 1 else None),
                         ensure_ascii=False, indent=1))
        return 0
    if cmd == "set" and len(argv) >= 3:
        print(json.dumps(set_scope(argv[1], json.loads(argv[2]))))
        return 0
    if cmd == "delete" and len(argv) >= 2:
        print(json.dumps(_req("DELETE", "/%s/%s" % (COLL, argv[1]))))
        return 0
    print("usage: profile.py get [scope] | set <scope> '<json>' | delete <scope>")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
