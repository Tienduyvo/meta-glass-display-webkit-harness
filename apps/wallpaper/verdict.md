# Verdict — Wallpaper (ambient), increment 1 — evaluated 2026-07-08

Built with the corrected loop: **define → build → evaluate → fix**. The soft gate caught a real
bug (see below), which was fixed and re-verified.

## HARD gate — `tools/flowtest.py wallpaper`: **PASS (9/9)**
config conformance · create · appears in list · `image` round-trips · favorite persists · delete
removes · **bulk replace persists the pushed items** (new assertion, added after the bug below).

## SOFT gate — agent-judge (glasses screenshot vs acceptance.md)
- [x] add by image URL → appears in list **as a thumbnail** — PASS (screenshot: 2 thumbnails)
- [x] open on glasses → image **fills the 600×600 canvas edge to edge** — PASS (fullscreen screenshot)
- [x] favorite (★) is D-pad-reachable and persists — PASS (focusable overlay + hard gate)
- [x] delete removes from list — PASS at the data layer (hard gate); on the glasses **delete is
  intentionally phone-only** (no accidental deletes), so it's not in the fullscreen overlay.
- [ ] file drop → downscaled + added — **increment 2, not built yet** (deferred by design).

## Bug found + fixed during evaluation
`POST /api/:c/bulk?replace=1` with items reported `upserted` but the rows didn't persist on the
local D1 (separate awaited DELETE + INSERTs). Fixed by running them as one atomic `env.DB.batch()`;
added a flowtest assertion so the hard gate catches this class next time. (Also cleared local
wrangler state cruft from many dev restarts.)

## Overall (increment 1): **PASS** (both gates green)
Next: increment 2 — file drop with client-side downscale.
