# Flashcards — acceptance criteria

**Assumptions (state, don't ask):**
- General-purpose flashcards, chemistry reactions as the driving example.
- **Front** = the prompt (e.g. "Combustion of methane"); **Back** = the answer
  (e.g. "CH₄ + 2O₂ → CO₂ + 2H₂O"); **Topic** = category badge (e.g. "Combustion").
- Belongs on the glasses: review is a hands-free / eyes-up moment (walking, commuting,
  chores) — glance the front, recall, flip to reveal the back. Authoring is on phone.
- `check` = "learned / mastered"; `fav` = "star the hard ones". Delete allowed.

## Given / When / Then

- **Given** the app is open on phone,
  **when** I add a card with front "Combustion of methane", back "CH₄ + 2O₂ → CO₂ + 2H₂O",
  topic "Combustion",
  **then** it appears in the list with the front shown prominently (big badge) and the
  topic as context.

- **Given** a card in the list,
  **when** I open it,
  **then** the detail shows the front, the back (the answer), and the topic.

- **Given** a card I've mastered,
  **when** I press check on the glasses (D-pad) or tap check on phone,
  **then** it's marked learned.

- **Given** a hard card,
  **when** I star it,
  **then** it's favourited.

- **Given** the glasses,
  **when** I browse the list,
  **then** the front of each card is the large glanceable element and I can arrow through
  cards hands-free before revealing the back.
