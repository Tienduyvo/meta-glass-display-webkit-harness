# Audiobooks — acceptance criteria

## Definition (desk Define round, 2026-07-11 — assumptions stated, owner said "go")
Long-form listening app, deliberately SEPARATE from Podcasts: books are sequential works
where **resume is the whole UX**, not an episodic feed (no 75/25 discovery quota — books
are deliberate choices). Sources: the open ecosystem only — **LibriVox** (keyless API,
public-domain classics, per-book RSS feeds with MP3 chapter enclosures) and any
podcast-serialized fiction; Audible/commercial DRM stays out of scope (native Audible
integration is the route for purchased books). Self-hosted personal files: deferred
until asked.

- **One item = one BOOK** (not chapters): `title`, `author`, `cover` (image), `about`,
  `chapter` (current chapter label), `audio` (current chapter's MP3 URL), `progress`
  ("7/22"), `total` (runtime), `chapters` (JSON array of {t,u} — the whole book),
  `pos` (seconds into the current chapter), `section`, `rank`.
- **Progress is sacred:** the pipeline PRESERVES `audio/chapter/progress/pos/seen/fav`
  for books already in the collection on every re-run — an update must never reset a
  half-read book.
- **Books come from the PRIVATE profile** (scope `audiobooks`); the committed
  `books.json` is a generic classics template (repo stays template-level).

## Surface plan
- **Glasses**: list rows — `progress` renders BIG ("7/22"), book title beside it;
  Enter → cover, author, current chapter, **🔊 Play / pause** (streams the current
  chapter; chapter-granular resume — starts the chapter at 0:00), readable About.
  ✓ finished / ★ / ✕ remove. **Empty state**: launcher hint + template seed.
- **Mobile**: `control.html` — book cards (cover, author, progress bar, current
  chapter), ▶ resumes at the exact saved second; expandable chapter list (tap any
  chapter to jump); **auto-advance** to the next chapter on end (PATCHes the book row);
  persistent bottom player shared pattern with Podcasts. **Empty state**: "ask Claude
  to add books or run `python tools/book_pipeline.py --push`".
- **Desktop**: the pipeline (on demand / scheduled); same dashboard.

## Given / when / then
- **Given** the profile lists books, **when** the pipeline runs with `--push`, **then**
  the `audiobooks` collection holds one row per book with non-empty `title`, `audio`
  (https MP3), `chapters` (≥1), `progress` "1/N" for new books — and **unchanged**
  `chapter/progress/pos` for books that already existed.
- **Given** books exist, **when** the glasses open Audiobooks, **then** rows show
  progress big + title, Enter → detail with cover and a working 🔊 Play / pause.
- **Given** the dashboard plays a chapter to its end, **then** the app advances to the
  next chapter, PATCHes `audio/chapter/progress/pos`, and keeps playing; pausing saves
  `pos` and replay resumes there.
- **Given** an empty collection, **then** both surfaces show worded empty states.
- **Given** a committable seed is needed, **then** it is generated with `--template`.
