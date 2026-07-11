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
    is_page = bool(re.match(r"apps/[^/]+/.+\.html$", rel))  # per-app page endpoint (e.g. control.html)
    is_meta = rel in ("apps/registry.json", "app/index.html",
                      "worker/public/index.html", "worker/src/worker.js")
    if not (is_config or is_page or is_meta):
        return 0  # not app-relevant -> no-op

    py = sys.executable or "python"
    problems = []

    is_html = rel.endswith(".html")
    if is_html:
        # FAST PATH (multi-edit sessions were paying ~seconds per edit): an HTML edit
        # can only break its own script syntax — extract its <script> blocks and
        # node-check just this one file. flowtest is API-level and can't be affected
        # by HTML; drift is reported for app pages.
        import tempfile
        src = open(os.path.join(ROOT, rel), encoding="utf-8").read()
        js = "\n;\n".join(re.findall(r"<script[^>]*>(.*?)</script>", src, re.S))
        tf = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                         encoding="utf-8")
        tf.write(js); tf.close()
        try:
            r = subprocess.run(["node", "--check", tf.name],
                               capture_output=True, text=True, cwd=ROOT)
            if r.returncode != 0:
                problems.append("%s script syntax failed:\n%s"
                                % (rel, (r.stdout or "") + (r.stderr or "")))
        finally:
            os.unlink(tf.name)
        if not problems and rel.startswith("apps/"):
            try:
                sys.path.insert(0, os.path.join(ROOT, "tools"))
                import sync_public
                if any(rel.split("/", 2)[1] in d for d in sync_public.drift()):
                    problems.append("drift: %s differs from worker/public — run tools/sync_public.py" % rel)
            except Exception:
                pass
    else:
        r = subprocess.run([py, os.path.join(ROOT, "tools", "check.py")],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            problems.append("check.py (static) failed:\n" + (r.stdout or "") + (r.stderr or ""))

        if _worker_up():
            env = dict(os.environ, GLASS_API="http://localhost:8787/api", GLASS_TOKEN=_dev_token())
            m = re.match(r"apps/([^/]+)/", rel)
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
