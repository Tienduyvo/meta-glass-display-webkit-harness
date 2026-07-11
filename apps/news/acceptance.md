# News — acceptance criteria

## Definition (from the Define round, WhatsApp 2026-07-11)
A **Claude-as-backend news app**: the user states interests ("stocks", "football"), Claude's
pipeline (`tools/news_pipeline.py`) fetches, curates and pushes items into a read-only feed;
the UI renders **widget templates** per section. Owner's sourcing order is tiered:
**1) free APIs / RSS / MCP → 2) script scraping (trafilatura) → 3) real browser (Chrome
extension, manual by Claude)**. UI ships **polished templates to populate** (ticker strip,
headline list, summary cards, hero) but stays **free to compose** — a section's look is data
(`template` field), new looks are a small edit to `control.html`, never a rebuild.

- **One item holds:** `tag` (short badge, e.g. `TICK ▲2.1%`), `headline`, `summary`, `price`,
  `source`, `url` (link), `section`, `template`, `rank`. Data comes from the pipeline
  (Yahoo/Google RSS keyless; Finnhub if key present; trafilatura fallback for thin summaries).
- **Consuming moment:** glance-while-busy (glasses: morning coffee, walking) + phone browse.
  Authoring = talking to Claude (WhatsApp/desk): "track football" edits `interests.json`.
- **Key action:** glance tag+headline; Enter → summary + ▶ Open article; ✓ mark read, ★ save.
- **Trackers are user-buildable:** one section per interest in `apps/news/interests.json`
  (name, template, tickers?, query). Adding an interest = adding one JSON entry (Claude does
  it on request). A **Discover** section always appends trending stories + related topics
  outside the trackers ("appetite").
- **Refresh:** pipeline runs morning + evening + on demand (Claude-triggered); the app
  re-fetches every 60 s while open.

## Assumptions (stated, not asked)
- Start sections: **Stocks** (ticker template, a few major tickers until the owner names his),
  **Markets** (headline template), **Discover** (auto). Owner renames/extends by chat.
- Prices from Yahoo's keyless quote endpoint; if unreachable, tag falls back to the plain
  ticker symbol (no blank badges).
- Tier 3 (Chrome) is not scripted in the pipeline — Claude drives it interactively when
  tiers 1–2 fail for a source.

## Surface plan
- **Glasses** (600×600 additive, D-pad): the generic read-only list — `tag` renders BIG
  (badge), headline beside it; Enter → detail with summary, price, source, focusable
  **▶ Open**; ✓/★ from the detail actions. Bright accents on transparent black; no typing.
  **Empty state:** launcher's built-in hint (fed-from-phone/PC message) — and the pipeline
  seeds content at build time so a real user lands on a filled feed.
- **Mobile (phone):** `control.html` — the **widget dashboard**. Sections in `rank` order,
  each rendered by its template: `ticker` (price chips + compact headlines), `headline`
  (rows with tag chip, source, unread dot), `summary` (cards with the summary paragraph),
  `hero` (big top story + rows). Tap = open article; ✓ mark read; ★ save. Auto-refresh 60 s.
  **Empty state:** a card saying news comes from the pipeline — "ask Claude for a news
  update (WhatsApp works) or run `python tools/news_pipeline.py --push`".
- **Desktop (PC/agent):** the pipeline itself — `python tools/news_pipeline.py` fetches +
  curates + `--push`es (or `--out staging.json` for Claude to hand-curate first). Same
  dashboard as mobile in a browser.

## Given / when / then
- **Given** `interests.json` has a Stocks section with tickers, **when** the pipeline runs
  with `--push`, **then** the `news` collection holds ≤ `max_per_section` items per section,
  each with non-empty `tag`, `headline`, `url`, `section`, `template`, `rank`, deduped by
  headline, and the feed replaces stale rows (`--replace`).
- **Given** the collection has items, **when** the phone opens News from the launcher,
  **then** `control.html` opens (creds carried in the hash), groups by section, renders each
  section with its named template, unknown template names fall back to `headline` (never a
  blank section).
- **Given** the collection has items, **when** the glasses open News, **then** the list shows
  tag (big) + headline per row, Enter opens the detail with summary and a working ▶ Open,
  ✓/★ round-trip to the API.
- **Given** an empty collection, **when** either surface opens, **then** a bright, worded
  empty state tells the user how content arrives (never a blank view).
- **Given** the owner says "track football", **when** Claude adds a section
  `{"name":"Football","template":"headline","query":"football bundesliga"}` and re-runs the
  pipeline, **then** a Football section appears on both surfaces with no code change.
- **Given** the pipeline runs, **then** a Discover section exists with trending items
  (and related-topic suggestions) even when no tracker matches them.
