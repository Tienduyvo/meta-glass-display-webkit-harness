# Memes — evaluation verdict (2026-07-11)

## HARD gate — flowtest
PASS — all assertions green against local `wrangler dev` (feed via bulk, all fields
round-trip, check/fav persist, delete removes, bulk replace, soft-delete + un-delete).

## SOFT gate — agent-judge (DOM assertions on the running app; template-level data)
- [x] Pipeline (sources live-tested before build): meme-api.com per community with real
      upvote counts + direct images, Lemmy backup, NSFW/spoiler filtered, image-URL
      gate; standing 75/25 mix (template run: 12 my humor + 4 viral = exactly 25%);
      upvote-sorted within sections.
- [x] Glasses: fullscreen app — opening lands straight in the meme full-bleed (image
      asserted), ↓ flips to the next (foot 1/16 → 2/16), **→ dismisses and advances**
      (16 → 15 asserted), ← exits.
- [x] Phone: generic list — `ups` renders big (badge), title beside, image detail.
- [x] STANDING — EMPTY STATE: launcher's built-in fullscreen/readOnly hints; template
      seed ships content.
- [x] Repo stays template-level: `communities.json`/`seed.json` generic; his real
      communities (programmer/science humor) live in the private profile scope.

## Known limits (stated in acceptance)
- meme-api.com is community-run (dependency risk) — Lemmy is the warm backup; Imgur/
  Giphy possible later with free keys; 9GAG/iFunny have no viable door (tested).

**Overall: PASS** (both halves green).

<!-- Share-asked: the star/share/contribute hand-off was made to the user (loop SHARE step). -->
