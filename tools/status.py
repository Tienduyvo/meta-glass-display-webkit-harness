# -*- coding: utf-8 -*-
"""Status doctor: 'where am I / what's next'. Run this first, in an agent or by hand.
    python tools/status.py
Never fails; prints a checklist + the single most relevant next action."""
import os, re, json, shutil, subprocess, sys
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def has_node():
    return bool(shutil.which("npx") or shutil.which("node"))

def d1_configured():
    p = os.path.join(ROOT, "worker", "wrangler.toml")
    try:
        t = open(p, encoding="utf-8").read()
        m = re.search(r'database_id\s*=\s*"([^"]*)"', t)
        return bool(m and "REPLACE" not in m.group(1) and m.group(1).strip())
    except Exception:
        return False

def published():
    try:
        r = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                           capture_output=True, text=True, timeout=10)
        return (r.returncode == 0 and r.stdout.strip(), r.stdout.strip())
    except Exception:
        return (False, "")

def apps():
    try:
        reg = json.load(open(os.path.join(ROOT, "apps", "registry.json"), encoding="utf-8"))
        return [a.get("name", "?") for a in reg.get("apps", [])]
    except Exception:
        return []

def app_drift():
    """List reasons apps/ and worker/public/apps/ are out of sync (empty = in sync)."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import sync_public
        return sync_public.drift()
    except Exception:
        return []

def line(ok, label):
    return ("[x] " if ok else "[ ] ") + label

def main():
    node = has_node(); d1 = d1_configured(); pub, url = published(); names = apps()
    drift = app_drift()
    print("\nmeta-glass-display-webkit-harness — status")
    print("---------------------------")
    print(line(node, "Node.js / npx installed"))
    print(line(d1,   "Backend: D1 configured in worker/wrangler.toml"))
    print(line(bool(pub), "Published to GitHub" + (f" ({url})" if pub else "")))
    print(f"[i] Apps registered: {len(names)}" + (f" — {', '.join(names)}" if names else ""))
    if drift:
        print(f"[!] worker/public out of sync ({len(drift)}): run runners/redeploy.bat (syncs + deploys)")
    print("[i] Worker URL + password: entered once in the launcher (browser) — not detectable here")

    print("\nNext step:")
    if not node:
        print("  Install Node.js (https://nodejs.org), then run runners/deploy_worker.bat")
    elif not d1:
        print("  Deploy the backend:  runners/deploy_worker.bat   (Cloudflare login, D1, secret, deploy)")
    elif not pub:
        print("  You're live at your Worker URL. Add apps:  python tools/new_app.py  then  runners/redeploy.bat")
        print("  Optional — open-source your kit:  runners/setup_repo.bat")
    else:
        print("  You're set. Add apps:  python tools/new_app.py  then  runners/redeploy.bat")
        print("  Open the launcher (phone/glasses) at your Worker URL.")
    print()

if __name__ == "__main__":
    main()
