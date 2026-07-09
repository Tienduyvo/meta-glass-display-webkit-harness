# Presentation Timer — user findings (real-device testing)

Open `- [ ]` lines put this app in the FIX state (loop_state.py) until fixed + re-evaluated.

- [x] 2026-07-09 Empty/dead on mobile and glasses when no timer set — "at least show some
  pre-used timer times like 1 min, 10 min". → Preset chips (1/5/10/15/20 min) on the control
  page + kit-wide empty-state hints.
- [x] 2026-07-09 Multiple preset timer rows confusing — "better to just select and then 1
  timer becomes active". → Collection reduced to a single `current` row; chips select the
  active duration; glasses always show exactly one timer.
