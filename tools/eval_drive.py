# -*- coding: utf-8 -*-
"""Reusable UI-eval driver for the soft gate — assertions, not screenshots.

Every eval round used to re-author throwaway Playwright scripts (and pay for their
typos). This driver bundles the recurring checks against a local `wrangler dev`.
Screenshots are deliberately NOT taken here (owner rule 2026-07-11: screenshots come
from the Chrome extension or Windows-MCP, never Playwright) — this tool only asserts
DOM state; capture pictures separately when a visual judgement is needed.

Usage (needs `pip install playwright` + Edge; wrangler dev on :8787):
  python tools/eval_drive.py glass-list <app-tile-index>   # rows render, marquee wiring
  python tools/eval_drive.py glass-detail <app-tile-index> # detail opens, scrollable?
  python tools/eval_drive.py dismiss <app-tile-index>      # D-pad right advances item
  python tools/eval_drive.py launcher                      # tiles, paging, focus ring
Exit 0 = all assertions passed; failures print what broke.
"""
import sys

BASE = "http://localhost:8787"
TOKEN = "localtest"


def _open_glass(pw):
    b = pw.chromium.launch(channel="msedge", headless=True)
    g = b.new_page(viewport={"width": 600, "height": 600})
    g.goto(BASE + "/?glass#t=" + TOKEN)
    g.wait_for_timeout(2200)
    return b, g


def _nav_to_tile(g, idx):
    # grid is 2 cols, paged by 6; walk focus from 0 to idx
    for _ in range(idx // 2):
        g.keyboard.press("ArrowDown"); g.wait_for_timeout(90)
    if idx % 2:
        g.keyboard.press("ArrowRight"); g.wait_for_timeout(90)
    g.keyboard.press("Enter"); g.wait_for_timeout(1600)


def main(argv):
    if len(argv) < 1:
        print(__doc__); return 2
    mode = argv[0]
    idx = int(argv[1]) if len(argv) > 1 else 0
    from playwright.sync_api import sync_playwright
    fails = []
    with sync_playwright() as pw:
        b, g = _open_glass(pw)
        if mode == "launcher":
            n = g.evaluate("document.querySelectorAll('.tile').length")
            if not (1 <= n <= 6): fails.append("tiles per page = %s (want 1..6)" % n)
            if not g.evaluate("!!document.querySelector('.tile.focus')"):
                fails.append("no focus ring on the launcher")
        else:
            _nav_to_tile(g, idx)
            if mode == "glass-list":
                rows = g.evaluate("document.querySelectorAll('.row').length")
                if rows < 1: fails.append("no rows rendered")
                mq = g.evaluate("(function(){var m=document.querySelector('.row.focus .mq');"
                                "return m?{go:m.classList.contains('go')}:null})()")
                if mq is None: fails.append("focused row has no .mq wrap")
            elif mode == "glass-detail":
                g.keyboard.press("Enter"); g.wait_for_timeout(800)
                st = g.evaluate("(function(){var s=document.getElementById('screen');"
                                "return {sh:s.scrollHeight,ch:s.clientHeight,"
                                "acts:document.querySelectorAll('#screen .row').length}})()")
                if st["acts"] < 1: fails.append("no focusable actions in detail")
                print("detail: scrollHeight=%(sh)s clientHeight=%(ch)s actions=%(acts)s" % st)
            elif mode == "dismiss":
                g.keyboard.press("Enter"); g.wait_for_timeout(800)
                h1 = g.evaluate("(document.querySelector('#screen .muted')||{}).nextElementSibling"
                                "?.textContent||''") or ""
                g.keyboard.press("ArrowRight"); g.wait_for_timeout(1000)
                h2 = g.evaluate("(document.querySelector('#screen .muted')||{}).nextElementSibling"
                                "?.textContent||''") or ""
                if not h1 or h1 == h2:
                    fails.append("ArrowRight did not advance (%r -> %r)" % (h1[:30], h2[:30]))
            else:
                fails.append("unknown mode: " + mode)
        b.close()
    if fails:
        print("EVAL-DRIVE FAIL:")
        for f in fails: print("  - " + f)
        return 1
    print("eval-drive %s: PASS" % mode)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
