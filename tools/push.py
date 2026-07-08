# -*- coding: utf-8 -*-
"""Push data into a Worker collection so the glasses/phone can display it.

The thin "brain -> display" bridge: your local agent (Claude on your PC, a script,
whatever) computes something, this posts it to `POST /api/<collection>/bulk` on the
Worker. No UI, no framework — stdlib only. The launcher you already have renders and
navigates it on the glasses (use a `readOnly:true` app config for a display feed).

Credentials come from environment variables, or a git-ignored `push.env` at the repo
root (copy `push.env.example`). NEVER commit real values — `push.env` / `*.env` are
git-ignored.
  GLASS_API    = https://<worker>.workers.dev/api
  GLASS_TOKEN  = your app password (the Worker's API_SECRET)

Usage:
  python tools/push.py <collection> --file items.json
  python tools/push.py <collection> --items '[{"title":"Clip","url":"https://...","type":"video"}]'
  echo '[{"title":"..."}]' | python tools/push.py <collection>
  python tools/push.py <collection> --replace --file items.json   # replace the whole feed (drop stale rows)

Each item is a dict of your app's fields (+ optional id/seen/fav). Items with an existing
`id` are updated; without one, an id is generated. Example item for a video feed:
  {"id":"v1","title":"Launch demo","url":"https://youtu.be/...","note":"2 min"}
"""
import os, sys, json, urllib.request, urllib.error


def _load_creds_file():
    """Populate GLASS_API/GLASS_TOKEN from a git-ignored `push.env` (or `.env`) at the
    repo root if they aren't already in the environment. Keeps creds off GitHub."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ("push.env", ".env"):
        p = os.path.join(root, name)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in ("GLASS_API", "GLASS_TOKEN", "GLASS_LAUNCHER") and not os.environ.get(k):
                os.environ[k] = v


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: push.py <collection> [--file F | --items JSON]  (else reads stdin)")
        return 2
    _load_creds_file()
    coll = argv[0]
    data = None
    replace = False
    i = 1
    while i < len(argv):
        if argv[i] == "--file" and i + 1 < len(argv):
            data = open(argv[i + 1], encoding="utf-8").read(); i += 2
        elif argv[i] == "--items" and i + 1 < len(argv):
            data = argv[i + 1]; i += 2
        elif argv[i] == "--replace":
            replace = True; i += 1
        else:
            i += 1
    if data is None:
        data = sys.stdin.read()

    try:
        items = json.loads(data)
    except Exception as e:
        print("bad JSON:", e); return 2
    if isinstance(items, dict):
        items = items.get("items", [items])
    if not isinstance(items, list):
        print("expected a JSON array of items"); return 2

    api = os.environ.get("GLASS_API", "").rstrip("/")
    tok = os.environ.get("GLASS_TOKEN", "")
    if not api or not tok:
        print("Set GLASS_API (…/api) and GLASS_TOKEN (your app password) env vars first.")
        return 2

    body = json.dumps({"items": items}).encode("utf-8")
    endpoint = api + "/" + coll + "/bulk" + ("?replace=1" if replace else "")
    req = urllib.request.Request(
        endpoint, data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok,
                 "User-Agent": "meta-glass-webkit-push/1.0"})  # default python UA trips Cloudflare 1010
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            print(r.status, r.read().decode("utf-8"))
            return 0
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read().decode("utf-8")); return 1
    except Exception as e:
        print("push failed:", e); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
