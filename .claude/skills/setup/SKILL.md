---
name: setup
description: Agent-driven setup wizard for the WHOLE kit — one upfront question round covering every chosen section (backend, first app, glasses hookup, WhatsApp bridge, publish), then Claude drives each section to completion and self-heals known failures. Use on a fresh clone/fork, when the user asks to "set up" anything, or when status.py shows an unconfigured piece.
---

# Kit setup — one wizard for everything

You (the Claude Code session) are the wizard for the entire kit, not just one
feature. Same contract as `bridge-setup`: **ask everything ONCE up front, then
drive to completion, self-healing before ever asking again.** The user's total
workload: one answer round + the few genuinely human moments (a browser login,
scanning a QR, answering the app-Define questions, on-device tests).

Ground truth first: run `python tools/status.py` — never ask about something it
already answers (existing backend, registered apps, drift).

## 1. ONE upfront round (AskUserQuestion, multiSelect where sensible)

Ask only what status.py + the repo can't tell you:

- **Which sections?** (multiselect; preselect what status.py shows as missing)
  - *Backend* — Cloudflare Worker + D1 + app password (required for everything else)
  - *First app* — define + build + verify + deploy one app
  - *Glasses hookup* — register the launcher URL in the Meta AI app
  - *WhatsApp bridge* — remote control from phone/glasses (→ `bridge-setup` skill)
  - *Publish/share* — push the repo, template it
- **Per-section blockers, same round:**
  - Backend: do they HAVE a Cloudflare account (free is fine)? Have they picked
    an app password? (Don't ask for the password value — deploy.py prompts once.)
  - First app: the one-line idea. (The 2–3 Define questions from AGENTS.md follow
    immediately as part of this same opening phase — before any execution starts,
    never mid-run.)
  - Bridge: does a second WhatsApp-registered number exist right now?
- Close the round by stating the full plan + assumptions and get ONE go-ahead
  that covers everything, including deploys.

If a blocker answer is "no" (no Cloudflare account, no second number), drop that
section from this run and say what to prepare — don't stall the rest.

## 2. Drive the sections (in this order, skipping unchosen ones)

Each section = engine command(s) + a verify + a self-heal budget of ~3 attempts.
Sections are idempotent — re-running is always safe.

| Section | Engine | Verify |
|---|---|---|
| Prereqs | node/npx, python present (`tools/setup_bridge.py check` covers git/bun/node/claude for the bridge) | commands answer |
| Backend | `python tools/deploy.py` — unattended; reuses existing D1, writes database_id, skips done steps. Only interactive bits: `wrangler login` (browser) + API_SECRET, both front-loaded by the script | `GET /health` → `{"ok":true}` |
| First app | the AGENTS.md loop: acceptance.md → build → `evaluate.py` → deploy → report | `loop_state.py` reaches COMMIT/DONE |
| Glasses | `python tools/qr.py` for the launcher URL; user registers it in Meta AI app (Developer Mode → App Connections → Web Apps) | user confirms launcher opens on-device |
| Bridge | invoke the `bridge-setup` skill (its own engine + healing table) | its pair section reports `verified` |
| Publish | `runners/setup_repo.bat` (staged-file secret scan aborts on hits) | push visible on GitHub |

User gates that remain (hand over ONE crisp ask each): the wrangler browser
login, choosing/typing the app password into deploy.py's prompt, Define answers,
the Meta-AI-app registration + QR scan, bridge QR + test texts, COMMIT approval,
on-device testing. Everything else: state the assumption and keep moving.

## 3. Self-healing (fix first, ask after ~3 failed attempts)

| Symptom | Fix yourself |
|---|---|
| `npx` missing | Node not installed — this one IS a user ask (installer needs admin) |
| deploy.py: not logged in | tell the user to run `! npx wrangler login` (interactive browser step), then re-run deploy.py |
| `wrangler dev` crashes (workerd std::terminate) | move `worker/.wrangler` aside, re-apply `schema.sql` locally, retry |
| flowtest red / evaluate red | the loop's own self-fix budget (AGENTS.md): fix → re-run ≤3, then blocker report |
| apps/ vs worker/public drift | `python tools/sync_public.py` |
| health check fails after deploy | re-read deploy output; check `wrangler.toml` database_id; redeploy once |
| bridge section fails | `bridge-setup`'s own healing table — don't duplicate it here |

Rules unchanged from AGENTS.md: never commit without the COMMIT gate, no secrets
or real database_ids in tracked files (revert the placeholder after publishing),
never end a turn on a silent failure — advance or hand over one crisp ask.
