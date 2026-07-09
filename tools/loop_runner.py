# -*- coding: utf-8 -*-
"""Code-driven outer loop: the STATE MACHINE drives the agent, not the other way round.

Inside a session, the agent is trusted (nudged by hooks) to advance the loop — but a crashed
session, a compaction, or plain model forgetfulness can strand the loop "nowhere". This
driver makes that impossible for unattended runs: CODE recomputes the state each pass and
hands the agent exactly ONE next action per fresh `claude -p` invocation. The loop never
lives in the model's head, so it can't be forgotten.

    while state has an agent-actionable transition (and < max passes):
        claude -p "<current state> — do THE next action, then stop"
    stop at DONE or a user gate (COMMIT) — those belong to the human.

Usage:
    python tools/loop_runner.py            # up to 8 passes
    python tools/loop_runner.py 3          # cap passes
    python tools/loop_runner.py --dry-run  # show what each pass would be told, don't run
Requires the `claude` CLI on PATH. Each pass runs headless with acceptEdits (file edits
auto-approved; anything bigger still prompts per your permission config)."""
import os, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass


def state_text():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "loop_state.py")],
                       capture_output=True, text=True, cwd=ROOT)
    return r.stdout


def main(argv):
    max_passes, dry = 8, "--dry-run" in argv
    for a in argv:
        if a.isdigit():
            max_passes = int(a)
    claude = shutil.which("claude")
    if not claude and not dry:
        print("`claude` CLI not found on PATH — run this from a machine with Claude Code installed.")
        return 1
    for i in range(1, max_passes + 1):
        state = state_text()
        if "[DONE]" in state:
            print(state)
            print("Driver: loop is DONE — nothing agent-actionable. Stopping.")
            return 0
        if "[COMMIT]" in state:
            print(state)
            print("Driver: loop is at the COMMIT user gate — that decision is yours. Stopping.")
            return 0
        prompt = ("You are one pass of the glass-crud-harness build loop (runbook: AGENTS.md). "
                  "The machine-computed state is:\n\n" + state +
                  "\nDo THE 'Next action' above — only that transition and what it directly "
                  "requires (fix reds it surfaces, re-run its gate). Then stop; the driver "
                  "re-computes the state and starts the next pass.")
        print("=== pass %d/%d — next action per loop_state ===" % (i, max_passes))
        if dry:
            print(prompt)
            print("(dry-run: not invoking claude)\n")
            continue
        subprocess.run([claude, "-p", prompt, "--permission-mode", "acceptEdits"], cwd=ROOT)
    print("Driver: reached the pass cap (%d). Re-run to continue, or inspect `python "
          "tools/loop_state.py` — a transition that won't converge needs a human look." % max_passes)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
