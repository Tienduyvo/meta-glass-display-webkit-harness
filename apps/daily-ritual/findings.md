# Daily Ritual — user findings (real-device testing)

Open `- [ ]` lines put this app in the FIX state (loop_state.py) until fixed + re-evaluated.

- [x] 2026-07-09 ▶ Open Play (YouTube) did nothing on the glasses. → Root cause 1: kit
  `openURL()` ignored blocked popups (fixed, both launchers + repro gate). Root cause 2
  (retest): the glasses webview won't open YouTube at all — device limitation. Resolved by
  embedded `audio` programs playing in-app; YouTube removed from the seed.
- [x] 2026-07-09 Ritual too long — "should be a couple of minutes, not half an hour". →
  Long YouTube compilations removed; seed = quick affirmations + ~2-min audio programs.
- [x] 2026-07-09 "2 min of only robo voice" — System.Speech TTS too robotic. → Replaced with
  real human public-domain readings (LibriVox: Invictus 1 min, If— 2 min) + neural-voice
  (edge-tts) regenerations of the three guided programs.
- [x] 2026-07-09 Sounds cut off mid-sentence on device — NOT samples: the mp3s are complete
  (0:42–1:43). Cause: `refresh: 60` re-rendered the detail view every 60 s, destroying the
  playing `<audio>` element (the 1:07 & 1:43 human readings always got cut). → Fixed at the
  kit level: `refresh()` now skips the re-render while audio is playing (`audioPlaying()`
  guard, both launchers) — verified a forced refresh mid-play didn't stop playback. Labels
  also corrected to real durations (were mislabeled "2 min").
- [x] 2026-07-09 "if you go in and play I wanted a nice wallpaper showing up rotating" → First
  cut was a dimmed backdrop pulled from the Wallpaper collection (superseded, see below).
- [x] 2026-07-09 (clarified) Inspiring images must be (a) SEPARATE/self-contained, not the
  Wallpaper app, and (b) FOREGROUND, prominent. → Generated a bundled set of 6 inspiring
  images (`/media/inspire/*.png` — warm radial glows + uplifting words) and replaced the
  dimmed backdrop with a full-bleed FOREGROUND overlay (`audioImages` config) shown while a
  program plays; tap to pause, ← to exit; rotates every 12 s. Verified full-bleed on play,
  rotation, audio-survives-refresh, removed-on-leave (`exports/verify_inspire.py`,
  `exports/dr_inspire_playing.png`). SUPERSEDED by real nature photos below.
- [x] 2026-07-09 "find nice image from nature, i dont like glowing visuals" → Replaced the
  generated gradient images with 6 real nature photographs (Wikimedia Commons, CC-BY-SA;
  `/media/inspire/nature1-6.jpg` + ATTRIBUTION.txt): cave temple sunbeam, moorland bridge,
  lone tree, Pyrenees valley, etc. Filtered to landscape proportions; all verified live.
- [x] 2026-07-09 Nature images don't appear on the Meta glasses. Root cause: the inspire
  overlay was triggered by the audio "play" event, but audio playback is device-limited on the
  glasses, so no play event → no images. → Fixed: `wireInspire()` now starts the overlay on
  opening an audio item's detail, decoupled from audio (audio is best-effort). Verified with
  audio playback fully BLOCKED (`exports/verify_inspire_noaudio.py`): image still appears
  full-bleed, loads, rotates, Back bar dismisses. Still can't drive the real device from here,
  but the audio dependency — the actual cause — is removed. Awaiting on-device confirmation.
- [x] 2026-07-09 Remove pre-seeded robotic/synthetic voice, keep only real human readings; and
  make the inspire images text-free (words + audio at once are too much). → Deleted the 3
  edge-tts synthetic program mp3s + their seed items (kept the 2 human LibriVox readings: If—,
  Invictus); regenerated the 6 inspire images with NO text (warm bokeh glows). Old mp3 URLs now
  404, new images live. Night keeps its text gratitude prompts (no synthetic program).
