# -*- coding: utf-8 -*-
"""Meme pipeline — reddit-lane data layer for the Memes app (sources live-tested 2026-07-11).

Primary: meme-api.com (keyless wrapper over Reddit) — per-community image posts with
upvote counts (the popularity signal). Backup: the open Lemmy API. NSFW/spoiler posts
are dropped. Reddit direct 403s keyless robots; 9GAG/iFunny have no usable door
(bridges tested dead); Imgur/Giphy are optional key-based add-ons later.

Communities come from the PRIVATE profile (scope `memes`); `apps/memes/communities.json`
is the generic template. Standing 75/25 rule: ~75% the user's humor, ~25% a "Viral"
slice from the general pool.

Usage:
  python tools/meme_pipeline.py --push
  python tools/meme_pipeline.py --template --out apps/memes/seed.json
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "apps", "memes", "communities.json")
UA = {"User-Agent": "meta-glass-memes/1.0 (personal display)"}
IMG_RX = re.compile(r"\.(png|jpe?g|gif|webp)(\?|$)", re.I)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def get_json(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def memeapi(community, n):
    """meme-api.com/gimme/<sub>/<n> -> [{title, image, ups, community}] (nsfw filtered)."""
    try:
        d = get_json("https://meme-api.com/gimme/%s/%d" % (community, n))
        out = []
        for m in d.get("memes", []) or ([d] if d.get("url") else []):
            if m.get("nsfw") or m.get("spoiler"):
                continue
            if not IMG_RX.search(m.get("url", "")):
                continue
            out.append({"title": m.get("title", ""), "image": m["url"],
                        "ups": int(m.get("ups") or 0), "community": "r/" + community})
        return out
    except Exception:
        return []


def lemmy(community_at_instance, n):
    """Open Lemmy API backup: community@instance -> image posts with scores."""
    try:
        comm, inst = community_at_instance.split("@", 1)
        d = get_json("https://%s/api/v3/post/list?community_name=%s&sort=TopDay&limit=%d"
                     % (inst if "." in inst else "lemmy.world",
                        community_at_instance, n))
        out = []
        for p in d.get("posts", []):
            post, url = p.get("post", {}), (p.get("post", {}).get("url") or "")
            if post.get("nsfw") or not IMG_RX.search(url):
                continue
            out.append({"title": post.get("name", ""), "image": url,
                        "ups": int(p.get("counts", {}).get("score") or 0),
                        "community": community_at_instance})
        return out
    except Exception:
        return []


def load_config(template):
    cfg = None
    if not template:
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            import profile as _profile
            cfg = _profile.get_scope("memes")
            if cfg:
                print("meme_pipeline: communities from the private profile")
        except Exception:
            cfg = None
    else:
        print("meme_pipeline: TEMPLATE mode (profile ignored — safe for committable output)")
    if not cfg:
        cfg = json.load(open(TEMPLATE, encoding="utf-8"))
        print("meme_pipeline: communities from the default template")
    return cfg


def build_items(cfg):
    per = int(cfg.get("per_community", 4))
    seen, mine = set(), []

    def add(bucket, raws, section):
        for m in raws:
            key = hashlib.md5(m["image"].encode()).hexdigest()[:12]
            if key in seen or not m["title"]:
                continue
            seen.add(key)
            m.update({"id": "m_" + key, "image": m["image"].replace("http://", "https://"),
                      "section": section, "template": "meme", "rank": 0})
            bucket.append(m)

    for c in cfg.get("communities", []):
        raws = memeapi(c, per)
        add(mine, raws, "My humor")
        print("  community r/%-22s -> %d meme(s)" % (c, len(raws)))
    for lc in cfg.get("lemmy", []) or []:
        raws = lemmy(lc, per)
        add(mine, raws, "My humor")
        print("  lemmy %-26s -> %d meme(s)" % (lc, len(raws)))

    mine.sort(key=lambda m: -m["ups"])

    ratio = float(cfg.get("discovery_ratio", 0.25) or 0.25)
    target = max(1, round(len(mine) * ratio / (1 - ratio))) if mine else 4
    viral = []
    for vc in cfg.get("viral_pool", ["memes"]):
        if len(viral) >= target:
            break
        add(viral, memeapi(vc, target), "Viral")
    viral.sort(key=lambda m: -m["ups"])
    viral = viral[:target]
    print("  feed mix: %d my humor + %d viral (target %.0f%%)"
          % (len(mine), len(viral), ratio * 100))

    items = mine + viral
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
        print("usage: meme_pipeline.py [--template] [--out FILE] [--push]"); return 2

    cfg = load_config(template)
    print("meme_pipeline: fetching…")
    items = build_items(cfg)
    print("  total: %d meme(s)" % len(items))
    if not items:
        print("nothing fetched — check the network / communities config"); return 1
    if out:
        tmp = out + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=1)
        os.replace(tmp, out)
        print("wrote %s" % out)
    if push:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push as pushmod
        return pushmod.main(["memes", "--replace", "--items", json.dumps(items)])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
