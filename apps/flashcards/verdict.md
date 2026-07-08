# Flashcards — verdict

Date: 2026-07-08

## Hard gate — flowtest
PASS (12/12 assertions). create → appears in list → front/back/topic round-trip →
check persists → fav persists → delete removes → bulk replace persists.
Run against the live Worker in an isolated `flashcards_flowtest` partition
(local `wrangler dev` unavailable on this machine — workerd runtime fails to start).

## Soft gate — screenshot vs acceptance.md
Opened the app (local `app/index.html` launcher → live API), added a chemistry card
(front "Combustion of methane", back "CH₄ + 2O₂ → CO₂ + 2H₂O", topic "Combustion").

- [x] Card appears in list with the **front shown prominently** (big bold badge) and
      **topic as smaller context** — matches the "front is the glanceable element" goal.
- [x] Detail view shows **front, back (the answer), topic** — subscripts render (CH₄, CO₂, H₂O).
- [x] Check-off present (D-pad on glasses / tap on phone) — "learned".
- [x] Star (fav) present — "hard cards".
- [x] Delete present.
- [x] List is browsable card-by-card before revealing the back (glasses review flow).

## Overall: PASS (both gates green)
