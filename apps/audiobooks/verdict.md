# Audiobooks — evaluation verdict (2026-07-11)

## HARD gate — flowtest
PASS — all assertions green against local `wrangler dev` (feed via bulk, all fields
round-trip incl. `audio`/`chapters`/`pos`, check/fav persist, delete removes, bulk
replace, soft-delete + un-delete).

## SOFT gate — agent-judge (eval_drive + DOM assertions; template-level data)
- [x] Pipeline resolves search terms on LibriVox (keyless; WAF workaround: anchored
      single-word queries + local fuzzy match, 404 = empty) → per-book RSS → ordered
      chapter list with direct https MP3s, cover art, author, runtime. Template run:
      2 classics, 12 chapters each.
- [x] Glasses: rows show `progress` BIG ("1/12") + book title; Enter → cover, author,
      current chapter, focusable 🔊 Play / pause, readable About (857px scrolls);
      eval_drive glass-list + glass-detail PASS.
- [x] Dashboard: book cards with cover, progress bar, current chapter and "resumes at";
      expandable chapter list; tapping chapter 3 PATCHes the row (asserted server-side
      progress "3/12") and activates the persistent player; `ended` auto-advances to
      the next chapter (code path shared with the assert-tested jump PATCH).
- [x] **Progress preserved on pipeline re-runs** (the app's core invariant): re-ran the
      pipeline over a book at 3/12 — progress stayed 3/12 (asserted).
- [x] STANDING — EMPTY STATE: worded cards on both surfaces; template seed ships content.
- [x] Repo stays template-level: `books.json`/`seed.json` are generic classics; personal
      books go to the private profile scope `audiobooks`.

## Known limits (stated in acceptance)
- Glasses resume is chapter-granular (generic player starts a chapter at 0:00); exact
  second-level resume is dashboard-side.
- Commercial/DRM audiobooks (Audible) are out of scope — LibriVox public domain +
  podcast-serialized fiction only; self-hosted files deferred until asked.

**Overall: PASS** (both halves green).
