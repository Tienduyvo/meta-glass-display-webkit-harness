# -*- coding: utf-8 -*-
"""Evaluate an app against its acceptance criteria — the Tier-2 gate, in two halves.

  HARD (automated): tools/flowtest.py — the data/CRUD user-flow, deterministic pass/fail.
  SOFT (agent-judge): the UI / qualitative half a script can't check — does the image
    render, is the ▶ Open action reachable by D-pad, does the flow read well on the
    additive display. This tool can't judge that; it prints the acceptance flow as a
    checklist so the AGENT captures a screenshot of the running app and rules each line.

So: `evaluate.py` runs the hard half and hands you the soft checklist; you (the agent)
open the app on a local `wrangler dev`, screenshot the key state, judge each line, and
write the verdict (PASS only if BOTH halves pass).

Usage:
    python tools/evaluate.py wallpaper
Needs a Worker (GLASS_API/GLASS_TOKEN, or push.env; a local `wrangler dev` for dev).
"""
import os, re, sys, subprocess

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def acceptance_bullets(slug):
    p = os.path.join(ROOT, "apps", slug, "acceptance.md")
    if not os.path.exists(p):
        return None
    out = []
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("- ") and re.search(r"\b[Gg]iven\b", s):
            out.append(re.sub(r"\*\*", "", s[2:]).strip())
    return out


def main(argv):
    if not argv:
        print("usage: evaluate.py <slug>")
        return 2
    slug = argv[0]
    py = sys.executable or "python"
    print("\n================ EVALUATE: %s ================\n" % slug)

    print("HARD gate — flowtest (automated data/CRUD flow):")
    hard_ok = subprocess.run([py, os.path.join(ROOT, "tools", "flowtest.py"), slug]).returncode == 0

    print("\nSOFT gate — agent-judge (screenshot of the running app vs acceptance.md):")
    bullets = acceptance_bullets(slug)
    if bullets is None:
        print("  (!) no apps/%s/acceptance.md — write acceptance criteria first (Define phase)" % slug)
    elif not bullets:
        print("  (!) acceptance.md has no given/when/then flow bullets to judge")
    else:
        for b in bullets:
            print("  [ ] " + b)
    print("\n-> Agent: open the app on a local `wrangler dev`, screenshot the key state,")
    print("   rule each [ ] line PASS/FAIL from the screenshot, then write the verdict.")

    print("\n---------------------------------------------")
    print("HARD gate: %s   |   SOFT gate: agent must judge the lines above" % ("PASS" if hard_ok else "FAIL"))
    print("Overall PASS only if BOTH halves pass.")
    return 0 if hard_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
