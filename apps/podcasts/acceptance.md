# Podcasts — acceptance criteria

## Definition (from the WhatsApp Define round, 2026-07-11)
A **Claude-as-backend podcast app** on the open podcasting ecosystem — no walled gardens.
The pipeline (`tools/podcast_pipeline.py`) resolves the user's shows to their public RSS
feeds, pulls the newest episodes (direct MP3 enclosure + show notes), mixes in popular/
discovery episodes (the standing **75% profile / 25% discovery** rule), and pushes a
read-only `podcasts` feed. Playback streams straight from the publisher — nothing stored.
Market context: no third-party podcast app exists for the Meta display yet (platform
opened 2026-05); the plumbing (RSS, iTunes search, Apple charts, Podcast Index) is
commodity — the glasses surface is the new part.

- **One item holds:** `show` (badge), `title`, `notes` (readable show notes, like the
  news reader), `audio` (direct MP3 enclosure URL — the launcher's `audio` field type),
  `duration`, `published`, `image` (episode/show art), `section` ("My shows"/"Discover"),
  `template`, `rank`.
- **Sources (tier 1, keyless):** show name → feed via iTunes Search API; episodes from
  the show's own RSS; discovery from Apple's top-podcasts charts (DE + US) resolved back
  through iTunes lookup. Podcast Index/fyyd are drop-in alternates if Apple's lookup
  ever fails. Spotify/Amazon exclusives are explicitly out of scope.
- **Shows come from the PRIVATE profile** (scope `podcasts`; AI-interviewed). The repo
  carries only a generic template (`apps/podcasts/shows.json`) — template-level rule.
- **Consuming moment:** ears-busy/eyes-free — walks, commute, chores. Short-to-medium
  sessions on the glasses (battery ~6 h mixed use); long sessions belong to the phone.
- **Key action:** glance the episode list, Enter → show notes + ▶ play in-app; ✓ mark
  played; ★ save; ✕/→ dismiss-and-next (same gestures as News).

## Assumptions (stated, not asked)
- Until the owner names shows, the profile is seeded from his interests (IT/life
  science, German): an AI/tech show, a science show, a German news daily. He corrects
  by chat ("follow X") — one profile edit, no code.
- 2 newest episodes per show; discovery = latest episode of charting shows.
- **Playback limits (honest):** audio lives while the web app stays open; display-sleep
  behavior is UNKNOWN until the owner's on-device test (ritual-app audio + let the
  display doze) — result decides phase 2 (persistent glasses mini-player). Resume
  positions are phone-side in phase 1 (dashboard saves `pos` via PATCH); the glasses
  generic player starts episodes from the beginning.

## Surface plan
- **Glasses** (600×600, D-pad): generic read-only list — `show` renders BIG (badge),
  episode title beside it (ticker-scrolls when long); Enter → detail with episode art,
  readable show notes (scrolls like the news reader), **🔊 Play / pause** action,
  ✓/★/✕ actions; → = dismiss-and-next. **Empty state:** launcher's fed-from-PC hint +
  template seed ships content.
- **Mobile (phone):** `control.html` dashboard — episode cards (art, show chip, title,
  notes preview) grouped My shows / Discover, tap to expand notes; **persistent bottom
  player** that survives browsing (one page), with seek bar and **remembered positions**
  (PATCH `pos` every ~15 s; resume on next play, any device with the dashboard).
  **Empty state:** "ask Claude to add shows (WhatsApp works) or run
  `python tools/podcast_pipeline.py --push`".
- **Desktop (PC/agent):** the pipeline (scheduled morning/evening + on demand); same
  dashboard in a browser.

## Given / when / then
- **Given** the profile lists shows, **when** the pipeline runs with `--push`, **then**
  the `podcasts` collection holds ≤2 newest episodes per show plus ~25% discovery
  episodes, each with non-empty `show`, `title`, `audio` (direct https MP3), `notes`,
  `section`, `rank`, deduped, `--replace` semantics.
- **Given** episodes exist, **when** the glasses open Podcasts, **then** the list shows
  show-badge + title, Enter → detail with art, scrollable notes, a focusable
  **🔊 Play / pause** action that starts audio in-app, and ✓/★/✕ actions.
- **Given** episodes exist, **when** the phone opens Podcasts, **then** the dashboard
  renders episode cards with a persistent bottom player; starting an episode, browsing
  cards, and returning keeps audio playing; pausing stores the position and replaying
  resumes within ~15 s of where it stopped.
- **Given** an empty collection, **when** either surface opens, **then** a worded empty
  state explains how episodes arrive (never blank).
- **Given** the owner says "follow <show>", **when** Claude updates the profile scope and
  re-runs the pipeline, **then** the show's episodes appear — no code change.
- **Given** a committable seed is needed, **then** it is generated with `--template`
  (generic shows only — never from the profile).
