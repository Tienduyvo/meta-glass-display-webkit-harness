# -*- coding: utf-8 -*-
"""Fast sanity check before you deploy or publish. Never changes anything.

  - every app.config.json + registry.json parses
  - both launchers' inline <script> pass `node --check` (JS syntax)
  - apps/ and worker/public/apps/ are in sync (no drift)

Exit code 0 = all good, 1 = something failed. Run:  python tools/check.py
"""
import os, re, sys, json, glob, subprocess

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fails = []


def check_json():
    files = glob.glob(os.path.join(ROOT, "apps", "**", "*.json"), recursive=True) \
        + glob.glob(os.path.join(ROOT, "worker", "public", "apps", "**", "*.json"), recursive=True)
    for f in files:
        try:
            json.load(open(f, encoding="utf-8"))
        except Exception as e:
            fails.append("JSON " + os.path.relpath(f, ROOT) + ": " + str(e))
    print("[%s] %d JSON config(s) parse" % ("x" if not fails else "!", len(files)))


def check_launchers():
    node = None
    for c in ("node",):
        try:
            subprocess.run([c, "--version"], capture_output=True); node = c; break
        except Exception:
            pass
    if not node:
        print("[i] node not found — skipped JS syntax check"); return
    # the two launchers + any per-app page endpoint (e.g. presentation-timer/control.html)
    targets = ["app/index.html", "worker/public/index.html"]
    for p in sorted(glob.glob(os.path.join(ROOT, "apps", "**", "*.html"), recursive=True)):
        targets.append(os.path.relpath(p, ROOT).replace("\\", "/"))
    for rel in targets:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        js = "\n;\n".join(re.findall(r"<script>(.*?)</script>", open(p, encoding="utf-8").read(), re.S))
        if not js.strip():
            continue
        tmp = os.path.join(ROOT, ".check_tmp.js")
        open(tmp, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
        os.remove(tmp)
        ok = r.returncode == 0
        print("[%s] %s script syntax" % ("x" if ok else "!", rel))
        if not ok:
            fails.append(rel + " JS: " + (r.stderr.strip().splitlines()[-1] if r.stderr else "error"))


KNOWN_TYPES = {"text", "number", "geo", "link", "video", "image", "audio", "countdown"}
# Types with a dedicated render/action path — each launcher must contain its type-marker
# string, so a type added to one launcher but forgotten in the other fails fast.
RENDERED_TYPES = {"geo", "link", "video", "image", "audio", "countdown"}


def check_field_types():
    """Gate (2026-07-09, audio-type change): configs use only KNOWN_TYPES, and every
    RENDERED_TYPE any app uses is handled by BOTH launchers (string marker parity)."""
    used = set()
    for f in glob.glob(os.path.join(ROOT, "apps", "*", "app.config.json")):
        try:
            cfg = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        for fld in cfg.get("fields", []):
            t = fld.get("type", "text")
            used.add(t)
            if t not in KNOWN_TYPES:
                fails.append("field type: %s uses unknown type '%s'" % (os.path.relpath(f, ROOT), t))
    launchers = [os.path.join(ROOT, "app", "index.html"),
                 os.path.join(ROOT, "worker", "public", "index.html")]
    srcs = {p: open(p, encoding="utf-8").read() for p in launchers if os.path.exists(p)}
    for t in sorted(used & RENDERED_TYPES):
        marker = '"%s"' % t
        for p, src in srcs.items():
            if marker not in src:
                fails.append("launcher parity: %s has no handling for field type '%s'"
                             % (os.path.relpath(p, ROOT), t))
    print("[%s] field types known + handled by both launchers (%s)"
          % ("x" if not any(s.startswith(("field type", "launcher parity")) for s in fails) else "!",
             ", ".join(sorted(used)) or "none"))


def check_drift():
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import sync_public
        d = sync_public.drift()
    except Exception as e:
        print("[i] drift check unavailable: " + str(e)); return
    if d:
        print("[!] worker/public out of sync (%d) — run tools/sync_public.py" % len(d))
        fails.append("drift: " + "; ".join(d))
    else:
        print("[x] apps/ and worker/public/apps/ in sync")


CRED_FILES = ["push.env", ".env", "worker/.dev.vars", ".claude/settings.local.json"]

def check_no_tracked_creds():
    """LOOP PATTERN (owner rule 2026-07-11): credentials/ids live ONLY in git-ignored
    files — never in tracked ones. Standing gate: the verify hook runs this on every
    config edit, so a real id parked in wrangler.toml fails immediately, not at commit."""
    import subprocess
    def git(*a):
        p = subprocess.run(["git"] + list(a), cwd=ROOT, capture_output=True, text=True)
        return p.returncode, (p.stdout or "").strip()
    rc, _ = git("rev-parse", "--git-dir")
    if rc != 0:
        print("[i] not a git repo — skipping tracked-creds gate"); return
    bad = []
    try:
        t = open(os.path.join(ROOT, "worker", "wrangler.toml"), encoding="utf-8").read()
        m = re.search(r'database_id\s*=\s*"([^"]*)"', t)
        if m and "REPLACE" not in m.group(1):
            bad.append("worker/wrangler.toml holds a real database_id (belongs in push.env; deploy.py injects it)")
    except OSError:
        pass
    for f in CRED_FILES:
        if not os.path.exists(os.path.join(ROOT, f)):
            continue
        if git("check-ignore", "-q", f)[0] != 0:
            bad.append("%s exists but is NOT gitignored — add it to .gitignore" % f)
        if git("ls-files", "--error-unmatch", f)[0] == 0:
            bad.append("%s is TRACKED by git — git rm --cached it" % f)
    if bad:
        print("[!] creds hygiene: " + "; ".join(bad))
        fails.append("creds: " + "; ".join(bad))
    else:
        print("[x] creds only in git-ignored files (wrangler.toml placeholder intact)")


def check_no_personal_data():
    """LOOP PATTERN (owner rule 2026-07-11): the repo must not contain — or allow
    deriving — the user's identity/tastes. Reads a git-ignored `.personal-guard`
    denylist (one term per line; itself never committed) and fails if any term appears
    in a git-TRACKED file. Silently skips when the guard file is absent (fresh forks)."""
    import subprocess
    guard = os.path.join(ROOT, ".personal-guard")
    if not os.path.exists(guard):
        return  # no denylist configured (e.g. a fork) — nothing to enforce
    terms = [l.strip() for l in open(guard, encoding="utf-8")
             if l.strip() and not l.startswith("#")]
    if not terms:
        return
    # committed + staged (about-to-be-committed) files — catch a leak BEFORE it lands
    p = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0:
        print("[i] not a git repo — skipping personal-data gate"); return
    st = subprocess.run(["git", "diff", "--cached", "--name-only"], cwd=ROOT,
                        capture_output=True, text=True)
    files = set(p.stdout.splitlines()) | set(st.stdout.splitlines())
    tracked = [f for f in files if f and f != ".personal-guard"]
    hits = []
    low = [t.lower() for t in terms]
    for f in tracked:
        fp = os.path.join(ROOT, f)
        try:
            body = open(fp, encoding="utf-8", errors="ignore").read().lower()
        except OSError:
            continue
        for t, tl in zip(terms, low):
            if tl in body:
                hits.append("%s in %s" % (t, f))
    if hits:
        print("[!] personal data in tracked files: " + "; ".join(hits[:8]))
        fails.append("personal-data: " + "; ".join(hits[:8]))
    else:
        print("[x] no personal-guard term in any tracked file (%d term(s) checked)" % len(terms))


def main():
    print("\nmeta-glass-display-webkit-harness — check")
    print("-----------------------------------------")
    check_json(); check_launchers(); check_field_types(); check_drift()
    check_no_tracked_creds(); check_no_personal_data()
    print()
    if fails:
        print("FAIL (%d):" % len(fails))
        for f in fails:
            print("  - " + f)
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
