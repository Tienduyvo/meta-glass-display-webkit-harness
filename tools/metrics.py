# -*- coding: utf-8 -*-
"""App-factory metrics — apps built, time-to-build, time-to-improve (owner rule 2026-07-11).

Derived from the loop's own artifacts, so nothing has to be logged by hand:
  built        = when apps/<slug>/acceptance.md first appeared (git first-add; mtime while
                 uncommitted)
  build time   = acceptance.md first appearing -> verdict.md first appearing (the Define
                 round opening -> the first evaluated PASS). Apps whose artifacts predate
                 tracking (or landed in one commit) show "pre-tracking".
  improve time = span + count of commits touching apps/<slug>/ AFTER the verdict landed
                 (the test -> learn -> harden lane), plus open/closed findings boxes.

Usage:
  python tools/metrics.py             # print the table
  python tools/metrics.py --readme    # also rewrite the README block between
                                      # <!-- app-metrics:start --> ... <!-- app-metrics:end -->
Run `--readme` at the end of every loop (CLEAN state) so the factory table stays current.
"""
import json
import os
import re
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
LEDGER = os.path.join(ROOT, "app-metrics.json")  # committed: locks in measured times
MARK_START, MARK_END = "<!-- app-metrics:start -->", "<!-- app-metrics:end -->"


def git(*args):
    p = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "").strip() if p.returncode == 0 else ""


def first_commit_ts(path):
    """Unix ts of the commit that first added `path` ('' if never committed)."""
    out = git("log", "--follow", "--diff-filter=A", "--format=%at", "--", path)
    return int(out.splitlines()[-1]) if out else 0


def touch_ts_after(prefix, after_ts):
    """Commit timestamps touching `prefix` strictly after `after_ts` (newest first)."""
    out = git("log", "--format=%at", "--", prefix)
    return [int(t) for t in out.splitlines() if after_ts and int(t) > after_ts]


def artifact_ts(path):
    """When an artifact appeared: git first-add, else file mtime (uncommitted work)."""
    ts = first_commit_ts(path)
    if ts:
        return ts, "git"
    full = os.path.join(ROOT, path)
    return (int(os.path.getmtime(full)), "mtime") if os.path.exists(full) else (0, "")


def _ktok(v):
    if not v:
        return "?"
    return "%.0fk" % (v / 1000.0) if v >= 1000 else str(int(v))


def fmt_dur(seconds):
    if seconds <= 0:
        return "—"
    m = round(seconds / 60)
    if m < 60:
        return "%dm" % m
    if m < 60 * 24:
        return "%dh%02dm" % (m // 60, m % 60)
    return "%.1fd" % (m / 60 / 24)


def findings_counts(slug):
    p = os.path.join(ROOT, "apps", slug, "findings.md")
    if not os.path.exists(p):
        return 0, 0
    t = open(p, encoding="utf-8").read()
    return len(re.findall(r"(?m)^\s*-\s*\[ \]", t)), len(re.findall(r"(?m)^\s*-\s*\[x\]", t))


def collect():
    reg = json.load(open(os.path.join(ROOT, "apps", "registry.json"), encoding="utf-8"))
    # Ledger: a build time measured from live mtimes must survive the commit (where
    # acceptance+verdict land together and the git-derived diff collapses to zero).
    try:
        ledger = json.load(open(LEDGER, encoding="utf-8"))
    except Exception:
        ledger = {}
    ledger_dirty = False
    rows = []
    for a in reg.get("apps", []):
        m = re.search(r"apps/([^/]+)/", a.get("config", ""))
        if not m:
            continue
        slug = m.group(1)
        acc_ts, acc_src = artifact_ts("apps/%s/acceptance.md" % slug)
        ver_ts, ver_src = artifact_ts("apps/%s/verdict.md" % slug)
        built = acc_ts or ver_ts or artifact_ts("apps/%s/app.config.json" % slug)[0]
        # Same-commit artifacts (or missing acceptance) predate per-phase tracking.
        tracked = acc_ts and ver_ts and ver_ts > acc_ts and not (
            acc_src == "git" and ver_src == "git" and acc_ts == ver_ts)
        build_s = (ver_ts - acc_ts) if tracked else 0
        if slug in ledger and ledger[slug].get("build_seconds"):
            build_s, tracked = ledger[slug]["build_seconds"], True
        elif tracked:
            # durations only — no calendar timestamps in the committed ledger
            # (owner rule 2026-07-11: no personal time-of-day/date shown)
            ledger[slug] = {"build_seconds": build_s}
            ledger_dirty = True
        improves = touch_ts_after("apps/%s/" % slug, ver_ts) if ver_ts else []
        improve_s = (max(improves) - min(improves)) if len(improves) > 1 else 0
        open_f, closed_f = findings_counts(slug)
        # Tokens + model come from the ledger (owner 2026-07-11): they aren't in any
        # git artifact, so the builder records them per app with `metrics.py tokens`.
        led = ledger.get(slug, {})
        tok = led.get("tokens")
        model = led.get("model", "")
        tok_cell = "%s (build) / %s (fix)" % (_ktok(tok.get("build")), _ktok(tok.get("fix"))) \
            if isinstance(tok, dict) else "—"
        # Durations only, no calendar dates (owner rule 2026-07-11): "when" an app was
        # built is personal schedule information and stays out of the README.
        rows.append({
            "app": a.get("name", slug), "slug": slug,
            "build": fmt_dur(build_s) if tracked else "pre-tracking",
            "improve": ("%s · %d commit(s)" % (fmt_dur(improve_s), len(improves)))
                       if improves else "—",
            "findings": "%d open / %d closed" % (open_f, closed_f),
            "tokens": tok_cell,
            "model": model or "—",
        })
    if ledger_dirty:
        tmp = LEDGER + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(ledger, f, indent=1)
        os.replace(tmp, LEDGER)
    return rows


def table_md(rows):
    lines = ["| App | Time to build | Improvement | Tokens | Model | Findings |",
             "|---|---|---|---|---|---|"]
    for r in rows:
        lines.append("| %s | %s | %s | %s | %s | %s |"
                     % (r["app"], r["build"], r["improve"], r["tokens"],
                        r["model"], r["findings"]))
    lines.append("")
    lines.append("**%d apps** in the launcher · times derived from the loop's artifacts "
                 "(`acceptance.md` → `verdict.md` → later commits), updated by "
                 "`python tools/metrics.py --readme` at the end of every build loop."
                 % len(rows))
    return "\n".join(lines)


def update_readme(md):
    t = open(README, encoding="utf-8").read()
    block = MARK_START + "\n" + md + "\n" + MARK_END
    if MARK_START in t and MARK_END in t:
        t = re.sub(re.escape(MARK_START) + r".*?" + re.escape(MARK_END), block, t, flags=re.S)
    else:
        # First run: insert as an own section after the intro (before '## What you can build').
        anchor = "## What you can build"
        section = "## 🏭 App factory metrics\n\n" + block + "\n\n"
        t = t.replace(anchor, section + anchor, 1) if anchor in t else t + "\n" + section
    tmp = README + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    os.replace(tmp, README)


def record_tokens(slug, model, build_tok, fix_tok):
    """Record per-app model + token spend into the ledger (owner 2026-07-11: the README
    tracks tokens used to build/fix and which model). Tokens aren't in any git artifact,
    so the builder logs them here at the end of a build/fix. Additive: fix tokens
    accumulate across improvement rounds."""
    try:
        ledger = json.load(open(LEDGER, encoding="utf-8"))
    except Exception:
        ledger = {}
    row = ledger.setdefault(slug, {})
    if model:
        row["model"] = model
    tok = row.setdefault("tokens", {})
    if build_tok is not None:
        tok["build"] = int(build_tok)
    if fix_tok is not None:
        tok["fix"] = int(tok.get("fix") or 0) + int(fix_tok)
    tmp = LEDGER + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(ledger, f, indent=1)
    os.replace(tmp, LEDGER)
    print("recorded %s: model=%s build=%s fix+=%s" % (slug, model, build_tok, fix_tok))


def main(argv):
    # `tokens <slug> <model> [build_tokens] [fix_tokens]` — log spend, then refresh.
    if argv and argv[0] == "tokens" and len(argv) >= 3:
        record_tokens(argv[1], argv[2],
                      int(argv[3]) if len(argv) > 3 and argv[3] else None,
                      int(argv[4]) if len(argv) > 4 and argv[4] else None)
        argv = ["--readme"]
    rows = collect()
    md = table_md(rows)
    print(md)
    if "--readme" in argv:
        update_readme(md)
        print("\nREADME.md metrics block updated.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
