# -*- coding: utf-8 -*-
"""PostToolUse hook: the moment an app config / launcher / worker file changes, run
the verify gate automatically so the agent gets immediate pass/fail feedback and
fixes red in the same turn (the self-running Build -> Test -> Fix loop).

Reads the hook JSON on stdin. If the edited file isn't app-relevant, it's a fast
no-op. Otherwise it runs `tools/check.py` (static) and, if a local `wrangler dev`
is up on :8787, `tools/flowtest.py` for the affected app(s). On failure it writes
the reason to stderr and exits 2 (Claude sees it and fixes); on success it's quiet.

Wired in `.claude/settings.json` (PostToolUse, matcher Edit|Write|MultiEdit).
Keep `wrangler dev` running during app work so the flowtest gate fires automatically.
"""
import os, sys, json, re, subprocess, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rel(p):
    try:
        return os.path.relpath(os.path.abspath(p), ROOT).replace("\\", "/")
    except Exception:
        return p or ""


def _worker_up():
    try:
        with urllib.request.urlopen("http://localhost:8787/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def _dev_token():
    try:
        for line in open(os.path.join(ROOT, "worker", ".dev.vars"), encoding="utf-8"):
            if line.strip().startswith("API_SECRET="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return "localtest"


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    ti = data.get("tool_input") or {}
    rel = _rel(ti.get("file_path") or ti.get("path") or "")

    is_config = bool(re.match(r"apps/[^/]+/app\.config\.json$", rel))
    is_meta = rel in ("apps/registry.json", "app/index.html",
                      "worker/public/index.html", "worker/src/worker.js")
    if not (is_config or is_meta):
        return 0  # not app-relevant -> no-op

    py = sys.executable or "python"
    problems = []

    r = subprocess.run([py, os.path.join(ROOT, "tools", "check.py")],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        problems.append("check.py (static) failed:\n" + (r.stdout or "") + (r.stderr or ""))

    if _worker_up():
        env = dict(os.environ, GLASS_API="http://localhost:8787/api", GLASS_TOKEN=_dev_token())
        m = re.match(r"apps/([^/]+)/app\.config\.json$", rel)
        args = [m.group(1)] if m else []  # one app, or all registered
        r = subprocess.run([py, os.path.join(ROOT, "tools", "flowtest.py")] + args,
                           capture_output=True, text=True, cwd=ROOT, env=env)
        if r.returncode != 0:
            problems.append("flowtest (runtime) failed:\n" + (r.stdout or "") + (r.stderr or ""))

    if problems:
        sys.stderr.write("\n[verify_hook] VERIFY FAILED - fix before continuing:\n\n"
                         + "\n\n".join(problems) + "\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
