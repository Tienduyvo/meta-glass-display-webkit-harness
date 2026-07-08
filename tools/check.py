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
        print("[i] node not found — skipped launcher JS syntax check"); return
    for rel in ("app/index.html", "worker/public/index.html"):
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        js = "\n;\n".join(re.findall(r"<script>(.*?)</script>", open(p, encoding="utf-8").read(), re.S))
        tmp = os.path.join(ROOT, ".check_tmp.js")
        open(tmp, "w", encoding="utf-8").write(js)
        r = subprocess.run([node, "--check", tmp], capture_output=True, text=True)
        os.remove(tmp)
        ok = r.returncode == 0
        print("[%s] %s script syntax" % ("x" if ok else "!", rel))
        if not ok:
            fails.append(rel + " JS: " + r.stderr.strip().splitlines()[-1] if r.stderr else rel + " JS error")


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


def main():
    print("\nmeta-glass-display-webkit-harness — check")
    print("-----------------------------------------")
    check_json(); check_launchers(); check_drift()
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
