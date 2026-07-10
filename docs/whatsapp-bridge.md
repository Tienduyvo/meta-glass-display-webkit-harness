# WhatsApp bridge — setup & operations

Remote-control the harness from your phone or Meta Ray-Ban Display glasses via WhatsApp.
Send "Sessions" → "Eins" to resume a session, approve actions with a natural "go ahead",
receive screenshots and code snippets as images. Works with voice dictation — no typing
needed. Replies come in the **standard bridge register** (owner decision 2026-07-10):
short plain English like a friend on a phone call — no lists, no numbered options, no
emojis — so using it around other people reads as a normal call. Keyword answers ("the
beach one") select options; bare numbers still work but are never required.

**Prerequisites:** Claude Code installed, a second WhatsApp number (for the bot), Node.js + bun.

## Setup effort — honest assessment

Be honest with yourself before starting: **this is a tinkerer-grade setup, not a
product.** What it took to build ran across two days and two abandoned approaches; the
pitfalls are all documented below, but even following this runbook cleanly you should
budget:

- **Comfortable with git/terminal/reading logs:** 1–2 hours of active work — clone,
  `bun install`, apply one patch file, create two small config files, pair, then one
  log-reading round-trip to capture your LID (step 3 cannot be done blind).
- **Plus dead waiting time:** getting a second phone number can take days (satellite
  activation letter: 2–4 Werktage). The number is a hard requirement, not optional.
- **Not comfortable with a terminal:** don't attempt this today. There is no installer;
  you'd be running a patched fork from source, editing `.cmd` files, and diagnosing
  identity issues from daemon logs.

What would make this end-user-ready (none of it exists yet): a packaged installer, an
upstreamed fork (PR candidate — the patch is `docs/whatsapp-bridge.fork.patch`),
automatic LID capture instead of the read-the-log dance, and a pairing wizard. Until
then, assume every fresh machine setup is a half-day project including the number wait.

## Quick setup

One-time configuration, then it runs unattended.

**Wizard (recommended): let Claude drive it.** Once you have the second number
registered on WhatsApp, open Claude Code in this repo and say "set up the WhatsApp
bridge" (the `bridge-setup` skill). It asks everything up front — which feature
sections you want (core / images+reliability / relay / autostart), your number —
then installs only what you chose, watches every step, and **self-heals known
failures** (missing bun, patch drift, pairing stalls, the LID whitelist dance)
before ever coming back to you. Your only actions: answer the questions, scan one
QR, send two test messages.

Under the hood it drives `tools/setup_bridge.py`, which is sectioned and idempotent
(`check` / `install` / `config` / `shim` / `pair` / `autostart`) — every section can
be re-run safely and reports a machine-readable `STATE:` line. No Claude session?
`python tools/setup_bridge.py all` runs the same flow standalone, without the
self-healing. The manual steps below remain the reference for what happens.

### 1. Get a second WhatsApp number (bot account)

The bridge needs a **separate** WhatsApp account (self-chat doesn't trigger notifications
on glasses). Options:
- Cheapest: German virtual number via satellite/sipgate (~€10 one-time, activation letter 2-4 days)
- Free tier SIM from any carrier (register WhatsApp on it, then keep the SIM powered off)
- Existing secondary phone number

### 2. Clone and patch the daemon

```bash
cd %USERPROFILE%\Downloads
git clone https://github.com/dsebastien/whatsapp-claude-agent.git
cd whatsapp-claude-agent
bun install
```

Apply the full fork patch (image sending, reliability fixes, relay mode, voice-friendly
permissions, reply style — see **Appendix: Daemon patches** for the inventory):

```bash
git apply "<harness repo>/docs/whatsapp-bridge.fork.patch"
bunx tsc --noEmit   # must exit 0
```

### 3. Configure your whitelist

Create `%USERPROFILE%\.bridge-env.cmd`:
```cmd
@echo off
set WA_WHITELIST=+1234567890,1234567890
```
Replace with your phone number and its LID (numeric privacy ID). Find your LID: start the
bridge once, send a message, read the log line `"Blocked message from non-whitelisted
number: <LID>@lid"` — add that bare number (no `@lid` suffix) to the whitelist.

### 4. Pair the bot

Double-click `start-bridge.cmd` in the harness root. A QR code appears → scan it with the
**bot account's** WhatsApp (Linked devices → Link a device). After pairing:
- Force-stop WhatsApp on YOUR phone (clears stale device cache)
- Send "Hallo" from your phone to the bot number → reply confirms it works

### 5. (Optional) Enable autostart

Create a shortcut to `start-bridge.cmd` in:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
Set "Run" to "Minimized" — the bridge starts silently at login.

Done. Say "Sessions" to your glasses to list sessions, "Eins" to resume one.

---

## Working architecture

```
Your WhatsApp (owner) ──► bot WhatsApp account (second number)
                             │  linked device (Baileys)
                             ▼
              whatsapp-claude-agent.exe  (standalone daemon, ~/.local/bin)
                             │  Agent SDK (inherits Claude Code login)
                             ▼
                Claude session in THIS repo (hooks, skills, loop)
```

- Daemon: [dsebastien/whatsapp-claude-agent](https://github.com/dsebastien/whatsapp-claude-agent)
  (v1.5.1, Windows x64 binary). No Claude Code plugin, no `--channels` — the daemon drives
  Claude via the Agent SDK directly.
- Started by `start-bridge.cmd` (repo root): watchdog loop, verbose logging, whitelist,
  workdir = repo, `--load-claude-md user,project`. Autostart: shortcut
  `claude-whatsapp-bridge.lnk` in the user Startup folder.
- WhatsApp session state: `~/.whatsapp-claude-agent/session` (pairing survives restarts).
- Protocol for the spawned session: `.claude/skills/whatsapp-loop/SKILL.md`
  (gates via `tools/remote_gate.py`, snippets via `tools/snippet_image.py`,
  screenshots via `tools/screenshot.py`).
- **Image sending: patched into the daemon itself.** The stock daemon is text-only, so we
  run a patched FORK from source (clone https://github.com/dsebastien/whatsapp-claude-agent
  next to this repo, apply patches from this doc; MIT license). Patch in
  `src/whatsapp/client.ts` `sendMessage()`. A reply line
  `[[img:C:\abs\path.png|caption]]` is stripped from the text and sent as a real photo.
  `start-bridge.cmd` runs the fork via bun from source; it uses the SAME session dir as
  the stock exe, so the pairing carries over. Candidate for an upstream PR. If the fork
  is ever replaced by the stock exe again, images silently degrade to visible marker text.
- **Relay mode (fork, `src/claude/relay-backend.ts`):** with `WA_RELAY_DIR` set (done in
  `start-bridge.cmd`), incoming messages are relayed to a live INTERACTIVE Claude Code
  session instead of a headless one — headless sessions can never use the
  Claude-in-Chrome extension (native messaging is interactive-only). Protocol: daemon
  appends `{id,ts,text}` to `<relay>/inbox.jsonl`; the desktop session runs a persistent
  Monitor (see `.claude/skills/whatsapp-relay/SKILL.md`) that heartbeats
  `<relay>/listener.alive` and answers by atomically writing `<relay>/outbox/<id>.txt`.
  No fresh heartbeat (60s) or no reply in 10 min → automatic fallback to the headless
  backend, replies prefixed `[headless]`. The bridge never goes dark; the relay session
  just makes it stronger while one is running.

---

## Appendix: Daemon patches

**Single source of truth: [`whatsapp-bridge.fork.patch`](whatsapp-bridge.fork.patch)**
(regenerate from the fork with `git add -N src/claude/relay-backend.ts && git diff`).
Apply to a fresh clone with `git apply`, then `bunx tsc --noEmit` must exit 0.
Inventory of what the patch contains and why:

| File | What | Why |
|---|---|---|
| `src/whatsapp/client.ts` | `[[img:path\|caption]]` markers → real photo messages | stock daemon is text-only |
| `src/whatsapp/client.ts` | `upsert.type !== 'notify'` filter, bounded inbound-ID dedup set, read receipts after whitelist gate | **re-delivery loop fix** — without all three, reconnect flaps replay old messages and each replay is a full paid Claude run |
| `src/whatsapp/messages.ts` | captionless images flow through (`caption ?? ''`) | glasses-camera photos usually have no caption |
| `src/claude/relay-backend.ts` (new) + `src/index.ts` | relay mode (`WA_RELAY_DIR`): inbox.jsonl / outbox / heartbeat, headless fallback | reach a live interactive session (Chrome extension etc.) |
| `src/claude/permissions.ts` | punctuation-tolerant matcher + natural yes/no phrases ("go ahead", "let's not", …) | voice dictation inserts punctuation; robotic "Stopp" is conspicuous in public |
| `src/claude/sdk-backend.ts` | `STYLE_HINT` in every system prompt: call-register English, no lists/options/emojis, keyword-echo selection | standard bridge style (owner decision 2026-07-10) |
| `src/conversation/manager.ts` | "sessions"/"sitzungen" + bare number/number-word session picking | dictation can't type slash commands |

Ambiguity rule for the yes/no phrase lists: only phrases that are unambiguous in speech.
"Passt schon" is deliberately excluded — in German it usually means "forget it".

---

## Troubleshooting

### Common issues (in order of likelihood)

1. **Bot needs a SECOND WhatsApp account.** Self-chat messages don't trigger notifications
   or glasses announcements. One-time number for registration is enough (satellite/sipgate
   works via call-verification; activation letter takes 2–4 Werktage).
2. **First attempt (rich627 whatsapp-claude-channel plugin) — abandoned.** Send worked,
   inbound NEVER arrived (zero `messages.upsert` events across bun AND node runtimes,
   three re-pairings). Don't reinstall. Its debugging did teach us: npm's bun is a `.cmd`
   shim MCP can't spawn (-32000); channel plugins need
   `--dangerously-load-development-channels plugin:<name>@<marketplace>`; Claude Code
   drops channel messages without that flag ("Channel notifications skipped").
3. **Sender identity is a LID, not a phone number.** The owner's messages arrive as
   `<numeric-lid>@lid` — a whitelist listing only the phone number blocks silently.
   Fix: whitelist BOTH the phone number AND the bare LID (comma-separated). The actual
   values live OUTSIDE the repo in `%USERPROFILE%\.bridge-env.cmd` (`WA_WHITELIST=…`),
   which `start-bridge.cmd` sources — never commit real numbers. If the account is ever
   re-registered the LID changes — read the new one from the daemon's `-v` log
   ("Blocked message from non-whitelisted number: …@lid").
4. **Daemon can't find Claude on Windows.** It probes Unix paths + `which claude`.
   Fix: `~/.local/bin/which.cmd` shim answering `which claude` with the full path to
   `claude.exe`. (Extensionless copies of the exe do NOT spawn — ENOENT.)
5. **Sender-side device cache.** After (re)pairing, the owner's phone may keep encrypting
   only to the bot's primary phone (messages show ✓✓ but never reach the companion).
   Force-stop WhatsApp on the OWNER's phone and reopen after any re-pairing.
6. **Watchdog ≠ config reload.** `start-bridge.cmd` restarts the daemon only when it
   exits. After editing the cmd (whitelist etc.) CLOSE the window and relaunch — a running
   daemon never picks up changes.
7. **Only one instance.** Two connections on one auth state kick each other off WhatsApp.
   The watchdog window is the single owner of the channel.
8. **Two answers to one message / bot replays old messages every ~90s.** Reconnect flaps
   make Baileys re-deliver history; each replay runs a full paid Claude session (one
   replay re-ran a whole Playwright script). Fixed in the fork (notify-filter + inbound
   dedup + read receipts — see appendix); if it returns, check those three patches
   survived a fork update. Side effect of the fix: senders see blue ticks.
9. **Replies prefixed `[headless]`.** Not an error — no interactive relay listener was
   alive, the daemon fell back to its built-in backend. Start one via the
   `whatsapp-relay` skill in a desktop session to get full capabilities back.

## Operations

- **Start/stop:** double-click `start-bridge.cmd` / close its window. Autostarts at login.
- **Logs:** live in the bridge window (`-v`). Look for `Found Claude Code at:` and the
  whitelist line at boot; `Blocked message from…` reveals identity/allowlist issues.
- **Session continuity:** everything runs LOCALLY — the daemon spawns Claude Code on this
  PC; WhatsApp is only transport, and terminal + WhatsApp share the same session store
  (`~/.claude/projects/<munged cwd>/`). From WhatsApp: `/sessions` lists the recent local
  sessions (fork-added command; timestamps + first-message preview), `/session <n>` resumes
  one by number, `/session <id>` by id, `/session clear` starts fresh, `/fork` branches.
  The reverse works too: `claude --resume <id>` pulls a WhatsApp-born session into the
  terminal. Never write to the SAME session from two places at once.
- **Benign noise:** `'which' is not recognized` before the shim ran, one
  `timed out waiting for message` after replies, a per-query cost line (informational
  under subscription auth).
