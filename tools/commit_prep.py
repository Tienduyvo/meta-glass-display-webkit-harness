# -*- coding: utf-8 -*-
"""CLEAN & COMMIT — prepare the loop's hand-off gate so commits come out professional.

Two jobs, no side effects (never stages or commits anything itself):

  1. HYGIENE (hard, exit 1 on failure — the loop's CLEAN state):
     - worker/wrangler.toml must hold the placeholder database_id (no personal id ships)
     - no secret-bearing files tracked (push.env, .dev.vars, settings.local.json)
     - dirty text files scanned for credential patterns and stray UUIDs (D1 ids)
     - leftover junk in the tree (*.bak/*.tmp/*.log untracked and not ignored)

  2. STRUCTURE (advisory): groups the dirty files into logical conventional commits
     (one per app slug; kit; docs; harness) with a suggested `type(scope):` stub.
     The agent writes the real message: imperative subject <= 72 chars, a body that
     says WHY, wrapped at ~72 — see AGENTS.md "Clean & commit".

Usage:  python tools/commit_prep.py        (also imported by tools/loop_state.py)
"""
import os, re, sys, json, subprocess

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_FILES = ("push.env", ".dev.vars", "settings.local.json")
SECRET_RX = re.compile(r"(?i)\b(api[_-]?key|secret|token|passw\w*)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}")
UUID_RX = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
SAFE_HINTS = ("replace_with", "your_password", "localtest", "example", "placeholder")
TEXT_EXT = (".json", ".md", ".html", ".js", ".py", ".toml", ".yml", ".yaml", ".bat", ".txt", ".sql")


def _git(*args):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True, timeout=15)
    return r.stdout


def dirty_files():
    """[(status, path)] for everything uncommitted (staged, unstaged, untracked)."""
    out = []
    for l in _git("status", "--porcelain").splitlines():
        if l.strip():
            out.append((l[:2], l[3:].strip().strip('"').replace("\\", "/")))
    return out


def hygiene_issues(files=None):
    """List of blocking hygiene problems (empty = clean). The loop's CLEAN gate."""
    issues = []
    files = files if files is not None else dirty_files()

    try:
        t = open(os.path.join(ROOT, "worker", "wrangler.toml"), encoding="utf-8").read()
        m = re.search(r'database_id\s*=\s*"([^"]*)"', t)
        if m and "REPLACE" not in m.group(1):
            issues.append("worker/wrangler.toml holds a real database_id — revert to the placeholder before committing")
    except Exception:
        pass

    tracked = _git("ls-files")
    for name in SECRET_FILES:
        for line in tracked.splitlines():
            if line.endswith(name):
                issues.append("secret-bearing file is TRACKED: %s — git rm --cached it and gitignore it" % line)

    for st, p in files:
        if st == "??" and re.search(r"\.(bak|tmp|log|orig|rej)$|~$", p):
            issues.append("leftover junk in the tree: %s — delete it or add to .gitignore" % p)
        full = os.path.join(ROOT, p)
        if st != "??" or not p.endswith(TEXT_EXT) or not os.path.isfile(full):
            if not (os.path.isfile(full) and p.endswith(TEXT_EXT)):
                continue
        try:
            body = open(full, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        for rx, what in ((SECRET_RX, "credential-like value"), (UUID_RX, "UUID (personal id?)")):
            for m in rx.finditer(body):
                ctx = body[max(0, m.start() - 40):m.end() + 10].lower()
                if any(h in ctx for h in SAFE_HINTS):
                    continue
                issues.append("%s in %s: …%s…" % (what, p, m.group(0)[:44]))
                break
    return issues


def grouped(files=None):
    """Group dirty paths into logical commits: [(subject-stub, [paths])]."""
    files = files if files is not None else dirty_files()
    apps, kit, docs, harness = {}, [], [], []
    for _, p in files:
        m = re.match(r"(?:worker/public/)?apps/([^/]+)/", p)
        if m and m.group(1) != "community":
            apps.setdefault(m.group(1), []).append(p)
        elif p.startswith((".claude/", ".github/")):
            harness.append(p)
        elif p.endswith(".md") and "/" not in p or p.startswith("docs/"):
            docs.append(p)
        else:
            kit.append(p)  # launchers, worker/src, tools/, runners/, registry
    plans = []
    for slug, ps in sorted(apps.items()):
        plans.append(("feat(%s): <what changed, imperative>" % slug, sorted(ps)))
    if kit:
        plans.append(("feat(kit)|fix(kit): <launcher/worker/tools change>", sorted(kit)))
    if harness:
        plans.append(("chore(harness): <hooks/CI/settings change>", sorted(harness)))
    if docs:
        plans.append(("docs: <what and why>", sorted(docs)))
    return plans


def main():
    files = dirty_files()
    print("\ncommit prep — clean & structure")
    print("-------------------------------")
    if not files:
        print("Working tree clean — nothing to commit.\n")
        return 0
    issues = hygiene_issues(files)
    for i in issues:
        print("  [!] " + i)
    print("  [%s] hygiene %s" % ("!" if issues else "x",
                                 "FAILED — fix the lines above first" if issues else "clean"))
    print("\nSuggested commit structure (%d dirty file(s)):" % len(files))
    for subject, ps in grouped(files):
        print("\n  " + subject)
        for p in ps:
            print("    - " + p)
    print("\nAgent: write real messages (imperative subject <=72 chars; body = the WHY, wrapped),")
    print("stage each group, commit, push. Related docs (CHANGELOG/AGENTS) may fold into the")
    print("commit they document instead of a separate docs commit — judgement over rules.\n")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
