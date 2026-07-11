# -*- coding: utf-8 -*-
"""Share & contribute — the FIXED end-of-loop step (owner rule 2026-07-11).

An app that passes its gates isn't "done" until the user has been asked whether they
want to star the repo, share the launcher link, or contribute the app to the community
catalog (AGENTS.md §D). loop_state.py holds an app in the SHARE state until this ask is
recorded, so it can't be silently skipped (it was, for every app built 2026-07-11).

  python tools/share.py <slug>           # print the star/share/contribute hand-off to ASK the user
  python tools/share.py <slug> --asked   # record that the ask happened (marks SHARE done)
  python tools/share.py <slug> --contribute  # scaffold apps/community/<slug>/ for a catalog PR

Recording appends a "Share-asked" line to apps/<slug>/verdict.md (no date — privacy rule).
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(ROOT, "apps")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def verdict_path(slug):
    return os.path.join(APPS, slug, "verdict.md")


def already_asked(slug):
    p = verdict_path(slug)
    return os.path.exists(p) and "share-asked" in open(p, encoding="utf-8", errors="replace").read().lower()


def mark_asked(slug):
    p = verdict_path(slug)
    if not os.path.exists(p):
        print("no verdict.md for %s — evaluate the app first" % slug); return 1
    if already_asked(slug):
        print("%s already recorded as share-asked" % slug); return 0
    with open(p, "a", encoding="utf-8", newline="\n") as f:
        f.write("\n<!-- Share-asked: the star/share/contribute hand-off was made to the user "
                "(loop SHARE step). -->\n")
    print("recorded: %s SHARE step done" % slug)
    return 0


def contribute(slug):
    """Scaffold a committable community-catalog entry (config + README stub)."""
    src = os.path.join(APPS, slug, "app.config.json")
    if not os.path.exists(src):
        print("no app.config.json for %s" % slug); return 1
    dst = os.path.join(APPS, "community", slug)
    os.makedirs(dst, exist_ok=True)
    import shutil
    shutil.copy(src, os.path.join(dst, "app.config.json"))
    readme = os.path.join(dst, "README.md")
    if not os.path.exists(readme):
        with open(readme, "w", encoding="utf-8", newline="\n") as f:
            f.write("# %s (community app)\n\nContributed config for the launcher. Drop the\n"
                    "folder into `apps/`, add a line to `apps/registry.json`, and it appears.\n"
                    "No personal data — generic config only.\n" % slug)
    print("scaffolded apps/community/%s/ — review, then open a PR (CONTRIBUTING.md)" % slug)
    return 0


def handoff(slug):
    print("\n=== SHARE & CONTRIBUTE — ask the user (loop SHARE step) ===\n")
    print("App '%s' passed its gates. Ask the user, warmly and directly:" % slug)
    print("  ⭐  Star the repo — helps others find the kit")
    print("  🔗  Share the launcher link + password with someone who'd use it")
    print("  🌱  Contribute this app to the community catalog (apps/community/ PR)")
    print("\nThen record it:  python tools/share.py %s --asked" % slug)
    print("(Contribute scaffold:  python tools/share.py %s --contribute)\n" % slug)
    return 0


def main(argv):
    if not argv:
        print(__doc__); return 2
    slug = argv[0]
    if "--asked" in argv:
        return mark_asked(slug)
    if "--contribute" in argv:
        return contribute(slug)
    return handoff(slug)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
