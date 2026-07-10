# WhatsApp bridge — setup & operations

Remote-control the harness from your phone or Meta Ray-Ban Display glasses via WhatsApp.
Send "Sessions" → "Eins" to resume a session, approve commits with "Ja", receive
screenshots and code snippets as images. Works with voice dictation — no typing needed.

**Prerequisites:** Claude Code installed, a second WhatsApp number (for the bot), Node.js + bun.

## Quick setup (30 minutes)

Following the same pattern as the harness setup in AGENTS.md — one-time configuration,
then it runs unattended.

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

Apply the image-sending patch (enables `[[img:path|caption]]` markers):
- Copy patch code from **Appendix: Daemon patches** below into `src/whatsapp/client.ts` and
  `src/whatsapp/messages.ts`, or cherry-pick commits if/when the upstream PR lands.

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

---

## Appendix: Daemon patches

### Patch 1: Image sending (`src/whatsapp/client.ts`)

Add to imports:
```typescript
import { existsSync, readFileSync } from 'fs'
```

Replace `async sendMessage(to: string, text: string)` body:
```typescript
if (!this.socket || !this.isReady) {
    throw new Error('WhatsApp client not ready')
}

// Image markers: `[[img:/abs/path.png|optional caption]]` anywhere in the response
// is stripped from the text and sent as an actual image message.
const images: { path: string; caption: string }[] = []
text = text.replace(
    /\[\[img:([^\]|]+?)(?:\|([^\]]*))?\]\]/g,
    (_all, p, c) => {
        images.push({ path: String(p).trim(), caption: (c ?? '').trim() })
        return ''
    }
).replace(/\n{3,}/g, '\n\n').trim()

for (const img of images) {
    if (!existsSync(img.path)) {
        this.logger.warn(`Image marker points to missing file: ${img.path}`)
        continue
    }
    try {
        const result = await this.socket.sendMessage(to, {
            image: readFileSync(img.path),
            caption: img.caption || undefined
        })
        if (result?.key?.id) {
            this.sentMessageIds.add(result.key.id)
            setTimeout(() => this.sentMessageIds.delete(result.key.id!), 60000)
        }
        this.logger.info(`Sent image ${img.path} to ${to}`)
    } catch (err) {
        this.logger.error(`Failed to send image ${img.path}: ${err}`)
    }
}
if (!text) return

// Original prefixing + chunking code follows...
const prefixedText = formatMessageWithAgentName(this.config.agentIdentity, text)
// ... rest unchanged
```

### Patch 2: Captionless images (`src/whatsapp/messages.ts`)

In `extractMessageText()`:
```typescript
// Image — WITH or WITHOUT caption (captionless images must flow through)
if (message.imageMessage) {
    return message.imageMessage.caption ?? ''
}
```

In `parseMessage()`:
```typescript
const text = extractMessageText(msg)
if (text === null) return null // '' is valid: a captionless image
```

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
