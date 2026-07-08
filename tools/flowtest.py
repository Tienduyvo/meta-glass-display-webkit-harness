# -*- coding: utf-8 -*-
"""Run an app's user-flow as automated assertions against a running Worker — the
"cheap reward" for the build loop. The flow is derived generically from the app's
`app.config.json` (no per-app test script): create -> item appears in list ->
fields round-trip -> check/fav persist -> delete removes it, plus config checks.

Runs in an isolated `<collection>_flowtest` partition, so real data is never touched
(it bulk-empties that partition before and after). Point it at a local `wrangler dev`
(ephemeral D1) so it's free and pollutes nothing:
    GLASS_API=http://localhost:8787/api  GLASS_TOKEN=localtest   (matches worker/.dev.vars)
Creds also load from a git-ignored push.env. The human-readable spec lives in
`apps/<slug>/acceptance.md`.

Usage:
    python tools/flowtest.py wallpaper
    python tools/flowtest.py                # every registered app
Exit 0 = all flow assertions passed, 1 = a failure (the loop's fail signal).
"""
import os, re, sys, json, urllib.request, urllib.error

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(ROOT, "apps")
UA = "meta-glass-webkit-flowtest/1.0"


def _creds():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push
        push._load_creds_file()
    except Exception:
        pass
    return os.environ.get("GLASS_API", "").rstrip("/"), os.environ.get("GLASS_TOKEN", "")


def api(method, base, tok, path, body=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Authorization": "Bearer " + tok, "User-Agent": UA}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        txt = r.read().decode("utf-8")
        return r.status, (json.loads(txt) if txt else {})


def synth(f):
    t = f.get("type", "text")
    if t == "number":
        d = f.get("default")
        return d if isinstance(d, (int, float)) else 1
    if t == "countdown":
        return 1893456000000
    if t == "geo":
        return "1.00000,2.00000"
    if t in ("link", "video", "image"):
        return "https://example.com/x"
    return "flowtest-" + f["key"]


def registered_slugs():
    try:
        reg = json.load(open(os.path.join(APPS, "registry.json"), encoding="utf-8"))
    except Exception:
        return []
    out = []
    for a in reg.get("apps", []):
        m = re.search(r"apps/([^/]+)/", a.get("config", ""))
        if m:
            out.append(m.group(1))
    return out


def run_app(slug, base, tok):
    cfg = json.load(open(os.path.join(APPS, slug, "app.config.json"), encoding="utf-8"))
    coll = cfg["collection"] + "_flowtest"
    A = cfg.get("actions", {})
    fields = cfg.get("fields", [])
    keys = [f["key"] for f in fields]
    R = []
    def check(ok, msg): R.append((bool(ok), msg))

    # config conformance
    check(cfg.get("row", {}).get("title") in keys, "row.title is a real field")
    check(all(k in keys for k in cfg.get("detail", [])), "detail keys are real fields")
    check("api" not in cfg, "no global 'api' field in config")

    api("POST", base, tok, "/" + coll + "/bulk?replace=1", {"items": []})  # clean

    item = {"id": "ft1"}
    for f in fields:
        item[f["key"]] = synth(f)

    if not cfg.get("readOnly") and A.get("add"):
        st, res = api("POST", base, tok, "/" + coll, item)
        check(st == 200 and res.get("ok"), "create item via POST")
    else:
        st, res = api("POST", base, tok, "/" + coll + "/bulk", {"items": [item]})
        check(st == 200 and res.get("ok"), "feed item via bulk (readOnly)")

    st, res = api("GET", base, tok, "/" + coll)
    got = next((i for i in res.get("items", []) if i.get("id") == "ft1"), None)
    check(got is not None, "item appears in the list")
    if got:
        for f in fields:
            check(str(got.get(f["key"])) == str(item[f["key"]]), "field round-trips: " + f["key"])

    if A.get("check"):
        api("PATCH", base, tok, "/" + coll + "/ft1", {"seen": True})
        _, res = api("GET", base, tok, "/" + coll)
        g = next((i for i in res.get("items", []) if i.get("id") == "ft1"), {})
        check(g.get("seen") is True, "check-off persists (seen=true)")
    if A.get("fav"):
        api("PATCH", base, tok, "/" + coll + "/ft1", {"fav": True})
        _, res = api("GET", base, tok, "/" + coll)
        g = next((i for i in res.get("items", []) if i.get("id") == "ft1"), {})
        check(g.get("fav") is True, "favorite persists (fav=true)")
    if A.get("delete"):
        api("DELETE", base, tok, "/" + coll + "/ft1")
        _, res = api("GET", base, tok, "/" + coll)
        check(not any(i.get("id") == "ft1" for i in res.get("items", [])), "delete removes item from list")

    # bulk replace with items must actually persist (regression: some D1 backends drop them)
    api("POST", base, tok, "/" + coll + "/bulk?replace=1", {"items": [dict(item, id="ftbulk")]})
    _, res = api("GET", base, tok, "/" + coll)
    check([i.get("id") for i in res.get("items", [])] == ["ftbulk"], "bulk replace persists the pushed items")

    api("POST", base, tok, "/" + coll + "/bulk?replace=1", {"items": []})  # cleanup
    return R


def main(argv):
    base, tok = _creds()
    if not base or not tok:
        print("Set GLASS_API + GLASS_TOKEN (env or push.env). Tip: run `wrangler dev` then use")
        print("  GLASS_API=http://localhost:8787/api  GLASS_TOKEN=localtest")
        return 2
    slugs = argv or registered_slugs()
    fails = 0
    print("\nflowtest — user-flow assertions")
    print("-------------------------------")
    for slug in slugs:
        try:
            res = run_app(slug, base, tok)
        except urllib.error.HTTPError as e:
            print("[%s] HTTP %d — is the Worker running/authorized?" % (slug, e.code)); fails += 1; continue
        except Exception as e:
            print("[%s] error: %s" % (slug, e)); fails += 1; continue
        bad = [m for ok, m in res if not ok]
        for ok, m in res:
            print(("  [x] " if ok else "  [!] ") + m)
        print("[%s] %s\n" % (slug, "PASS" if not bad else "FAIL (%d)" % len(bad)))
        fails += len(bad)
    print("All flow assertions passed." if not fails else "FAILED: %d assertion(s)." % fails)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
