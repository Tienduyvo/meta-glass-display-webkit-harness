# Memes — acceptance criteria

## Definition (WhatsApp Define round, 2026-07-11 — sources live-tested before build)
A meme feed that flips FULLSCREEN on the glasses (the wallpaper pattern: land in the
image, ↑↓ next/prev, → throws it away) — humor from the user's world plus the standing
**75/25 viral mix**. Sources (tested): **meme-api.com** (keyless Reddit lane: per-community
posts with upvote counts + direct images) with **Lemmy** (open API) as backup; 9GAG/iFunny
ruled out (no API, bridges dead — tested), Imgur/Giphy are later key-based add-ons.

- **One item = one meme:** `title`, `image` (direct URL), `ups` (upvote count — the
  popularity signal), `community`, `section` ("My humor" / "Viral"), `rank`, `template`.
- **NSFW/spoiler posts are filtered out** at the pipeline (the API flags them).
- **Communities come from the PRIVATE profile** (scope `memes`); the committed
  `communities.json` is a generic template. Profile-seeded from his world (programmer/
  science humor) — corrected by chat.
- **No control page in v1**: the generic launcher covers both surfaces (phone = list
  with thumbnails + detail; glasses = fullscreen flip). A dashboard is phase 2 if asked.

## Surface plan
- **Glasses** (fullscreen app): opening lands straight in the newest meme full-bleed;
  ↑↓ flip prev/next, **→ dismisses** (delete + next), ← exits; foot shows n/N. Bright
  meme images read well on the additive display. **Empty state:** the launcher's
  fullscreen empty hint ("send one from your phone…" pattern) + template seed content.
- **Mobile (phone):** generic list — `ups` renders big (badge), title beside, thumbnail
  detail with ✓/★/🗑; add bar hidden (readOnly).
- **Desktop (PC/agent):** `python tools/meme_pipeline.py --push` (scheduled + on
  demand).

## Given / when / then
- **Given** the profile lists communities, **when** the pipeline runs with `--push`,
  **then** the `memes` collection holds top-upvoted image posts per community plus a
  ~25% "Viral" slice from the general pool, all with non-empty `title`, `image`
  (https), `ups`, `community`, deduped, nsfw filtered, `--replace` semantics.
- **Given** memes exist, **when** the glasses open Memes, **then** the view lands
  fullscreen in the first meme; ↓ shows the next, → deletes and advances.
- **Given** memes exist, **when** the phone opens Memes, **then** the list shows ups
  (big) + title, detail renders the image full-width.
- **Given** an empty collection, **then** both surfaces show worded empty states.
- **Given** a committable seed is needed, **then** `--template` mode generates it
  (generic communities, profile ignored).
