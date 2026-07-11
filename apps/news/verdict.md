# News — evaluation verdict (2026-07-11)

## HARD gate — flowtest
PASS — all assertions green against local `wrangler dev` (item appears, all 9 fields
round-trip, check/fav persist, bulk replace persists, soft-delete hides, bulk upsert
un-deletes).

## SOFT gate — agent-judge (headless Edge screenshots, filled + empty states)
- [x] Pipeline fills sections from interests.json — SectionA (one per ticker, live quote
      tags like `TICK ▲2.1%`), Markets 6, Discover 4; 14 items, 14 unique ids, deduped,
      `--replace` semantics confirmed by the flowtest.
- [x] Phone opens `control.html` from the launcher (creds in hash): sections render with
      their templates — Stocks as `ticker` (price chips green/red + tagged rows), Markets
      as `hero` (big top story + rows), Discover as `headline`. Unknown template falls
      back to `headline` (code path; sections never blank).
- [x] Glasses list: tag renders BIG (badge), headline beside; Enter → detail with
      headline, summary, price, source, focusable **▶ Open Article**, ✓ Check off,
      ★ Favorite — all D-pad reachable. Additive-safe styling (bright on black).
- [x] STANDING — EMPTY STATE: glasses show the launcher's worded hint (never blank);
      phone dashboard shows its own card ("No news yet… ask Claude for a news update or
      run `python tools/news_pipeline.py --push`").
- [x] "track football" flow: a query section is exactly the Markets code path (proven);
      adding one interests.json entry creates the section — no code change.
- [x] Discover section present with trending stories outside the trackers.

## Fixes made during evaluation
1. Per-slot item ids (section+tag+url) — tickers sharing one story no longer collapse
   on bulk upsert (was: 14 pushed → 12 rows).
2. Google News " - Source" suffix stripped from headlines when a `<source>` tag exists.
3. Echo summaries (description == headline) dropped instead of doubling the hero card.

**Overall: PASS** (both halves green).

## Addendum 2026-07-11 (later session work, re-judged from screenshots)
- [x] Generic viz primitives (owner rule: generic, not domain widgets): items may carry
      `viz` JSON — `series` → inline SVG line chart, `pairs` → board rows, `stat` → big
      readout; every template renders it. First producer: tickers attach a day series
      (Yahoo closes); chart color follows `delta` so it always matches the ▲/▼ tag
      (screenshot-verified after fixing an intraday-direction mismatch on TICK).
- [x] GlassKit-language restyle applies to the dashboard's surfaces implicitly (launcher
      files) — launcher grid re-screenshot on glasses: 6-tile pages with page indicator,
      nothing clipped.
- [x] Dismiss-and-backfill: ✕ on every story soft-deletes it; sections show a top-6 cap
      over a pipeline-fetched reserve (+4/section), so a fresh story fills in instantly
      (Playwright-asserted: hero dismissed → count stays 6, new headline promoted;
      deletions survive refresh via the flowtest's soft-delete assertion).
- [x] Pictures: Bing News RSS (mkt=en-US) provides per-story thumbnails + direct
      publisher URLs (Google redirects hide og:image; GDELT 429s) — ~14/31 items carry
      an https image; hero/card/thumb rendering screenshot-verified, `onerror` hides
      broken images, glasses detail shows the photo via the `image` field type.

<!-- Share-asked: the star/share/contribute hand-off was made to the user (loop SHARE step). -->
