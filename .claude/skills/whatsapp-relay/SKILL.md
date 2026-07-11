---
name: whatsapp-relay
description: Become the WhatsApp relay listener — incoming bridge messages arrive as Monitor events in THIS interactive session (which has the Chrome extension, Gmail, etc.), replies go back to WhatsApp via outbox files. Use when the user wants WhatsApp messages handled with full desktop-session capabilities.
---

# WhatsApp Relay Listener

The WhatsApp bridge daemon (patched fork in `~/Downloads/whatsapp-claude-agent`, started
by `start-bridge.cmd` with `WA_RELAY_DIR` set) relays incoming messages to a live
interactive Claude Code session instead of spawning a headless one. Headless sessions
cannot use the Claude-in-Chrome extension (native messaging, interactive-only); this
session can. If no listener is alive, the daemon falls back to its built-in headless
backend and prefixes those replies with `[headless]` — the bridge never goes dark.

## Protocol

Relay dir: `~/.whatsapp-claude-agent/relay/`

- `inbox.jsonl` — daemon appends one JSON object per incoming WhatsApp message:
  `{"id": "<uuid>", "ts": "<iso>", "text": "<user message>"}`
- `outbox/<id>.txt` — you write the reply here. **Atomically**: write `<id>.txt.tmp`
  first, then rename to `<id>.txt` (the daemon polls every 500ms and must never read
  a half-written file).
- `listener.alive` — heartbeat file. The daemon treats the listener as alive when its
  mtime is < 60s old. The Monitor script below maintains it; when the Monitor stops,
  the heartbeat goes stale and the daemon falls back to headless.
- `listener.info` — one-time JSON metadata about this listener, e.g.
  `{"model":"claude-fable-5","kind":"interactive desktop session"}`. The daemon's
  startup banner reads it (with a fresh heartbeat) to announce who actually answers.
  Write it (atomically) right after starting the Monitor.
- `outbox/events/<name>.txt` — **speak first** (daemon feature added 2026-07-11): the
  daemon polls this dir every 2 s and sends each file's content to the owner as an
  UNPROMPTED WhatsApp message — no inbound message or reply slot needed. Write
  atomically (`.tmp` → rename); prefix names for ordering (`001-…`).
  `[[img:path|caption]]` markers work here too. Use it for what request/reply can't
  cover: a long build finished, you're blocked and need the desk, a promised follow-up.
  Same register as replies (short, call-style, glance-safe) — one message per real
  transition, never a progress ticker.

## Becoming the listener

FIRST check whether a listener is already alive — another interactive session may
still hold the role (heartbeat fresh = mtime < 60s; verified incident 2026-07-10:
two listeners raced on replies and overwrote each other's outbox files):

```bash
A="$HOME/.whatsapp-claude-agent/relay/listener.alive"
[ -f "$A" ] && [ $(( $(date +%s) - $(stat -c %Y "$A") )) -lt 60 ] \
  && echo "LISTENER ALREADY ALIVE - do not start a second one" || echo "free"
```

If one is alive, STOP and tell the user which decision is theirs: close the other
session (or its Monitor) first, or leave the listener role there. Only proceed when
the heartbeat is stale/absent.

**Takeover mode** (skill invoked with arg `takeover` — used by the voice-triggered
session swap below): the opposite rule. A predecessor is about to retire; poll the
heartbeat until it goes stale (check every 10s, give up after 3 min), THEN start the
Monitor and write `listener.info`. While waiting, do nothing else. If it never goes
stale, report that the old listener didn't retire and stop.

Then start ONE persistent Monitor (single process = heartbeat dies exactly when the
watch dies; never run two listeners at once):

```
Monitor (persistent: true, description: "WhatsApp relay inbox") with command:

RELAY="$HOME/.whatsapp-claude-agent/relay"
mkdir -p "$RELAY/outbox"
touch "$RELAY/inbox.jsonl"
LAST=$(stat -c %s "$RELAY/inbox.jsonl")
while true; do
  touch "$RELAY/listener.alive"
  SIZE=$(stat -c %s "$RELAY/inbox.jsonl")
  if [ "$SIZE" -lt "$LAST" ]; then LAST=0; fi
  if [ "$SIZE" -gt "$LAST" ]; then
    tail -c +"$((LAST + 1))" "$RELAY/inbox.jsonl"
    LAST=$SIZE
  fi
  sleep 2
done
```

Each event line is one inbox JSON record. Note the starting `LAST` skips messages that
arrived while no listener ran — those were already answered by the headless fallback.

## Handling an event

1. Parse `id` and `text`. Do the task with your full toolset (Chrome extension, Gmail,
   repo tools). The message may include an image note ("saved at: <path>") — Read it.
2. Reply in the STANDARD bridge style (owner decision 2026-07-10, replaces the old
   bare-numbers/ja-nein etiquette): the owner is usually on voice-only glasses, often
   around other people; the register is a normal phone call. Write in English like a
   friend on a call — short plain sentences, no lists, no numbered options, no emojis,
   no markdown, no jargon unless he asks for detail. Answer the message directly; no
   status dumps, no commit proposals unless asked. Offer choices as casual either/or
   questions and accept replies that echo a keyword of an option ("the beach one") —
   bare numbers still work but never require them. Glance-safe: a bystander seeing
   the screen should read harmless small talk. Natural yes/no phrases ("go ahead",
   "let's not") count as confirmations — the daemon's permission matcher (fork
   permissions.ts) accepts the same list.

   To send a photo, embed `[[img:C:\abs\path.png|caption]]`
   — the daemon converts it to a real WhatsApp image.

   Getting a photo file (the Chrome-extension screenshot tool's `save_to_disk`
   leaves NO locatable file on this setup — verified 2026-07-10, don't use it):
   - Web page: Playwright + Edge (`channel='msedge'`, headless) →
     `page.screenshot(path=...)`, save under `~/.whatsapp-claude-agent/relay/shots/`.
   - PC screen: `python tools/screenshot.py` (harness repo; owner-only, only on
     explicit request).
3. Write the reply atomically (bash):
   ```bash
   RELAY="$HOME/.whatsapp-claude-agent/relay"
   cat > "$RELAY/outbox/<id>.txt.tmp" <<'EOF'
   <reply text>
   EOF
   mv "$RELAY/outbox/<id>.txt.tmp" "$RELAY/outbox/<id>.txt"
   ```
4. Deadline: the daemon waits max 10 minutes per message. If the task needs longer,
   reply with a progress note before the deadline and continue when the user's next
   message arrives.

## Owner voice command: "new session" (glasses-first session swap)

The glasses are the primary UX — the owner must be able to replace a long/slow
listener session by voice, no PC. When an inbox message is essentially just
"new session" / "fresh session" (not an incidental mention), the CURRENT listener
runs this handover, in this order:

1. Update the bridge memory file with a 3-line handover note (open items, oddities).
2. Spawn the successor in a NEW visible terminal (PowerShell):
   `Start-Process cmd -ArgumentList '/k cd /d "<harness repo>" && claude "/whatsapp-relay takeover"'`
3. Reply to the message (BEFORE retiring — the reply slot dies with the daemon wait):
   confirm the swap and say the next answer comes from the fresh session.
4. TaskStop your own Monitor. Heartbeat goes stale; the successor claims the role
   within ~1–2 min. If the successor never starts, the daemon's headless fallback
   answers meanwhile — the bridge never goes dark.

The needed permissions (Monitor, the `RELAY=`-prefixed Bash pattern, python tools,
windows-mcp) are pre-allowlisted in `.claude/settings.local.json`, so the fresh
session runs the listener loop without desk prompts. Task-specific tools may still
prompt — that's expected and approved at the desk as usual.

⚠️ **KNOWN LIMIT (verified 2026-07-10, first attempt): step 2 auto-spawn is BLOCKED
by the safety classifier** — a session auto-launching a successor that would act on
remote commands with the per-action gate pre-bypassed is exactly what "create unsafe
agents" refuses, and relay events are marked NOT USER INPUT so they can't clear the
bar. Do NOT retry the spawn or try to route around it. Instead, when the owner asks
for "new session" by voice: DON'T retire; reply that the fully-hands-free swap is
blocked by design, keep serving, and tell him the desk path (open a new session, say
"whatsapp relay" — 10s). Auto-swap would require the owner to explicitly pre-authorize
that spawn at the desk first.

## Caveats

- Permission prompts in this session block until approved AT THE DESK. For unattended
  remote use, start the session with a permission mode/allowlist that covers the
  expected tools — or expect stalls.
- Don't run the terminal conversation and heavy relay work simultaneously on
  conflicting files; events interleave with the local conversation.
