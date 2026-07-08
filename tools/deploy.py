# -*- coding: utf-8 -*-
"""Stateful, walk-away deploy for the Cloudflare Worker + D1 backend.

Design goal: **you should be able to start it, go make tea, and come back to a live app.**
So it (1) PREFLIGHTS everything read-only first, (2) FRONT-LOADS the only two steps that
need a human — Cloudflare login and setting the app password — at the very start, then
(3) runs the whole rest UNATTENDED: link D1, apply schema, sync, deploy, health-check.

Nothing is asked "in between": already-done steps are detected and skipped, an existing D1
is reused (never re-created), and its database_id is written into wrangler.toml automatically
(no hand-paste). Safe to re-run any time — a fully set-up project runs end-to-end with zero
prompts.

Run via `runners/deploy_worker.bat` or `python tools/deploy.py`. Node.js/npx required.
"""
import os, re, sys, json, shutil, subprocess, urllib.request, urllib.error

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKER = os.path.join(ROOT, "worker")
TOML = os.path.join(WORKER, "wrangler.toml")
DB_NAME = "glass_crud"
NPX = shutil.which("npx")


def say(mark, msg): print("  [%s] %s" % (mark, msg))
def head(msg): print("\n" + msg + "\n" + "-" * len(msg))


def wr(args, capture=False):
    """Run `npx wrangler <args>` in the worker dir. capture=True returns
    (returncode, combined output); capture=False inherits the terminal (for the
    interactive steps: login / secret put)."""
    cmd = [NPX, "wrangler"] + args
    if capture:
        p = subprocess.run(cmd, cwd=WORKER, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    return subprocess.run(cmd, cwd=WORKER).returncode, ""


# ---- read-only probes (used by preflight) -----------------------------------
def probe_login():
    rc, out = wr(["whoami"], capture=True)
    m = re.search(r"associated with the email\s+([\w.+-]+@[\w-]+(?:\.[\w-]+)+)", out)
    ok = rc == 0 and ("You are logged in" in out or bool(m))
    return ok, (m.group(1) if m else "")

def read_toml():
    with open(TOML, encoding="utf-8") as f: return f.read()

def current_db_id():
    m = re.search(r'(?m)^\s*database_id\s*=\s*"([^"]*)"', read_toml())
    return m.group(1) if m else ""

def d1_list():
    rc, out = wr(["d1", "list", "--json"], capture=True)
    if rc != 0: return None
    try:
        return json.loads(out[out.index("["):out.rindex("]") + 1])   # tolerate banners
    except Exception:
        return None

def d1_info(dbs):
    row = next((d for d in (dbs or []) if d.get("name") == DB_NAME), None)
    return row

def probe_secret():
    rc, out = wr(["secret", "list"], capture=True)
    if rc != 0: return False               # worker not deployed yet / no secrets
    try:
        return any(x.get("name") == "API_SECRET" for x in json.loads(out[out.index("["):out.rindex("]") + 1]))
    except Exception:
        return "API_SECRET" in out

def probe_configs():
    p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check.py")],
                       cwd=ROOT, capture_output=True, text=True)
    return p.returncode == 0


# ---- preflight: inventory everything BEFORE doing anything -------------------
def preflight():
    head("Preflight — checking every step before the run")
    logged_in, email = probe_login()
    dbs = d1_list()
    row = d1_info(dbs)
    cur = current_db_id()
    linked = bool(cur) and "REPLACE" not in cur and (dbs is None or any(d.get("uuid") == cur for d in dbs))
    has_tables = bool(row and (row.get("num_tables") or 0) > 0)
    secret = probe_secret()
    configs = probe_configs()

    say("x" if NPX else "!", "Node.js / npx installed" if NPX else "Node.js / npx MISSING")
    say("x" if logged_in else "!", ("Logged in" + (" as " + email if email else "")) if logged_in
        else "Not logged in  -> one-time: Cloudflare login (browser)")
    if linked:
        say("x", "D1 '%s' linked in wrangler.toml (%s)" % (DB_NAME, cur[:8]))
    elif row:
        say("~", "D1 '%s' exists but not linked  -> will link automatically (no re-create)" % DB_NAME)
    else:
        say("~", "D1 '%s' not created yet  -> will create + link automatically" % DB_NAME)
    say("x" if has_tables else "~", "Schema applied" if has_tables
        else "Schema not applied yet  -> will apply automatically")
    say("x" if secret else "!", "App password (API_SECRET) set" if secret
        else "App password not set  -> one-time: you'll type it at the start")
    say("x" if configs else "!", "App configs valid" if configs else "App configs FAILED check.py")

    # blockers that make an unattended run impossible / pointless
    hard = []
    if not NPX: hard.append("Install Node.js (https://nodejs.org), then re-run.")
    needs_human = (not logged_in) or (not secret)   # the only interactive steps
    return {"logged_in": logged_in, "secret": secret, "linked": linked, "row": row,
            "has_tables": has_tables, "configs": configs, "hard": hard, "needs_human": needs_human}


# ---- mutating steps ---------------------------------------------------------
def write_toml_db_id(uuid):
    new = re.sub(r'(?m)^(\s*database_id\s*=\s*).*$', r'\1"%s"' % uuid, read_toml())
    tmp = TOML + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f: f.write(new)
    os.replace(tmp, TOML)

def ensure_login(pf):
    if pf["logged_in"]:
        return True
    say(" ", "Opening Cloudflare login in your browser…")
    rc, _ = wr(["login"])
    if rc != 0: say("!", "Login failed — re-run once you've authorized wrangler."); return False
    say("x", "Logged in"); return True

def ensure_secret(pf):
    if pf["secret"]:
        return True
    say(" ", "Set your APP PASSWORD now — a strong one you'll remember (input is hidden):")
    rc, _ = wr(["secret", "put", "API_SECRET"])
    if rc != 0: say("!", "Setting the password failed."); return False
    say("x", "App password set"); return True

def ensure_d1(pf):
    if pf["linked"]:
        say("x", "D1 already linked — skipping"); return True
    dbs = d1_list()
    row = d1_info(dbs)
    if not row:
        say(" ", "Creating D1 database '%s'…" % DB_NAME)
        wr(["d1", "create", DB_NAME])
        row = d1_info(d1_list())
    else:
        say(" ", "Reusing existing D1 '%s' (no re-create)…" % DB_NAME)
    if not row:
        say("!", "Could not create/find D1 '%s'." % DB_NAME); return False
    write_toml_db_id(row["uuid"])
    say("x", "Linked D1 in wrangler.toml (%s)" % row["uuid"][:8]); return True

def ensure_schema(pf):
    # re-probe: num_tables may be stale if we just linked/created
    if d1_info(d1_list()) and (d1_info(d1_list()).get("num_tables") or 0) > 0:
        say("x", "Schema already applied — skipping"); return True
    say(" ", "Applying schema.sql to the remote D1…")
    rc, _ = wr(["d1", "execute", DB_NAME, "--remote", "--file=schema.sql", "-y"])
    if rc != 0:
        rc, _ = wr(["d1", "execute", DB_NAME, "--remote", "--file=schema.sql"])
    say("x" if rc == 0 else "!", "Schema applied" if rc == 0 else "Schema step failed"); return rc == 0

def sync_public():
    say(" ", "Syncing apps/ -> worker/public…")
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync_public.py")], cwd=ROOT)

def deploy():
    say(" ", "Deploying the Worker…")
    rc, out = wr(["deploy"], capture=True)
    print(out.rstrip())
    m = re.search(r"https://[a-z0-9-]+\.[a-z0-9-]+\.workers\.dev", out) or \
        re.search(r"https://[a-z0-9-]+\.workers\.dev", out)
    return rc == 0, (m.group(0) if m else "")

def health(url):
    if not url: return False
    try:
        # A custom UA is required — Cloudflare's bot filter 403s the default python urllib UA.
        req = urllib.request.Request(url.rstrip("/") + "/health",
                                     headers={"User-Agent": "meta-glass-webkit-deploy/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            ok = r.status == 200 and b'"ok":true' in r.read()
            say("x" if ok else "!", "Health check %s (%s/health)" % ("passed" if ok else "unexpected", url))
            return ok
    except Exception as e:
        say("!", "Health check could not reach %s/health (%s)" % (url, e)); return False


def main():
    print("=" * 54); print("  Deploy the CRUD Worker to Cloudflare (D1) — walk-away"); print("=" * 54)
    if not NPX:
        print("\nNode.js / npx not found. Install Node.js first: https://nodejs.org"); return 1

    pf = preflight()
    if pf["hard"]:
        print("\nCan't proceed:"); [print("  - " + h) for h in pf["hard"]]; return 1

    if pf["needs_human"]:
        head("One-time setup (do these now, then you can step away)")
        if not ensure_login(pf): return 1
        if not ensure_secret(pf): return 1
        print("\n➡  Interactive part done — you can go get tea now; the rest runs unattended.\n")
    else:
        print("\n✅ Nothing needs you — running fully unattended. Go get tea. ☕\n")

    head("Unattended: link D1 -> schema -> sync -> deploy")
    if not ensure_d1(pf): return 1
    ensure_schema(pf)
    sync_public()
    ok, url = deploy()
    if ok and url: health(url)

    print()
    if ok:
        print("✅ DONE. Your app is live at:  %s" % (url or "https://glass-crud-api.*.workers.dev"))
        print("   Open it, enter your password once (it's the launcher).")
        if url:
            print("   Glasses one-tap QR:")
            print('     python tools/qr.py "Meta Glass" "%s/#glass&t=YOUR_PASSWORD"' % url)
    else:
        print("Deploy did not complete — see the wrangler output above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
