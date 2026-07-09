# -*- coding: utf-8 -*-
"""The build loop as an explicit STATE MACHINE — the agent's 'where am I / what do I do now'.

States per app (computed from artifacts on disk, like `git status` computes yours):

    DEFINE  apps/<slug>/acceptance.md missing, or has no surface plan / definition section
    VERIFY  no verdict.md yet — run `python tools/evaluate.py <slug>` and judge the soft gate
    FIX     verdict.md exists but is not a PASS — fix and re-evaluate
    SYNC    apps/ and worker/public/ differ — run `python tools/sync_public.py`
    DEPLOY  worker/public differs from the LIVE worker (compared over HTTP) — run `python tools/deploy.py`
    COMMIT  loop artifacts uncommitted — a user gate: propose the commit, don't just stop
    DONE    nothing actionable

Usage:
    python tools/loop_state.py               # human/agent-readable: states + THE next action
    python tools/loop_state.py --stop-hook   # Claude Code Stop hook: if the agent stops while an
                                             # agent-actionable transition remains on an app it
                                             # touched this session (git-dirty), block the stop
                                             # once and feed the next action back. Honors
                                             # stop_hook_active so it can't loop forever.
Never fails (exit 0 always) — a state doctor, not a gate."""
import os, re, sys, json, subprocess, urllib.request

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(ROOT, "apps")


def registered():
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


def app_state(slug):
    """(STATE, next-action) for one app; ('OK', None) when its own gates are green."""
    acc = os.path.join(APPS, slug, "acceptance.md")
    if not os.path.exists(acc):
        return ("DEFINE", "write apps/%s/acceptance.md — Define round: 2-3 questions + per-surface plan" % slug)
    txt = open(acc, encoding="utf-8", errors="replace").read().lower()
    if "surface plan" not in txt and "## definition" not in txt:
        return ("DEFINE", "apps/%s/acceptance.md lacks the surface plan — add Definition + Surface plan sections" % slug)
    ver = os.path.join(APPS, slug, "verdict.md")
    if not os.path.exists(ver):
        return ("VERIFY", "run `python tools/evaluate.py %s` (wrangler dev up), judge the soft gate, write verdict.md" % slug)
    head = open(ver, encoding="utf-8", errors="replace").read(600)
    if "PASS" not in head:
        return ("FIX", "apps/%s/verdict.md is not a PASS — fix the red gate and re-run evaluate" % slug)
    return ("OK", None)


def drift():
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import sync_public
        return sync_public.drift()
    except Exception:
        return []


def git_dirty_paths():
    try:
        r = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True, timeout=10)
        return [l[3:].strip().strip('"') for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []


def dirty_slugs(paths):
    out = set()
    for p in paths:
        m = re.match(r"(?:worker/public/)?apps/([^/]+)/", p.replace("\\", "/"))
        if m:
            out.add(m.group(1))
    return out


def _launcher_base():
    """Worker base URL from push.env / env (GLASS_API minus /api). None if unknown."""
    try:
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import push
        push._load_creds_file()
    except Exception:
        pass
    api = os.environ.get("GLASS_API", "").rstrip("/")
    if not api or "localhost" in api or "127.0.0.1" in api:
        return None
    return re.sub(r"/api$", "", api)


def _get(url):
    """GET with a real User-Agent — Cloudflare 403s python-urllib's default. None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "meta-glass-webkit-loopstate/1.0"})
        with urllib.request.urlopen(req, timeout=4) as r:
            return r.read()
    except Exception:
        return None


def deploy_mismatch():
    """True if the LIVE worker serves a different registry/config than worker/public.
    None = can't tell (offline / no URL) — never nag on unknown."""
    base = _launcher_base()
    if not base:
        return None
    def live(path):
        return _get(base + path)
    def local(path):
        try:
            return open(os.path.join(ROOT, "worker", "public") + path, "rb").read()
        except Exception:
            return b""
    reg = live("/apps/registry.json")
    if reg is None:
        return None
    if reg.strip() != local("/apps/registry.json").strip():
        return True
    for slug in registered():
        p = "/apps/%s/app.config.json" % slug
        l = live(p)
        if l is not None and l.strip() != local(p).strip():
            return True
    return False


def transitions(only_dirty=False):
    """Ordered agent-actionable transitions: [(STATE, action)]. Empty = nothing to push."""
    out = []
    dirty = dirty_slugs(git_dirty_paths())
    for slug in registered():
        if only_dirty and slug not in dirty:
            continue
        st, act = app_state(slug)
        if act:
            out.append((st, act))
    d = drift()
    if d:
        out.append(("SYNC", "apps/ and worker/public/ differ (%d) — run `python tools/sync_public.py`" % len(d)))
    elif not out:  # only worth checking the live site once local states are green
        m = deploy_mismatch()
        if m:
            out.append(("DEPLOY", "live worker differs from worker/public — run `python tools/deploy.py` "
                                  "(then revert wrangler.toml database_id to the placeholder)"))
    if not out:
        try:
            import commit_prep
            issues = commit_prep.hygiene_issues()
            if issues:
                out.append(("CLEAN", "commit hygiene failed (%d): %s — run `python tools/commit_prep.py`"
                            % (len(issues), issues[0])))
        except Exception:
            pass
    return out


def print_table():
    dirty = dirty_slugs(git_dirty_paths())
    print("\nloop state (per app)")
    print("--------------------")
    backlog = 0
    for slug in registered():
        st, act = app_state(slug)
        if act and slug not in dirty:
            backlog += 1
        mark = "*" if slug in dirty else " "
        print(" %s %-22s %-7s%s" % (mark, slug, st, (" -> " + act) if act else ""))
    print("   (* = touched in this working tree — agent-actionable now; the rest is backlog)")
    t = transitions(only_dirty=True)
    d = git_dirty_paths()
    print("\nNext action:")
    if t:
        print("  [%s] %s" % t[0])
    elif d:
        print("  [COMMIT] %d file(s) uncommitted — run `python tools/commit_prep.py`, present the plan,"
              " commit + push on approval (user gate)" % len(d))
    else:
        print("  [DONE] nothing actionable — invite real-device testing / share")
    if backlog:
        print("  (backlog: %d committed app(s) predate a gate — improve when next touched, don't churn)" % backlog)
    print()


def stop_hook():
    """Stop-hook mode: block the agent's stop ONCE when an agent-actionable transition
    remains on something it touched (git-dirty). stop_hook_active prevents nag loops."""
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if payload.get("stop_hook_active"):
        return
    t = transitions(only_dirty=True)
    if not t:
        return
    st, act = t[0]
    print(json.dumps({
        "decision": "block",
        "reason": "[loop_state] The build loop is not at a resting state: %s — %s. "
                  "Do this now if it needs no user input; if you are genuinely blocked on the user "
                  "(or a gate stayed red after ~3 fix attempts), say exactly what you need and stop. "
                  "Full picture: python tools/loop_state.py" % (st, act)
    }))


if __name__ == "__main__":
    if "--stop-hook" in sys.argv:
        stop_hook()
    else:
        print_table()
    sys.exit(0)
