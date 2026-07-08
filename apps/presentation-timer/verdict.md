# Presentation Timer — verdict

**Result: PASS** (both halves green) — evaluated against a local `wrangler dev` (ephemeral D1),
control page served from the Worker at `/apps/presentation-timer/control.html`.

## HARD gate — flowtest
`python tools/flowtest.py presentation-timer` → **PASS** (9/9 assertions: config conformance,
bulk feed, list appearance, `time`/`phase`/`label` round-trip, bulk-replace persistence).

## SOFT gate — agent-judge (screenshots of the running app vs acceptance.md)

### Display app
- [x] One row shows the **time as the hero** (big/bold `.big`) + phase beside it. Verified in both
  surfaces: web `12:47 · 🟢 On pace`; glasses (600×600) `12:00 · 🟢 On pace` on black (additive-
  friendly, D-pad focus ring visible). *(Fixed during eval: originally the phase was the big element;
  swapped `row` to `{title:"phase", badge:"time"}` so the time renders large.)*
- [x] Live update within the app's `refresh:3` — `refresh()` pulled the control page's latest push
  (`-0:26 · 🔴 OVER`) with no interaction.
- [x] `readOnly` — no add bar / delete controls in the app UI.
- [~] Detail view (label/time/phase): configured in `detail[]` and passes flowtest's detail-keys
  check; not separately screenshotted (low risk, list view confirmed on both surfaces).

### Control page (`control.html`)
- [x] Worker URL + password persist (localStorage) and are used for pushes.
- [x] **Start** ticks the big clock every second locally.
- [x] Pushes to the backend every ~3s **and** immediately on Start/Pause/Reset (confirmed by reading
  `GET /api/presentation_timer` after each action).
- [x] **Pause** freezes and pushes the frozen time (`-0:26 · 🔴 OVER`).
- [x] **Reset** returns to the set duration and pushes a clean idle state (`0:08 · 🟢 Ready`).
- [x] Pacing transitions: `🟢 On pace` → `🟡 Wrap up` (at the amber threshold) → `🔴 OVER` with the
  clock counting **negative** past zero. All observed in an 8s test run (amber at 5s).
- [~] Offline/failed-push handling: code path present (`catch` → "Offline — showing locally, will
  retry", keeps ticking); not exercised at runtime.

## Update (v2): smooth 1-second local ticking
Added a reusable `countdown` field type to both launchers (`app/index.html`,
`worker/public/index.html`). The control page now pushes an **absolute deadline** (epoch ms while
running; negative frozen-ms while paused) plus `amber` + `label`; the launcher ticks it **locally
every second** and computes the pace phase locally, re-syncing only via `refresh` (~15s).
Verified in the browser (glasses mode):
- [x] Time decremented `11:22 → 11:18` over 4s with **zero pushes** — proves local ticking.
- [x] Helper edge cases: running `1:30 → 🟡 Wrap up`, over `-0:32 → 🔴 OVER`, paused `12:30 → 🟢`,
  ready `15:00`.
- [x] Control page pushes an epoch deadline while running and a negative frozen value on pause.
- [x] Resilient: `tickCd` reads the cached deadline, not the network — a dropped sync never freezes it.

## Update (v3): glasses controls + conflict-free two-way sync
The glasses are no longer read-only. The launcher's `countdown` capability gained detail-view actions
(**Pause / Resume / Reset**) that write a new deadline to the DB, and the control page was refactored
so **both surfaces read/write the same DB deadline** (single source of truth) — no private clocks.
Verified in the browser (both tabs, live worker):
- [x] Glasses detail offers state-aware actions: running -> `Pause / Reset`, paused -> `Resume / Reset`.
- [x] Glasses **Pause** writes a negative (frozen) deadline; **Reset** writes `-(full*1000)` (10:00);
  **Resume** writes an epoch deadline.
- [x] Glasses Pause -> **phone control page adopts it within 3s** (`9:15 · ⏸ Paused`, running=false).
- [x] Phone Resume -> glasses adopt running (detail flips to `Pause`). No clobber (poll guarded 2.5s
  after a local action).
- [x] `full` (length) pushed by the control page so the glasses Reset knows the original duration.
- Note: glasses 1s DOM tick appears frozen only when the tab is backgrounded (browser timer
  throttling); `render()`/`cdTime` are correct and it ticks live when foreground.

## Known constraints (by design — see acceptance.md "Out of scope")
- No sound/vibration alarm on the glasses — it turns red and counts negative.
- Start/pause/settings live on the control page, not in the glasses/launcher app UI.

## Deploy note
The glasses/phone display needs the backend live (Cloudflare Worker + D1) — not yet deployed
(`runners/deploy_worker.bat`). Verified here against a local `wrangler dev`.
