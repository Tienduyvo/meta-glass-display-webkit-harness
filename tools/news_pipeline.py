# -*- coding: utf-8 -*-
"""News pipeline — the Claude-as-backend data layer for the News app.

Reads the user's trackers from `apps/news/interests.json`, fetches + curates news per
section, and feeds the read-only `news` collection (via tools/push.py --replace).
Adding a tracker = adding one entry to interests.json (ask Claude: "track football").

Tiered sourcing (owner decision 2026-07-11) — cheapest first:
  1. Free APIs / RSS, no key: Yahoo Finance RSS + keyless quote endpoint per ticker,
     Google News RSS per query, Google News top stories for the Discover section.
     Finnhub company-news is used *additionally* when FINNHUB_KEY is set (env/push.env).
  2. Script extraction: if an item's summary is thin and `trafilatura` is installed,
     fetch the article and extract the first sentences (opt-in via --extract, capped).
  3. Real browser (Chrome extension): not scripted here — Claude drives it interactively
     in a desktop session when tiers 1-2 fail for a source.

Usage:
  python tools/news_pipeline.py --push               # personal feed (profile) -> live, in one go
  python tools/news_pipeline.py --out exports/f.json # stage a personal run (exports/ is git-ignored)
  python tools/news_pipeline.py --template --out apps/news/seed.json
      # TEMPLATE-LEVEL run (ignores the private profile) — the ONLY mode allowed for
      # committable artifacts (owner rule 2026-07-11: repo stays template-level; not
      # even interests may be derivable from tracked files)

Items produced (fields of apps/news/app.config.json): id (stable per URL), tag, headline,
summary, price, source, url, section, template, rank. stdlib only; trafilatura optional.
"""
import hashlib
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERESTS = os.path.join(ROOT, "apps", "news", "interests.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; meta-glass-news/1.0)"}


def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def strip_tags(s):
    # unwrap CDATA before stripping tags — otherwise `<[^>]+>` swallows a
    # `<![CDATA[text]]>` block whole, text included (regression test locks this;
    # same class of bug that blanked a 1030-item podcast feed).
    s = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", s or "", flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def clip(s, n=240):
    s = (s or "").strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    return cut[: cut.rfind(" ")] + "…" if " " in cut else cut + "…"


def parse_rss(xml_bytes, limit=10):
    """Minimal RSS 2.0 parser -> [{headline, url, summary, source, ts}]."""
    out = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    for it in root.iter("item"):
        if len(out) >= limit:
            break
        g = lambda k: (it.findtext(k) or "").strip()
        title, link = g("title"), g("link")
        if not title or not link:
            continue
        src = (it.findtext("source") or "").strip()
        # Google News titles read "Headline - Source" — strip the suffix either way.
        if not src and " - " in title:
            title, src = title.rsplit(" - ", 1)
        elif src and title.endswith(" - " + src):
            title = title[: -len(" - " + src)]
        title = strip_tags(title)
        summary = clip(strip_tags(g("description")))
        # Google News descriptions are usually just the headline again — drop the echo.
        if summary and re.sub(r"\W+", "", summary.lower()).startswith(
                re.sub(r"\W+", "", title.lower())[:60]):
            summary = ""
        out.append({"headline": title, "url": link, "summary": summary,
                    "source": src or "", "ts": g("pubDate")})
    return out


def yahoo_quote(sym):
    """Keyless quote -> (tag, price, viz). viz is the GENERIC series payload the UI's
    vizHTML renders as a line chart ({"type":"series","values":[...]}); any other data
    source can attach the same shape (or "pairs"/"stat") — content drives the UI.
    Plain symbol + no viz on failure."""
    try:
        d = json.loads(fetch("https://query1.finance.yahoo.com/v8/finance/chart/"
                             + urllib.parse.quote(sym) + "?range=1d&interval=15m"))
        res = d["chart"]["result"][0]
        meta = res["meta"]
        px = meta.get("regularMarketPrice")
        prev = meta.get("chartPreviousClose") or meta.get("previousClose")
        if px is None or not prev:
            raise ValueError
        pct = (px - prev) / prev * 100.0
        arrow = "▲" if pct >= 0 else "▼"
        chg = "%s%.1f%%" % (arrow, abs(pct))
        viz = ""
        try:
            closes = [round(c, 2) for c in res["indicators"]["quote"][0]["close"] if c]
            if len(closes) > 1:
                # delta ties the chart color to the tag's vs-previous-close direction —
                # the intraday line alone can point the other way.
                viz = json.dumps({"type": "series", "values": closes, "delta": round(pct, 2)})
        except Exception:
            pass
        return "%s %s" % (sym, chg), "%.2f %s" % (px, chg), viz
    except Exception:
        return sym, "", ""


def yahoo_news(sym, limit):
    try:
        return parse_rss(fetch("https://feeds.finance.yahoo.com/rss/2.0/headline?s="
                               + urllib.parse.quote(sym) + "&region=US&lang=en-US"), limit)
    except Exception:
        return []


def _tag(block, t):
    m = re.search(r"<%s>(.*?)</%s>" % (t, t), block, re.S)
    return html.unescape(m.group(1)).strip() if m else ""


def bing_news(query, limit):
    """Bing News RSS (mkt=en-US): unlike Google News it carries a thumbnail per item
    (News:Image) and the DIRECT publisher URL (inside the apiclick link's url= param) —
    the only keyless combo found that gives the feed real pictures (owner ask
    2026-07-11; Google redirects hide og:image, Yahoo search RSS is blocked, GDELT 429s)."""
    try:
        x = fetch("https://www.bing.com/news/search?q=" + urllib.parse.quote(query)
                  + "&format=rss&mkt=en-US").decode("utf-8", "replace")
    except Exception:
        return []
    out = []
    for block in x.split("<item>")[1:]:
        if len(out) >= limit:
            break
        block = block.split("</item>")[0]
        title, link = _tag(block, "title"), _tag(block, "link")
        m = re.search(r"[?&]url=([^&]+)", link)
        if m:
            link = urllib.parse.unquote(m.group(1))
        if not title or not link:
            continue
        img = _tag(block, "News:Image").replace("http://", "https://")
        out.append({"headline": strip_tags(title),
                    "url": link.replace("http://", "https://"),
                    "summary": clip(strip_tags(_tag(block, "description"))),
                    "source": _tag(block, "News:Source"), "ts": _tag(block, "pubDate"),
                    # https rewrite: the dashboard is served over https and http images
                    # would hit mixed-content blocking
                    "image": img + "&w=640" if img else ""})
    return out


def google_news(query, limit):
    try:
        return parse_rss(fetch("https://news.google.com/rss/search?q="
                               + urllib.parse.quote(query) + "&hl=en-US&gl=US&ceid=US:en"), limit)
    except Exception:
        return []


def google_top(limit):
    try:
        return parse_rss(fetch("https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"), limit)
    except Exception:
        return []


def finnhub_news(sym, key, limit):
    """Tier-1 extra when a key exists: Finnhub company news (last 3 days)."""
    try:
        import datetime as dt
        to = dt.date.today()
        frm = to - dt.timedelta(days=3)
        d = json.loads(fetch("https://finnhub.io/api/v1/company-news?symbol=%s&from=%s&to=%s&token=%s"
                             % (urllib.parse.quote(sym), frm, to, key)))
        return [{"headline": strip_tags(a.get("headline", "")), "url": a.get("url", ""),
                 "summary": clip(strip_tags(a.get("summary", ""))), "source": a.get("source", ""),
                 "ts": ""} for a in d[:limit] if a.get("headline") and a.get("url")]
    except Exception:
        return []


def extract_body(url):
    """Tier 2, now a standard step (owner 2026-07-11): readable story text rendered
    IN-APP on the glasses — no cookie walls, no heavy external pages. Capped for the
    600×600 reader; the ▶ Open action keeps the original as backup."""
    try:
        import trafilatura
    except ImportError:
        return ""
    try:
        text = trafilatura.extract(fetch(url, timeout=20).decode("utf-8", "replace"),
                                   include_comments=False) or ""
        # Generous cap: clipping was making stories "end with .." (owner 2026-07-11).
        # 6000 chars ships virtually every extraction whole; what still ends in "…"
        # is the SOURCE's teaser (JS-loaded articles), handled by the stub filter.
        return clip(re.sub(r"\n{2,}", "\n\n", text.strip()), 6000)
    except Exception:
        return ""


def add_bodies(items, workers=8):
    from concurrent.futures import ThreadPoolExecutor
    def one(it):
        it["body"] = extract_body(it["url"]) or it["summary"]
    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(one, items))
    print("  tier-2 story bodies: %d/%d extracted"
          % (sum(1 for i in items if i["body"] and i["body"] != i["summary"]), len(items)))


def extract_summary(url):
    """Tier 2: pull the article and let trafilatura produce a short summary."""
    try:
        import trafilatura
    except ImportError:
        return ""
    try:
        text = trafilatura.extract(fetch(url, timeout=20).decode("utf-8", "replace")) or ""
        sents = re.split(r"(?<=[.!?])\s+", text.strip())
        return clip(" ".join(sents[:2]))
    except Exception:
        return ""


def _load_env():
    """FINNHUB_KEY from env or the git-ignored push.env (same convention as push.py)."""
    for name in ("push.env", ".env"):
        p = os.path.join(ROOT, name)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() == "FINNHUB_KEY" and not os.environ.get("FINNHUB_KEY"):
                    os.environ["FINNHUB_KEY"] = v.strip().strip('"').strip("'")


def build_items(cfg, extract=False):
    per = int(cfg.get("max_per_section", 6))
    seen, items, extracted = set(), [], 0
    fh_key = os.environ.get("FINNHUB_KEY", "")

    def add(section, template, raws, tag="", price="", keyprefix="", viz=""):
        n = 0
        for r in raws:
            # Google News URLs are JS redirect shells the Meta glasses browser cannot
            # follow (device finding 2026-07-11) — skip them; only direct publisher
            # links (Bing url= param, Yahoo feeds) make it into the feed.
            if "news.google.com" in r["url"]:
                continue
            # keyprefix scopes dedupe (per ticker): Yahoo symbol feeds overlap heavily and
            # would otherwise starve later tickers of their top story (and their price chip).
            key = keyprefix + re.sub(r"\W+", "", r["headline"].lower())[:80]
            if not key or key in seen:
                continue
            seen.add(key)
            items.append({
                # id is per slot (section+tag+url), not per url: tickers can share one story
                # and identical ids would collapse into a single row on bulk upsert.
                "id": "n_" + hashlib.md5((section + "|" + tag + "|" + r["url"])
                                         .encode()).hexdigest()[:12],
                "tag": tag or (r["source"] or section)[:16],
                "headline": r["headline"], "summary": r["summary"],
                "price": price, "source": r["source"], "url": r["url"],
                "image": r.get("image", ""),
                "section": section, "template": template, "rank": 0,
                "viz": viz if n == 0 else "",  # one chart per tag, not per headline
            })
            n += 1
        return n

    sections = list(cfg.get("sections", []))
    for sec in sections:
        name, tpl = sec["name"], sec.get("template", "headline")
        got = 0
        tickers = sec.get("tickers", [])
        for sym in tickers:
            if got >= per:
                break
            tag, price, viz = yahoo_quote(sym)
            raws = yahoo_news(sym, 3)
            if fh_key:
                raws += finnhub_news(sym, fh_key, 2)
            take = max(1, per // max(1, len(tickers)))
            n = add(name, tpl, raws[:take], tag=tag, price=price, viz=viz)
            if n == 0 and raws:
                # all of this symbol's stories were cross-symbol dupes — keep its top story
                # anyway (scoped dedupe) so the ticker still shows up with its price chip
                n = add(name, tpl, raws[:1], tag=tag, price=price, keyprefix=sym + ":", viz=viz)
            got += n
        if sec.get("query") and got < per:
            # +8 reserve beyond the visible cap: backfill for dismissed (✕) stories AND
            # headroom for the stub filter (extraction fails on ~40% of pages).
            # Bing first (it has pictures + direct links), fetch 2x to maximize image coverage.
            want = per - got + 8
            raws = bing_news(sec["query"], want * 2)  # Over-fetch from Bing for more images
            if len(raws) < want:
                raws += google_news(sec["query"], want - len(raws))
            add(name, tpl, raws)
        print("  section %-12s -> %d item(s)" % (name, sum(1 for i in items if i["section"] == name)))

    disc = cfg.get("discover")
    if disc:
        n_disc = int(disc.get("max", 4)) + 3
        # Bing only (google links don't open on the glasses); one query can run thin,
        # so walk fallback queries until the section is filled.
        draws = []
        for q in ("breaking news today", "top world news", "latest news"):
            if len(draws) >= n_disc:
                break
            draws += bing_news(q, n_disc * 2)
        add(disc.get("name", "Discover"), disc.get("template", "headline"), draws)
        print("  section %-12s -> %d item(s)"
              % (disc.get("name", "Discover"),
                 sum(1 for i in items if i["section"] == disc.get("name", "Discover"))))

    if extract:
        for it in items:
            if extracted >= 6:
                break
            if len(it["summary"]) < 60:
                s = extract_summary(it["url"])
                if s:
                    it["summary"] = s
                    extracted += 1
        print("  tier-2 extraction: %d summarie(s)" % extracted)

    # Mix the interests (device finding 2026-07-11): round-robin across sections so the
    # glasses' flat list alternates topics with each section's most popular story first
    # (source order = popularity). The dashboard still groups by the `section` field.
    def _mix(lst):
        by_sec, order = {}, []
        for it in lst:
            by_sec.setdefault(it["section"], []).append(it)
            if it["section"] not in order:
                order.append(it["section"])
        mixed = []
        while any(by_sec.values()):
            for s in order:
                if by_sec[s]:
                    mixed.append(by_sec[s].pop(0))
        return mixed

    items = _mix(items)

    add_bodies(items)
    # The in-app text IS the article on the glasses (no Open fallback there), so a stub
    # story is a dead end (device finding 2026-07-11): drop items whose extraction came
    # back too short — except chart items (tickers), whose value is the quote + viz.
    MIN_BODY = 400
    before = len(items)

    def readable(it):
        b = it.get("body", "")
        if it.get("viz"):
            return True
        if len(b) < MIN_BODY:
            return False
        # source-side teasers: short text that trails off — the site loads the real
        # article via JS, so a static fetch can never get more. Drop those too.
        return not (len(b) < 900 and b.rstrip().endswith(("…", "...", "..")))

    items = [it for it in items if readable(it)]
    if before != len(items):
        print("  dropped %d stub stor(ies) (body < %d chars, no chart)" % (before - len(items), MIN_BODY))

    # Feed-mix rule (owner 2026-07-11): the final feed is ~25% popular/viral discovery,
    # ~75% profile-driven (ratio overridable per profile via "discovery_ratio").
    ratio = float(cfg.get("discovery_ratio", 0.25) or 0.25)
    disc_name = (cfg.get("discover") or {}).get("name", "Discover")
    prof = [it for it in items if it["section"] != disc_name]
    disc = [it for it in items if it["section"] == disc_name]
    target = max(2, round(len(prof) * ratio / (1 - ratio)))
    disc = disc[:target]
    print("  feed mix: %d profile + %d discovery (target %.0f%%)"
          % (len(prof), len(disc), ratio * 100))
    items = _mix(prof + disc)

    for i, it in enumerate(items):
        it["rank"] = i + 1
    return items


def main(argv):
    out, push, extract, template = "", False, False, False
    i = 0
    while i < len(argv):
        if argv[i] == "--out" and i + 1 < len(argv):
            out = argv[i + 1]; i += 2
        elif argv[i] == "--push":
            push = True; i += 1
        elif argv[i] == "--extract":
            extract = True; i += 1
        elif argv[i] == "--template":
            template = True; i += 1
        elif argv[i] in ("-h", "--help"):
            print(__doc__); return 0
        else:
            i += 1
    if not out and not push:
        print("usage: news_pipeline.py [--out FILE] [--push] [--extract]"); return 2

    _load_env()
    # Personalization comes from the PRIVATE profile (D1 `profile` collection, scope
    # "news" — filled by AI interview, never committed); the repo's interests.json is
    # only the non-personal default template for fresh forks.
    cfg = None
    if not template:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import profile as _profile
            cfg = _profile.get_scope("news")
            if cfg:
                print("news_pipeline: interests from the private profile")
        except Exception:
            cfg = None
    else:
        print("news_pipeline: TEMPLATE mode (profile ignored — safe for committable output)")
    if not cfg:
        cfg = json.load(open(INTERESTS, encoding="utf-8"))
        print("news_pipeline: interests from the default template (no profile yet)")
    print("news_pipeline: fetching…")
    items = build_items(cfg, extract=extract)
    print("  total: %d item(s)" % len(items))
    if not items:
        print("nothing fetched — check the network / interests.json"); return 1

    if out:
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out)
        print("wrote %s (push: python tools/push.py news --replace --file %s)" % (out, out))
    if push:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push as pushmod
        return pushmod.main(["news", "--replace", "--items", json.dumps(items)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
