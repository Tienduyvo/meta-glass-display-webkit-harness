# Daily Ritual — acceptance criteria

**What it is:** a morning/evening companion in one list. In the **morning** you glance
affirmations and open guided video/audio ("programming") hands-free on the glasses while
getting ready. At **night** you review what you typed you're grateful for. All authoring
(new affirmations, media links, gratitude entries, edits) happens on phone/desktop.

## Definition (user-answered, 2026-07-09)

1. *Structure?* → **One combined app** — every item carries a `slot` tag
   (🌅 Morning / 🌙 Night); the list sorts Morning first, so the ritual reads top-down.
2. *Content source?* → **Seeded starter pack** — curated affirmations plus **embedded
   ~2-minute audio programs** (self-hosted TTS under `/media/`, `audio` field) so it works
   on day one; the user adds/replaces their own from the phone. **The whole ritual is a
   couple of minutes, not half an hour** (user feedback 2026-07-09): no long YouTube
   compilations in the seed. On-device testing confirmed YouTube doesn't open from the
   glasses webview anyway (device limitation) — `media` links the user adds are a
   phone-side extra.
3. *Surfaces?* → **Glasses for consuming both rituals** (morning affirmations + play links,
   night gratitude review); **mobile/desktop only for adding content and settings**.

## Surface plan

- **Glasses (consuming, both rituals):** the row shows the affirmation/gratitude text BIG
  and bright with the small 🌅/🌙 tag above it; D-pad ↓ walks the ritual top-down
  (Morning group first). Enter opens the detail card; items with a media link show
  **▶ Open Play** — Enter launches the video/audio. Check = "done today", ★ = favorite.
  No typing on this surface.
- **Mobile (authoring):** the add bar creates items — type the text, optionally paste a
  YouTube/audio URL, keep or change the default 🌅 Morning tag (type 🌙 Night for evening
  gratitude). Nightly gratitude is typed here in the moment, then reviewed on the glasses.
- **Desktop (bulk):** same UI; also the seed path — `tools/push.py daily_ritual --file
  apps/daily-ritual/seed.json` feeds the starter pack in one call. No readOnly/push-only
  feed needed beyond that — skipped, the app is user-authored.

## Assumptions (defaulted, not asked)

- One list, grouped by sorting on `slot` ascending ("🌅 Morning" < "🌙 Night" as strings);
  no time-of-day auto-switching — the user scrolls to their ritual.
- `check` means "done today"; it is a persistent flag the user may clear or ignore —
  no automatic daily reset in this first increment.
- Media plays via the launcher's ▶ Open link behavior (device-limited playback — treat
  as "open a link", per the kit's video rule).
- Seed media links are verified live (YouTube oEmbed 200) at build time.

## Flow (given / when / then)

- **Given** the seeded app on the glasses in the morning, **when** I open Daily Ritual,
  **then** 🌅 Morning items are at the top, the affirmation text is the big bright element
  of each row, and D-pad ↓ walks them in order.
- **Given** an affirmation with a media link, **when** I press Enter on it and choose
  **▶ Open Play**, **then** the video/audio URL opens.
- **Given** an item with an `audio` field (direct .wav/.mp3 URL, e.g. the seeded
  self-hosted sample), **when** I open its detail, **then** an inline audio player
  renders on phone/desktop and a **🔊 Play / pause** action is reachable by D-pad on
  the glasses — playback without leaving the app.
- **Given** any surface with an empty collection, **when** the app opens, **then** a
  bright "Nothing here yet" hint says what to do next (add on phone) — never a blank view.
- **Given** the add bar on the phone, **when** I type a gratitude line and set the tag to
  🌙 Night, **then** it appears in the Night group on all surfaces.
- **Given** an item with no media link, **when** I open its detail, **then** no ▶ Open
  action is shown (no broken affordance).
- **Given** any item, **when** I check it on the glasses, **then** the check state
  persists and syncs to phone/desktop.
- **Given** the seed file, **when** `tools/push.py daily_ritual --file seed.json` runs,
  **then** all starter items land in the collection and render in the launcher.

## Out of scope (first increment)

- Automatic daily reset of check-offs and time-of-day auto-switching (morning vs night
  view) — revisit after real use.
- In-app audio playback / a media library beyond "open the link".
