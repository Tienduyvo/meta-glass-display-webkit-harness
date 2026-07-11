# -*- coding: utf-8 -*-
"""Audiobook pipeline — LibriVox-backed data layer for the Audiobooks app.

One collection row per BOOK: the current chapter's audio URL + label + progress ride on
the row and are PATCHed forward as the user listens (dashboard auto-advance); the full
chapter list is a JSON field. **Progress is preserved on re-runs** — updating the
library must never reset a half-read book.

Sources: LibriVox keyless API (path-style params) resolves a search term to a book and
its per-book RSS feed; chapter MP3s are direct enclosures. Books come from the PRIVATE
profile (scope `audiobooks`); `apps/audiobooks/books.json` is the generic template.

Usage:
  python tools/book_pipeline.py --push                      # personal library -> live
  python tools/book_pipeline.py --template --out apps/audiobooks/seed.json
"""
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "apps", "audiobooks", "books.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; meta-glass-audiobooks/1.0)"}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def fetch(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_tags(s):
    import html as _html
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", _html.unescape(s)).strip()


def clip(s, n=900):
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return cut[: cut.rfind(" ")] + "…" if " " in cut else cut + "…"


def librivox_find(term):
    """Search term (optionally 'term|language') -> book dict or None.
    LibriVox's API 403/400s on multi-word title params (WAF), so: query by the term's
    most distinctive single word, then fuzzy-match the full term against the results."""
    lang = ""
    if "|" in term:
        term, lang = [p.strip() for p in term.split("|", 1)]
    words = re.findall(r"[A-Za-zÀ-ÿ0-9]+", term)
    if not words:
        return None
    want = {w.lower() for w in words}

    def score(b):
        have = {w.lower() for w in re.findall(r"[A-Za-zÀ-ÿ0-9]+", b.get("title", ""))}
        return len(want & have) / max(1, len(want))

    # `^word` anchors to the title START (their search has no substring mode and the
    # WAF rejects multi-word params); a query with zero hits returns 404, not [].
    # Try each word longest-first until the result set contains a good fuzzy match.
    tried = set()
    for key in sorted(words, key=len, reverse=True):
        key = key.lower()
        if key in tried or len(key) < 3:
            continue
        tried.add(key)
        try:
            d = json.loads(fetch("https://librivox.org/api/feed/audiobooks/title/%s/format/json"
                                 % urllib.parse.quote("^" + key)))
            books = d.get("books", []) or []
        except Exception:
            continue  # 404 = no titles start with this word
        if lang:
            books = [b for b in books if (b.get("language") or "").lower() == lang.lower()]
        books = [b for b in books if int(b.get("num_sections") or 0) > 0]
        books.sort(key=score, reverse=True)
        if books and score(books[0]) >= 0.5:
            return books[0]
    return None


def book_chapters(book_id):
    """Per-book RSS -> ordered [{t, u}] chapter list (+ cover from itunes:image)."""
    try:
        x = fetch("https://librivox.org/rss/%s" % book_id).decode("utf-8", "replace")
    except Exception:
        return [], ""
    m = re.search(r'<itunes:image[^>]*href="([^"]+)"', x)
    cover = (m.group(1) if m else "").replace("http://", "https://")
    out = []
    for block in x.split("<item")[1:]:
        block = block.split("</item>")[0]
        enc = re.search(r'<enclosure[^>]*url="([^"]+)"', block)
        tm = re.search(r"<title(?:\s[^>]*)?>(.*?)</title>", block, re.S | re.I)
        if not enc or not tm:
            continue
        out.append({"t": strip_tags(tm.group(1)), "u": enc.group(1).replace("http://", "https://")})
    return out, cover


def load_config(template):
    cfg = None
    if not template:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import profile as _profile
            cfg = _profile.get_scope("audiobooks")
            if cfg:
                print("book_pipeline: books from the private profile")
        except Exception:
            cfg = None
    else:
        print("book_pipeline: TEMPLATE mode (profile ignored — safe for committable output)")
    if not cfg:
        cfg = json.load(open(TEMPLATE, encoding="utf-8"))
        print("book_pipeline: books from the default template")
    return cfg


def existing_rows():
    """Current collection rows by id — progress survives every pipeline run."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push as _push
        _push._load_creds_file()
        api = os.environ.get("GLASS_API", "").rstrip("/")
        tok = os.environ.get("GLASS_TOKEN", "")
        if not api or not tok:
            return {}
        req = urllib.request.Request(api + "/audiobooks", headers={
            "Authorization": "Bearer " + tok, "User-Agent": UA["User-Agent"]})
        with urllib.request.urlopen(req, timeout=20) as r:
            return {it["id"]: it for it in json.loads(r.read()).get("items", [])}
    except Exception:
        return {}


def build_items(cfg):
    old = existing_rows()
    items = []
    for term in cfg.get("books", []):
        b = librivox_find(term)
        if not b:
            print("  ! not found on LibriVox: %s" % term)
            continue
        chapters, cover = book_chapters(b["id"])
        if not chapters:
            print("  ! no chapters for: %s" % b.get("title"))
            continue
        bid = "b_" + hashlib.md5(str(b["id"]).encode()).hexdigest()[:12]
        row = {
            "id": bid,
            "title": strip_tags(b.get("title", term)),
            "author": ", ".join(("%s %s" % (a.get("first_name", ""),
                                            a.get("last_name", ""))).strip()
                                for a in (b.get("authors") or [])),
            "cover": cover, "about": clip(strip_tags(b.get("description", ""))),
            "chapter": chapters[0]["t"], "audio": chapters[0]["u"],
            "progress": "1/%d" % len(chapters), "total": b.get("totaltime", ""),
            "chapters": json.dumps(chapters, ensure_ascii=False),
            "section": "Library", "template": "book", "rank": 0, "pos": 0,
        }
        if bid in old:  # never reset a half-read book
            for k in ("chapter", "audio", "progress", "pos", "seen", "fav"):
                if old[bid].get(k) not in (None, ""):
                    row[k] = old[bid][k]
        items.append(row)
        print("  book %-38s -> %d chapter(s), %s" % (row["title"][:38], len(chapters),
                                                     row["progress"]))
    for i, it in enumerate(items):
        it["rank"] = i + 1
    return items


def main(argv):
    out, push, template = "", False, False
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]; i += 2
        elif argv[i] == "--push":
            push = True; i += 1
        elif argv[i] == "--template":
            template = True; i += 1
        elif argv[i] in ("-h", "--help"):
            print(__doc__); return 0
        else:
            i += 1
    if not out and not push:
        print("usage: book_pipeline.py [--template] [--out FILE] [--push]"); return 2

    cfg = load_config(template)
    print("book_pipeline: fetching…")
    items = build_items(cfg)
    print("  total: %d book(s)" % len(items))
    if not items:
        print("nothing fetched — check the network / books config"); return 1
    if out:
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out)
        print("wrote %s" % out)
    if push:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push as pushmod
        return pushmod.main(["audiobooks", "--replace", "--items", json.dumps(items)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
