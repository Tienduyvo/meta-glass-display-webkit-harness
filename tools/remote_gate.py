# -*- coding: utf-8 -*-
"""Render a build-loop gate as a WhatsApp-ready message — ONE schema, many renderers.

The bridge design rule: every moment where the loop needs the user is emitted as a
structured GATE OBJECT, and channels (WhatsApp today; voice notes, the glasses stage
later) are just renderers of it. This tool is the WhatsApp text renderer.

Gate JSON schema (all fields optional except kind + title):
    {
      "kind":    "define" | "approval" | "fix" | "status",
      "app":     "flashcards",
      "title":   "Define round",
      "summary": "one spoken-style sentence; glasses read this aloud first",
      "questions": [                       # define rounds: batch ALL questions in one gate
        {"q": "Spaced repetition or simple flip?",
         "options": [{"label": "spaced (SM-2)", "detail": "boxes, due dates"},
                     {"label": "simple flip", "detail": "no scheduling"}]}
      ],
      "options": [ ... ],                  # top-level options for approval-style gates
      "snippet": {"file": "apps/x/app.js", "lines": "10-25", "hl": "12", "note": "..."},
      "ask":     "override for the footer instruction line"
    }

Usage:
    python tools/remote_gate.py <gate.json>     # or - for stdin
    python tools/remote_gate.py --demo          # sample define gate

Output: the message text on stdout; if a snippet is present, renders the PNG and
appends a final line `SNIPPET_PNG: <abs path>` — pass that path in the WhatsApp
reply tool's files[] and everything above it as text.
"""
import os, sys, json, argparse, subprocess

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ICON = {"define": "🟡", "approval": "🔴", "fix": "🔧", "status": "📊"}
ASK = {
    "define": "Antworte pro Frage mit der Nummer (z.B. \"1: 2, 2: 1\") oder einfach per Sprachnachricht.",
    "approval": "Antworte mit der Nummer, \"ja\" oder \"nein\".",
    "fix": "Antworte mit der Nummer oder beschreib es per Sprachnachricht.",
    "status": "",
}


def render_options(opts, indent=""):
    lines = []
    for i, o in enumerate(opts, 1):
        detail = " — %s" % o["detail"] if o.get("detail") else ""
        lines.append("%s*%d* · %s%s" % (indent, i, o["label"], detail))
    return lines


def render(gate):
    kind = gate.get("kind", "status")
    head = "%s *%s*" % (ICON.get(kind, "🟡"), gate["title"])
    if gate.get("app"):
        head += "  ·  _%s_" % gate["app"]
    out = [head]
    if gate.get("summary"):
        out += ["", gate["summary"]]
    for qi, q in enumerate(gate.get("questions", []), 1):
        out += ["", "*%d. %s*" % (qi, q["q"])]
        out += render_options(q.get("options", []), indent="   ")
    if gate.get("options"):
        out.append("")
        out += render_options(gate["options"])
    snip = gate.get("snippet")
    if snip and snip.get("note"):
        out += ["", "🖼️ %s" % snip["note"]]
    ask = gate.get("ask", ASK.get(kind, ""))
    if ask:
        out += ["", "_%s_" % ask]
    return "\n".join(out)


def render_snippet(snip):
    cmd = [sys.executable, os.path.join(ROOT, "tools", "snippet_image.py"),
           os.path.join(ROOT, snip["file"])]
    if snip.get("lines"):
        cmd += ["--lines", snip["lines"]]
    if snip.get("hl"):
        cmd += ["--hl", str(snip["hl"])]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


DEMO = {
    "kind": "define",
    "app": "flashcards",
    "title": "Define round — 2 Fragen",
    "summary": "Bevor ich flashcards baue: zwei Entscheidungen, dann läuft der Rest ohne dich durch.",
    "questions": [
        {"q": "Lernmodus?",
         "options": [{"label": "Spaced repetition", "detail": "Boxen + Fälligkeit, mehr Logik"},
                     {"label": "Simple flip", "detail": "nur umdrehen, kein Scheduling"}]},
        {"q": "Karten-Quelle?",
         "options": [{"label": "Manuell anlegen", "detail": "CRUD im Handy-UI"},
                     {"label": "Markdown-Import", "detail": "eine .md Datei pro Deck"}]},
    ],
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("gate", nargs="?", help="gate JSON file, or - for stdin")
    p.add_argument("--demo", action="store_true")
    a = p.parse_args()

    if a.demo:
        gate = DEMO
    elif a.gate == "-":
        gate = json.load(sys.stdin)
    elif a.gate:
        gate = json.load(open(a.gate, encoding="utf-8"))
    else:
        p.error("pass a gate.json, -, or --demo")

    print(render(gate))
    snip = gate.get("snippet")
    if snip and snip.get("file"):
        png = render_snippet(snip)
        if png:
            print("SNIPPET_PNG: %s" % png)


if __name__ == "__main__":
    main()
