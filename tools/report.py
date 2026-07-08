# -*- coding: utf-8 -*-
"""End-of-loop report for an app — the single deliverable that closes the build loop.

Consolidates what the loop otherwise scatters, so the loop can't end half-done:
  1. Features confirmed  — what the app does, from app.config.json (the codified request).
  2. The spec            — given/when/then from apps/<slug>/acceptance.md.
  3. Tests done          — the verdict from apps/<slug>/verdict.md (hard flowtest + soft judge).
  4. Try it              — live URL + control page + the (leak-safe) QR command to add to glasses.
  5. Share & star        — the GitHub star link + share/export hand-off (AGENTS.md section D).

Reads the live worker origin from push.env (GLASS_API/GLASS_LAUNCHER) if present — the URL only,
never the password. Never prints secrets.

Usage:
    python tools/report.py <slug>
"""
import os, sys, re, json, subprocess

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(ROOT, "apps")


def rule(c="-"): return c * 66
def head(t): print("\n" + t + "\n" + rule())


def load_json(p):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return None


def live_origin():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push; push._load_creds_file()
    except Exception:
        pass
    api = os.environ.get("GLASS_API", "").rstrip("/")
    if api.endswith("/api"): return api[:-4].rstrip("/")
    lnch = os.environ.get("GLASS_LAUNCHER", "")
    return re.sub(r"[#?].*$", "", lnch).rstrip("/") or api


def star_url():
    try:
        u = subprocess.run(["git", "remote", "get-url", "origin"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?$", u)
    return "https://github.com/%s/%s" % (m.group(1), m.group(2)) if m else ""


def acceptance_criteria(slug):
    p = os.path.join(APPS, slug, "acceptance.md")
    if not os.path.exists(p): return []
    out = []
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("- ") and re.search(r"\b[Gg]iven\b", s):
            out.append(re.sub(r"\*\*", "", s[2:]).strip())
    return out


def verdict_summary(slug):
    p = os.path.join(APPS, slug, "verdict.md")
    if not os.path.exists(p): return None, []
    txt = open(p, encoding="utf-8").read()
    m = re.search(r"(?im)^\**Result:?\**\s*(.+)$", txt)
    result = m.group(1).strip().rstrip("*") if m else None
    checks = re.findall(r"(?m)^\s*-?\s*\[[xX]\]\s+(.+)$", txt)
    return result, checks


def main(argv):
    if not argv:
        print("usage: report.py <slug>"); return 2
    slug = argv[0]
    cfg = load_json(os.path.join(APPS, slug, "app.config.json"))
    if not cfg:
        print("No apps/%s/app.config.json" % slug); return 1
    reg = load_json(os.path.join(APPS, "registry.json")) or {"apps": []}
    registered = any(("apps/%s/" % slug) in a.get("config", "") for a in reg.get("apps", []))
    origin = live_origin()
    has_control = os.path.exists(os.path.join(APPS, slug, "control.html"))

    print("\n" + rule("="))
    print("  END-OF-LOOP REPORT  ·  " + (cfg.get("title") or slug))
    print(rule("="))

    head("1. Features confirmed")
    surface = "glasses + phone/desktop" if (cfg.get("refresh") or cfg.get("readOnly")) else "phone/desktop"
    print("  Collection : %s   ·   Surface: %s   ·   %s" % (
        cfg.get("collection"), surface, "read-only display" if cfg.get("readOnly") else "editable list"))
    for f in cfg.get("fields", []):
        print("  - %-12s %s" % (f.get("label") or f.get("key"), "(%s)" % f.get("type", "text")))
    acts = [k for k, v in (cfg.get("actions") or {}).items() if v]
    print("  Actions    : %s" % (", ".join(acts) or "none (display only)"))
    if cfg.get("refresh"): print("  Live sync  : every %ss" % cfg["refresh"])
    print("  Registered in launcher: %s" % ("yes" if registered else "NO — not served!"))

    head("2. Spec (from the build conversation) — apps/%s/acceptance.md" % slug)
    crit = acceptance_criteria(slug)
    if crit:
        for c in crit[:20]: print("  - " + c)
    else:
        print("  (no acceptance.md — write given/when/then before calling the loop done)")

    head("3. Tests done — apps/%s/verdict.md" % slug)
    result, checks = verdict_summary(slug)
    print("  Verdict: %s" % (result or "(no verdict.md — run tools/evaluate.py %s)" % slug))
    for c in checks[:20]: print("  [x] " + c)
    print("  (Re-run anytime: python tools/check.py  ·  python tools/evaluate.py %s)" % slug)

    head("4. Try it")
    if origin:
        print("  App        : %s" % origin)
        if has_control:
            print("  Control    : %s/apps/%s/control.html" % (origin, slug))
        print("  Glasses    : %s/#glass&t=YOUR_PASSWORD" % origin)
    else:
        print("  (Deploy first: python tools/deploy.py — then the live URL shows here.)")
    print("  Add to glasses QR (password stays in push.env, masked in output):")
    print("      python tools/qr.py \"Meta Glass\"")

    head("5. Share & star")
    s = star_url()
    print("  Star the kit (helps others find it): %s" % (s or "(no github remote)"))
    print("  Share to use : send the app URL + password to someone you trust (your backend).")
    print("  Export bundle: python tools/export_app.py %s --redact <password>" % slug)
    print(rule("="))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
