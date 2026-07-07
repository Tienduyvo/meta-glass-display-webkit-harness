# -*- coding: utf-8 -*-
"""Export an app as a self-contained, uploadable folder: the app config + the
build session (this conversation) that created it, as readable Markdown.

Modular: one folder per app under ``published/<slug>/`` — each is independently
committable to GitHub (``published/`` is intentionally NOT git-ignored). Contents:
  - app.config.json   copy of apps/<slug>/app.config.json
  - README.md         what the app is + how it was built
  - BUILD_SESSION.md  the coding-agent conversation, tools condensed, SECRETS REDACTED

Secrets are stripped before writing (the raw transcript is NEVER copied):
bearer tokens, `t=`/`api=` URL params, 32-hex account ids, plus any literal
strings passed with --redact (use this for your app password / token).

Usage:
    python tools/export_app.py                 # export every registered app
    python tools/export_app.py todo            # export one app
    python tools/export_app.py todo --redact SECRET1 --redact SECRET2
    python tools/export_app.py --transcript PATH todo

Always pass your app password / any live tokens via --redact so they are stripped
from the build session before it can be committed.
"""
import os, re, sys, json, glob, shutil

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(ROOT, "apps")
EXPORTS = os.path.join(ROOT, "published")

REDACT = "***REDACTED***"
_PATTERNS = [
    (re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]{8,}"), "Bearer " + REDACT),
    (re.compile(r"([?#&](?:t|token|api|secret)=)[^\s&\"'<>]+"), r"\1" + REDACT),
    (re.compile(r"\b[0-9a-f]{32}\b"), "***REDACTED-ID***"),
]

def redactor(literals):
    lits = sorted({l for l in literals if l}, key=len, reverse=True)
    def red(text):
        if not text:
            return text
        for l in lits:
            text = text.replace(l, REDACT)
        for rx, repl in _PATTERNS:
            text = rx.sub(repl, text)
        return text
    return red


def find_transcript():
    """Newest session .jsonl for this repo under ~/.claude/projects/<slug>/."""
    base = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    slug = re.sub(r"[:\\/ ]", "-", ROOT)          # C:\Users\Me\x -> C--Users-Me-x
    cands = glob.glob(os.path.join(base, slug, "*.jsonl"))
    if not cands:                                  # fallback: any project folder
        cands = glob.glob(os.path.join(base, "*", "*.jsonl"))
    return max(cands, key=os.path.getmtime) if cands else None


def _blocks(content):
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content if isinstance(content, list) else []

def _tool_hint(inp):
    if not isinstance(inp, dict):
        return ""
    for k in ("file_path", "path", "pattern", "command", "description", "url"):
        if inp.get(k):
            v = str(inp[k]).replace("\n", " ")
            return (v[:70] + "…") if len(v) > 70 else v
    return ""

def transcript_to_md(path, red):
    """Render user/assistant turns to Markdown; condense tool calls; skip tool results."""
    out = ["# Build session\n",
           "_Conversation that built this app with the meta-glass-display-webkit-harness coding agent. "
           "Tool calls are condensed and secrets are redacted._\n"]
    for ln in open(path, encoding="utf-8").read().splitlines():
        try: o = json.loads(ln)
        except Exception: continue
        if o.get("type") not in ("user", "assistant"):
            continue
        msg = o.get("message") or {}
        role = msg.get("role")
        texts, tools = [], []
        is_tool_result = False
        for b in _blocks(msg.get("content")):
            t = b.get("type")
            if t == "text" and b.get("text", "").strip():
                texts.append(b["text"].strip())
            elif t == "tool_use":
                hint = _tool_hint(b.get("input"))
                tools.append(f"🔧 `{b.get('name','tool')}`" + (f" — {hint}" if hint else ""))
            elif t == "tool_result":
                is_tool_result = True
        if role == "user":
            if is_tool_result and not texts:
                continue                            # skip tool-result echoes
            body = "\n\n".join(texts).strip()
            # drop system-reminder-only / injected context noise
            if not body or body.startswith("<") or "system-reminder" in body[:40]:
                continue
            out.append("\n---\n\n### 🧑 User\n\n" + red(body) + "\n")
        else:
            chunk = []
            if texts:
                chunk.append(red("\n\n".join(texts)))
            for tl in tools:
                chunk.append("> " + red(tl))
            if chunk:
                out.append("\n### 🤖 Assistant\n\n" + "\n".join(chunk) + "\n")
    return "\n".join(out) + "\n"


def app_readme(slug, cfg):
    fields = "\n".join(f"- **{f.get('label', f['key'])}** (`{f['key']}`, {f.get('type','text')})"
                       for f in cfg.get("fields", []))
    ro = "read-only (bulk-fed)" if cfg.get("readOnly") else "editable (add / check / delete)"
    return (f"# {cfg.get('title', slug)}\n\n"
            f"A tiny list app for Meta glasses + phone, built with the "
            f"[meta-glass-display-webkit-harness](../../AGENTS.md) coding agent.\n\n"
            f"- **Collection:** `{cfg.get('collection', slug)}`\n"
            f"- **Mode:** {ro}\n\n"
            f"## Fields\n{fields or '_none_'}\n\n"
            f"## Files\n"
            f"- `app.config.json` — drop into `apps/{slug}/` of a harness checkout to reuse it.\n"
            f"- `BUILD_SESSION.md` — the conversation that produced it.\n")


def export_one(slug, transcript_md, red):
    src = os.path.join(APPS, slug, "app.config.json")
    if not os.path.exists(src):
        print(f"  ! {slug}: no app.config.json, skipped"); return False
    cfg = json.load(open(src, encoding="utf-8"))
    dest = os.path.join(EXPORTS, slug)
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(src, os.path.join(dest, "app.config.json"))
    open(os.path.join(dest, "README.md"), "w", encoding="utf-8").write(app_readme(slug, cfg))
    open(os.path.join(dest, "BUILD_SESSION.md"), "w", encoding="utf-8").write(
        transcript_md if transcript_md else "_No build session transcript was found._\n")
    print(f"  exported published/{slug}/  (app.config.json, README.md, BUILD_SESSION.md)")
    return True


def registered_slugs():
    try:
        reg = json.load(open(os.path.join(APPS, "registry.json"), encoding="utf-8"))
    except Exception:
        return []
    out = []
    for a in reg.get("apps", []):
        m = re.search(r"apps/([^/]+)/", a.get("config", ""))
        if m: out.append(m.group(1))
    return out


def main(argv):
    slugs, redlits, transcript = [], [], None
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--redact" and i + 1 < len(argv):
            redlits.append(argv[i + 1]); i += 2
        elif a == "--transcript" and i + 1 < len(argv):
            transcript = argv[i + 1]; i += 2
        else:
            slugs.append(a); i += 1
    if not slugs:
        slugs = registered_slugs()
    if not slugs:
        print("No apps to export."); return

    transcript = transcript or find_transcript()
    red = redactor(redlits)
    tmd = None
    if transcript and os.path.exists(transcript):
        tmd = transcript_to_md(transcript, red)
        print(f"Build session: {os.path.basename(transcript)}"
              + (f"  (redacting {len(redlits)} literal secret(s))" if redlits else ""))
        # safety: warn if any provided secret survived
        leaked = [l for l in redlits if l and l in tmd]
        if leaked:
            print(f"  !! WARNING: a --redact value still appears after redaction — aborting.")
            return
    else:
        print("Build session: none found (exporting app config only).")

    os.makedirs(EXPORTS, exist_ok=True)
    n = sum(export_one(s, tmd, red) for s in slugs)
    print(f"\nDone: {n} app(s) -> published/.  Review, then commit/upload if you want.")
    print("Tip: git add published/ && commit — each app folder is self-contained.")


if __name__ == "__main__":
    main(sys.argv[1:])
