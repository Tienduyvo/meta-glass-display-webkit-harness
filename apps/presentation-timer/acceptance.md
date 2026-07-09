# Presentation Timer — acceptance

A glanceable presentation countdown for the glasses, driven by a control page you run on your
phone/laptop. The control page pushes an **absolute deadline** (not a ticking string); the launcher's
`countdown` field type ticks it **locally every second** on the glasses and re-syncs via `refresh`
(3s) to pick up pause/reset/adjust. Because both the phone and the glasses derive from the *same*
absolute deadline, the running time can't drift — they only differ by device clock offset; and a
state change (pause/reset) reaches the glasses within the 3s sync. A dropped fetch never freezes the
clock (the tick reads the cached deadline). All settings + start/pause controls live in `control.html`.
When over time, the glasses row **blinks red**.

## Definition (consolidated 2026-07-09; presets from user feedback on live testing)

1. *What's the data?* → **One absolute deadline** (epoch-ms running / negative-frozen paused)
   plus label, length and wrap-up threshold — the DB row is the single source of truth both
   surfaces read AND write; plus **preset rows** (1/5/10/15 min, paused at full) so the app is
   usable before any setup.
2. *What's the consuming moment?* → **Presenting: hands busy, eyes up** — glancing time-left
   mid-talk is exactly when pulling out a phone is impossible. Glasses-worthy by definition.
3. *Key action in the moment?* → **Glance the big time + pacing phase**; Enter → Pause /
   Resume / Reset. Everything else (durations, labels, thresholds) is phone-side authoring.

## Surface plan

- **Glasses (consuming):** big ticking time as the row's bright element, pacing badge
  (🟢/🟡/🔴, blinks red when over); detail = Pause/Resume/Reset via D-pad. **Never empty:**
  seeded preset timers (1/5/10/15 min) sit in the list ready to Resume even before the control
  page was ever opened; a truly empty collection shows the kit's "set it up on your phone" hint.
- **Mobile (authoring/control):** the launcher opens `control.html` directly — big local clock,
  Start/Pause/Reset, ±adjust, **one-tap preset chips (1/5/10/15/20 min)** that arm + sync the
  timer immediately, length/label/amber inputs.
- **Desktop:** same control page (presenter's laptop); no bulk/PC feed — skipped, nothing to
  compute.

## Assumptions (stated, not asked)
- The **consuming** moment (glancing at time left while presenting, hands busy, eyes up) belongs on
  the **glasses**; the **authoring/control** moment (set duration, start/pause) belongs on
  **phone/desktop** — different moments, different surfaces.
- The display shows **one** live row: the remaining time as the title, a pacing phase as the badge.
- The glasses tick **every second** (local animation from the deadline). Re-sync is every 3s and only
  corrects state changes (pause/reset/adjust). No buzzer on the glasses — it turns red, **blinks**, and
  counts negative when over.
- Pacing: `🟢 On pace` while remaining > amber threshold, `🟡 Wrap up` at/under amber, `🔴 OVER`
  (with negative time, e.g. `-1:12`) once time is up. Default amber threshold = **2:00** remaining.
- Default talk length = **15:00**. All of these are editable in the control page.
- The glasses app is **not** read-only: its detail view (press Enter, D-pad) offers **Pause / Resume
  / Reset**. The **DB deadline is the single source of truth** — glasses and the phone control page
  both read and write it, so neither owns a private clock and they can't drift or clobber. Each side
  adopts the other's changes within its 3s sync (proven: glasses Pause → phone shows Paused at the
  same time; phone Resume → glasses resume).

## Criteria

### Display app (glasses + phone view)
- **Given** the control page has pushed a state, **when** I open Presentation Timer in the launcher,
  **then** I see one row: the remaining time (e.g. `12:47`) as the title and the phase as the badge.
- **Given** the app is open, **when** the control page pushes a new time, **then** the display
  updates within ~3s (the app's `refresh`) without any interaction.
- **Given** I open the detail view on the glasses (Enter), **then** I see the talk label, time, and
  phase.
- The app is `readOnly` — no add bar, no delete.

### Control page (`control.html`, phone/laptop)
- **Given** I open the control page, **when** I enter the Worker URL + password once, **then** it is
  remembered (localStorage) and used for pushes.
- **Given** a duration is set, **when** I press **Start**, **then** a large countdown ticks down
  every second locally.
- **Given** the timer is running, **then** the remaining time + phase are pushed to the backend
  every ~3s (and immediately on Start/Pause/Reset).
- **Given** I press **Pause**, **then** the countdown holds and the pushed state reflects the frozen
  time.
- **Given** I press **Reset**, **then** the countdown returns to the set duration and the display is
  updated.
- **Given** remaining time crosses the amber threshold, **then** the phase becomes `🟡 Wrap up`;
  **given** it reaches 0, **then** the phase becomes `🔴 OVER` and time counts negative.
- **Given** a push fails (offline/bad creds), **then** the control page shows a clear status and keeps
  ticking locally (it retries on the next tick).

## Glasses controls (added)
- **Given** the timer is running, **when** I open the row's detail on the glasses, **then** I can
  arrow to **⏸ Pause** or **↺ Reset** and press Enter; **given** it's paused, I see **▶ Resume / Reset**.
- **Given** I press a glasses control, **then** it writes the new deadline to the DB and the phone
  control page adopts it within ~3s (and vice-versa) — no two-clock conflict.

## Presets & empty state (added 2026-07-09, user feedback; revised same day)
- **One active timer, selected by preset** (user: "showing multiple timers… better to just
  select and then 1 timer becomes active"): the collection holds a single `current` row —
  the glasses always show exactly ONE timer. Selection happens on the control page: tapping
  a preset chip (1/5/10/15/20 min) makes that duration THE active timer (armed paused-at-full,
  synced). The earlier multi-preset-row seeding is retired.
- **Given** a fresh backend, **when** I open the timer on the glasses, **then** I see the one
  seeded ready timer (10:00 default) — Enter → **▶ Resume** starts it hands-free; never blank.
- **Given** the control page, **when** I tap a preset chip, **then** the length is set and the
  single active timer re-arms to it. (Verified: `exports/dr2_control_after_chip.png`,
  10-min chip → `10:00`.)
- **Given** an empty collection, **then** the glasses show the kit's "Nothing here yet — set it
  up on your phone" hint instead of a blank list.

## Out of scope (kit constraints, by design)
- No sound/vibration alarm on the glasses (it turns red and blinks when over).
- Rich settings (duration/thresholds) stay on the phone control page; the glasses expose the common
  actions (pause/resume/reset) only.
