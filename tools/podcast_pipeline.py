# -*- coding: utf-8 -*-
"""Podcast pipeline — Claude-as-backend data layer for the Podcasts app.

Open-ecosystem only (owner decision 2026-07-11): show names resolve to their PUBLIC RSS
feeds via the keyless iTunes Search API; episodes (direct MP3 enclosure + show notes)
come from the shows' own feeds; the discovery slice comes from Apple's free top-podcasts
charts. No Spotify/Amazon (walled gardens). Audio is never stored — it streams from the
publisher at play time.

Personalization: the PRIVATE profile scope `podcasts` (tools/profile.py — AI-interviewed)
holds the user's shows; `apps/podcasts/shows.json` is the generic fallback template.
The standing feed-mix rule applies: ~75% the user's shows, ~25% charts discovery
(`discovery_ratio` overridable in the profile).

Usage:
  python tools/podcast_pipeline.py --push                  # personal feed -> live
  python tools/podcast_pipeline.py --out exports/pods.json # stage a personal run
  python tools/podcast_pipeline.py --template --out apps/podcasts/seed.json
      # TEMPLATE run (profile ignored) — the only mode for committable artifacts
"""
import json
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "apps", "podcasts", "shows.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; meta-glass-podcasts/1.0)"}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_tags(s):
    import html as _html
    # unwrap CDATA first — `<[^>]+>` would otherwise swallow `<![CDATA[text]]>`
    # whole, text included (bug found on the AI Daily Brief feed: 1030 episodes, 0 parsed)
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"[ \t]+", " ", _html.unescape(s)).strip()


def clip(s, n=3000):
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return cut[: cut.rfind(" ")] + "…" if " " in cut else cut + "…"


def _tag(block, names):
    for t in names:
        m = re.search(r"<%s(?:\s[^>]*)?>(.*?)</%s>" % (t, t), block, re.S | re.I)
        if m:
            return m.group(1).strip()
    return ""


def resolve_show(name_or_url):
    """Show name/feed-URL -> (title, feedUrl, artUrl). iTunes Search is the phone book;
    the feed itself is the show's own (no Apple dependence for content)."""
    if name_or_url.startswith("http"):
        return name_or_url, name_or_url, ""
    try:
        d = json.loads(fetch("https://itunes.apple.com/search?media=podcast&limit=1&term="
                             + urllib.parse.quote(name_or_url)))
        r = (d.get("results") or [{}])[0]
        return (r.get("collectionName", name_or_url), r.get("feedUrl", ""),
                r.get("artworkUrl600", "") or r.get("artworkUrl100", ""))
    except Exception:
        return name_or_url, "", ""


def _fmt_duration(raw):
    raw = (raw or "").strip()
    if raw.isdigit():                       # seconds
        m = int(raw) // 60
        return "%dh%02dm" % (m // 60, m % 60) if m >= 60 else "%dm" % m
    return raw                              # already hh:mm:ss-ish (or empty)


def feed_episodes(feed_url, show_title, art, limit):
    """Newest episodes with a direct audio enclosure."""
    try:
        x = fetch(feed_url).decode("utf-8", "replace")
    except Exception:
        return []
    # channel-level artwork fallback
    if not art:
        m = re.search(r'<itunes:image[^>]*href="([^"]+)"', x)
        art = m.group(1) if m else ""
    out = []
    for block in x.split("<item")[1:]:
        if len(out) >= limit:
            break
        block = block.split("</item>")[0]
        enc = re.search(r'<enclosure[^>]*url="([^"]+)"', block)
        title = strip_tags(_tag(block, ("title",)))
        if not enc or not title:
            continue
        notes = clip(strip_tags(_tag(block, ("content:encoded", "description",
                                             "itunes:summary"))))
        out.append({
            "show": show_title, "title": title, "notes": notes,
            "audio": enc.group(1).replace("http://", "https://"),
            "duration": _fmt_duration(_tag(block, ("itunes:duration",))),
            "published": strip_tags(_tag(block, ("pubDate",)))[:16],
            "image": art.replace("http://", "https://"),
        })
    return out


def chart_shows(storefront, limit):
    """Apple top-podcasts chart (keyless JSON) -> [(name, feedUrl, art)] via lookup."""
    try:
        d = json.loads(fetch("https://rss.marketingtools.apple.com/api/v2/%s/podcasts/"
                             "top/%d/podcasts.json" % (storefront, limit)))
        out = []
        for e in d.get("feed", {}).get("results", []):
            try:
                lk = json.loads(fetch("https://itunes.apple.com/lookup?id=" + e["id"]))
                r = (lk.get("results") or [{}])[0]
                if r.get("feedUrl"):
                    out.append((e.get("name", ""), r["feedUrl"],
                                e.get("artworkUrl100", "").replace("100x100", "600x600")))
            except Exception:
                continue
        return out
    except Exception:
        return []


def load_config(template):
    cfg = None
    if not template:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import profile as _profile
            cfg = _profile.get_scope("podcasts")
            if cfg:
                print("podcast_pipeline: shows from the private profile")
        except Exception:
            cfg = None
    else:
        print("podcast_pipeline: TEMPLATE mode (profile ignored — safe for committable output)")
    if not cfg:
        cfg = json.load(open(TEMPLATE, encoding="utf-8"))
        print("podcast_pipeline: shows from the default template")
    return cfg


def build_items(cfg):
    import hashlib
    per = int(cfg.get("episodes_per_show", 2))
    items, seen = [], set()

    def add(eps, section):
        for e in eps:
            key = re.sub(r"\W+", "", (e["show"] + e["title"]).lower())[:90]
            if key in seen:
                continue
            seen.add(key)
            e.update({"id": "p_" + hashlib.md5((e["show"] + "|" + e["title"])
                                               .encode()).hexdigest()[:12],
                      "section": section, "template": "episode", "rank": 0, "pos": 0})
            items.append(e)

    for s in cfg.get("shows", []):
        title, feed, art = resolve_show(s)
        if not feed:
            print("  ! could not resolve show: %s" % s)
            continue
        eps = feed_episodes(feed, title, art, per)
        add(eps, "My shows")
        print("  show %-32s -> %d episode(s)" % (title[:32], len(eps)))

    # discovery: latest episode of charting shows, excluding ones already followed
    ratio = float(cfg.get("discovery_ratio", 0.25) or 0.25)
    have = len(items)
    target = max(1, round(have * ratio / (1 - ratio))) if have else 3
    followed = {i["show"] for i in items}
    for name, feed, art in chart_shows((cfg.get("charts") or ["us"])[0], target + 4):
        if len([i for i in items if i["section"] == "Discover"]) >= target:
            break
        if name in followed:
            continue
        add(feed_episodes(feed, name, art, 1), "Discover")
    print("  feed mix: %d my shows + %d discovery (target %.0f%%)"
          % (have, len(items) - have, ratio * 100))

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
        print("usage: podcast_pipeline.py [--template] [--out FILE] [--push]"); return 2

    cfg = load_config(template)
    print("podcast_pipeline: fetching…")
    items = build_items(cfg)
    print("  total: %d episode(s)" % len(items))
    if not items:
        print("nothing fetched — check the network / shows config"); return 1
    if out:
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out)
        print("wrote %s" % out)
    if push:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push as pushmod
        return pushmod.main(["podcasts", "--replace", "--items", json.dumps(items)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
