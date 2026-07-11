# -*- coding: utf-8 -*-
"""Build queue — line up several app-build ideas; the loop works through them one by one.

Owner ask 2026-07-11: "a real queue function so I can have multiple loops for multiple
app devs." The queue is a durable list of build requests. Claude (the app builder) pulls
the next PENDING item, runs the full AGENTS.md loop for it (Define → build → evaluate →
deploy), marks it DONE, and moves on — announcing each over the bridge, no babysitting.

Storage: git-ignored `build_queue.json` at the repo root (an app idea can hint at
personal interests → template-level rule keeps it out of git). Atomic writes.

Usage:
  python tools/build_queue.py add "a strava-style run tracker"   # enqueue
  python tools/build_queue.py list                               # show the queue
  python tools/build_queue.py next                               # print the next PENDING (JSON) — the builder claims it
  python tools/build_queue.py start <id>                         # mark in_progress
  python tools/build_queue.py done <id> [slug]                   # mark done
  python tools/build_queue.py drop <id>                          # remove
Status values: pending -> in_progress -> done.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(ROOT, "build_queue.json")

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _load():
    try:
        return json.load(open(QUEUE, encoding="utf-8"))
    except Exception:
        return {"seq": 0, "items": []}


def _save(q):
    tmp = QUEUE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(q, f, ensure_ascii=False, indent=1)
    os.replace(tmp, QUEUE)


def _find(q, qid):
    return next((it for it in q["items"] if it["id"] == qid), None)


def add(idea):
    q = _load()
    q["seq"] += 1
    qid = "q%d" % q["seq"]
    # No timestamp: Date.now()-style calls are avoided elsewhere in this kit and the
    # queue is ordered by seq anyway; the builder stamps completion in the app's docs.
    q["items"].append({"id": qid, "idea": idea, "status": "pending", "slug": ""})
    _save(q)
    print("queued %s: %s" % (qid, idea))
    return qid


def cmd_list():
    q = _load()
    if not q["items"]:
        print("queue empty"); return
    order = {"in_progress": 0, "pending": 1, "done": 2}
    for it in sorted(q["items"], key=lambda x: (order.get(x["status"], 9), x["id"])):
        mark = {"pending": "· ", "in_progress": "▶ ", "done": "✓ "}.get(it["status"], "  ")
        print("%s%s [%s]%s %s" % (mark, it["id"], it["status"],
                                  (" " + it["slug"]) if it["slug"] else "", it["idea"]))


def cmd_next():
    q = _load()
    nxt = next((it for it in q["items"] if it["status"] == "pending"), None)
    print(json.dumps(nxt) if nxt else "")


def set_status(qid, status, slug=None):
    q = _load()
    it = _find(q, qid)
    if not it:
        print("no such id: " + qid); return 1
    it["status"] = status
    if slug:
        it["slug"] = slug
    _save(q)
    print("%s -> %s%s" % (qid, status, (" (" + slug + ")") if slug else ""))
    return 0


def drop(qid):
    q = _load()
    n = len(q["items"])
    q["items"] = [it for it in q["items"] if it["id"] != qid]
    _save(q)
    print("dropped " + qid if len(q["items"]) < n else "no such id: " + qid)


def main(argv):
    if not argv:
        print(__doc__); return 0
    c = argv[0]
    if c == "add" and len(argv) > 1:
        add(" ".join(argv[1:])); return 0
    if c == "list":
        cmd_list(); return 0
    if c == "next":
        cmd_next(); return 0
    if c == "start" and len(argv) > 1:
        return set_status(argv[1], "in_progress")
    if c == "done" and len(argv) > 1:
        return set_status(argv[1], "done", argv[2] if len(argv) > 2 else None)
    if c == "drop" and len(argv) > 1:
        drop(argv[1]); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
