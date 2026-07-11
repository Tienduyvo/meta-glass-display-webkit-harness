# News — findings (user testing)

- [x] 2026-07-11 Glasses: headlines too long for the row — FIXED: focused row's title
      glides left→right→left (CSS marquee, speed scaled to overflow, only the focused
      row animates). Kit-level (both launchers, all apps). Verified: `.mq.go` active
      with −423px travel on a long headline.
- [x] 2026-07-11 Glasses: article detail with an image can't scroll — FIXED: glass
      `#screen` scrolls (max-height 502px), detail images capped at 280px (`.dimg`),
      opening lands at the top, arrowing through actions keeps them in view.
      Kit-level. Verified: scrollHeight 532 > clientHeight 502, scrollable.
- [x] 2026-07-11 Glasses: "swipe right" to remove article + next — FIXED: D-pad →
      in the detail view deletes the article and shows the next one (needs
      `actions.delete`, now on for News). Kit-level mapping. Verified: headline
      advanced to the next story on ArrowRight.
- [x] 2026-07-11 Feed order: mix interests, most popular first — FIXED in the
      pipeline: round-robin across sections (each section's top story first), so the
      glasses list alternates topics; the phone dashboard still groups by section.
      Verified: rank order = SectionA, SectionB, SectionC, Discover, SectionA, …
- [x] 2026-07-11 Glasses: many articles cannot be opened on the Meta browser — CONFIRMED
      Google News redirect URLs (JS shell pages; 6/35 items). FIXED twice over: the
      pipeline now drops news.google.com URLs entirely (only direct Bing/Yahoo publisher
      links ship; Discover walks Bing fallback queries instead of Google top stories),
      AND articles no longer need the browser at all — tier-2 extraction (trafilatura)
      puts the full story text (`body`, ≤1800 chars, paragraphs preserved) into the
      in-app detail view; ▶ Open original stays as backup. Verified: 0 redirect URLs,
      24/40 real bodies, detail scrolls 1477px of story on the glasses.
- [x] 2026-07-11 Glasses: some stories are cut off — FIXED: ↓ now scrolls the story
      300px at a time and only cycles the bottom actions once the end is reached;
      ↑ scrolls back. Body cap also raised 1800→2400 chars. Verified headless
      (scrollTop 0→300 before action focus engages).
- [x] 2026-07-11 Glasses: "swipe right" unreliable on-device — FIXED gesture-independent:
      a focusable "✕ Dismiss — next story" action in every article (Enter always works),
      plus ArrowRight dismiss in the LIST view too (swiping on a row). ArrowRight in
      detail stays. Awaiting on-device confirmation of which gesture path fires.
- [x] 2026-07-11 Glasses: some articles still fail via ▶ Open — RESOLVED by removing
      the action from the glasses surface entirely (owner: "is open article still
      needed?"): the in-app story text IS the article there; `url` removed from the
      config's fields/detail so the generic launcher builds no Open action. The phone
      dashboard (control.html) still opens originals from item data. Verified: glass
      detail actions = Check off / Favorite / Dismiss only.
- [x] 2026-07-11 Glasses: stories still cut off + stub stories dead-end without a link —
      FIXED in the pipeline: body cap raised to 3200 chars, and a MIN_BODY=400 quality
      gate drops any story whose extraction failed (chart/ticker items exempt — their
      value is the quote+viz). Reserve fetch raised (+8) to compensate; feed is smaller
      (22) but every text story has ≥698 chars of real content. Known limit: Bing caps
      ~12 results/query, so Markets runs thin post-filter — add query variants per
      section if it bothers in practice.
- [x] 2026-07-11 Glasses: teach the gestures — FIXED: the article footer now reads
      "n/N · → next story · ↓ read · ← back" (generic: any app with actions.delete).
- [x] 2026-07-11 Stories ending with ".." — two causes, both handled: my clip cap was
      trimming long extractions (raised 3200→6000, extractions now ship whole) and some
      sites only embed a teaser in static HTML (JS-loaded articles) — short trailing-off
      bodies (<900 chars ending "…") now filtered with the stubs. Genuine full-story
      needs = tier 3 (Claude fetches via real browser on request).
- [x] 2026-07-11 Glasses: bottom navigation hint not visible on-device — FIXED: in glass
      detail the hint rides in the TOP-RIGHT status slot ("n/N · → next · ↓ read",
      bright #9ecbff, 15px); footer kept as secondary.
