---
name: bridge-setup
description: Agent-driven WhatsApp bridge setup wizard — front-loads all questions, then installs only the chosen feature sections via tools/setup_bridge.py, watching each step and self-healing known failures from docs/whatsapp-bridge.md before ever asking the user. Use on a fresh machine, after a broken setup, or when the user asks to (re)install the WhatsApp bridge.
---

# WhatsApp bridge setup — agent-driven wizard

You (the Claude Code session) are the wizard. The deterministic engine is
`tools/setup_bridge.py` — sectioned, idempotent, safe to re-run. Your job:
ask everything ONCE up front, then drive sections to completion, self-healing
failures. The user should only ever: answer the upfront questions, scan one QR,
and send two test messages. Read `docs/whatsapp-bridge.md` (especially
Troubleshooting) BEFORE starting — it is your self-healing playbook.

## 1. Front-load ALL questions (one AskUserQuestion round, nothing later)

- **Second number reality check:** does a second WhatsApp-registered number for
  the bot exist RIGHT NOW? If no → stop; tell them the options (satellite/sipgate
  ~€10 + activation letter 2–4 Werktage, spare SIM) and to come back when it's
  registered. Nothing else is worth doing before that.
- **Owner number** (international format) — the phone that will text the bot.
- **Feature sections** (multiSelect):
  - *Core bridge* (always) — daemon, whitelist, pairing, text chat
  - *Images + reliability patch* (recommended) — send/receive photos, reconnect
    re-delivery fix, voice-friendly commands (= apply the fork patch; opting out
    installs the stock text-only daemon)
  - *Relay mode* — replies come from a live desktop session with browser access;
    requires someone to start the `whatsapp-relay` listener per session
  - *Autostart* — bridge launches at login
- Install directory only if non-default matters to them (default
  `~/Downloads/whatsapp-claude-agent`; warn that `start-bridge.cmd` expects it).

Then say you'll take it from here and only need them again for QR + two texts.

## 2. Drive the sections

Run each with Bash; every section ends with a `STATE: {json}` line — parse it.

```
python tools/setup_bridge.py check
python tools/setup_bridge.py install --dir <dir> [--no-patch]   # --no-patch if images section declined
python tools/setup_bridge.py config --owner +49...
python tools/setup_bridge.py shim
```

**Pairing needs a VISIBLE console** (the QR renders live; a Bash tool call would
buffer it). Launch it in its own window and poll the state file instead:

```
cmd /c start "bridge pairing" cmd /k python tools\setup_bridge.py pair --dir <dir>
```

Then poll `~/.whatsapp-claude-agent/setup-state.json` (Monitor or a Bash
until-loop, every ~5s). Phases: `starting → connected → lid_captured → verified`
(status `ok` = done, `fail` + reason otherwise). Prompt the user at the right
moments: "scan now", "send a text now", "send one more". Timeout per phase is
5 min inside the script.

Afterwards: `autostart` section if chosen. Relay mode needs no install step —
it's enabled by `WA_RELAY_DIR` in `start-bridge.cmd` (already set); just tell
the user how a desktop session becomes the listener (`whatsapp-relay` skill).

Finish: start the real bridge (`start-bridge.cmd`), confirm one round-trip
message, and summarize what was installed and how to start/stop.

## 3. Self-healing rules

On any `STATE: fail`, do NOT immediately ask the user. Diagnose → fix → re-run
the section (idempotent). Up to ~3 attempts per section, then explain and ask.
Known signatures (details in docs/whatsapp-bridge.md Troubleshooting):

| Symptom | Fix yourself |
|---|---|
| `check` missing bun | `npm i -g bun`, re-run |
| `check` missing claude | look for `claude.exe` under `~/.local/bin` and npm global dir; only ask if truly absent |
| `install` git apply failed | upstream drifted: `git apply --3way`, or clone the pinned base commit from the doc, or offer `--no-patch` |
| `install` tsc failed | read the errors; if from the patch, fix the code; if from upstream, pin the older commit |
| `pair` no connection | QR expired → relaunch pairing window; check system clock; delete `~/.whatsapp-claude-agent/session` ONLY with user consent (re-pairs from scratch) |
| `pair` stuck after connected | user's message never arrived → have them force-stop WhatsApp on their phone (stale device cache), send again |
| `pair` fail after lid_captured | whitelist wasn't reloaded → verify `~/.bridge-env.cmd`, restart pairing section |
| daemon "Claude Code executable not found" | re-run `shim` section, verify `~/.local/bin` is on PATH |
| replies show `[headless]` | expected without a relay listener — not an error |
| two answers to one message | re-delivery patch missing → images/reliability section was declined; recommend enabling it |

Never commit anything during setup. Never put real phone numbers in repo files —
they live only in `~/.bridge-env.cmd`.
