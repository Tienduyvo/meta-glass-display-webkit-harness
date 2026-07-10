---
name: whatsapp-loop
description: Drive the build loop remotely over WhatsApp — gates become WhatsApp messages, replies advance the loop. Use when a session is bridged to WhatsApp (whatsapp-claude-agent daemon) and the user is steering from phone/glasses instead of the terminal.
---

# Remote loop over WhatsApp

The user steers this harness from Meta glasses + phone via the **whatsapp-claude-agent
daemon** (standalone exe wrapping the Agent SDK; started by `start-bridge.cmd`, autostarts
at login — see memory: whatsapp-claude-bridge). If you are reading this you are likely THE
session that daemon spawned: inbound WhatsApp messages arrive as user turns, and your
replies go back to WhatsApp. The glasses announce and read messages aloud and take voice
replies — write every message to survive being HEARD, not just read.

## Emitting a gate
Whenever the loop hits a user gate (Define answers, commit approval, fix decision):

1. Build a gate object and render it: `python tools/remote_gate.py <gate.json>` (schema in
   the tool's docstring). Send the printed text as the reply.
2. Batch a whole Define round into ONE message (front-load, never dribble questions).
3. First sentence = the decision needed, spoken-style — that's what the glasses read first.
4. Never paste code — WhatsApp has no code formatting and read-aloud would recite it.
   Send code as a snippet PNG instead: `python tools/snippet_image.py <file> --lines a-b`
   prints a PNG path. To deliver ANY image, put a marker line in your reply:
   `[[img:C:\absolute\path.png|one-line caption]]`
   — the (patched) daemon strips it and sends the file as a real WhatsApp photo.
   One marker per line, absolute paths only.
5. Keep messages under ~900 characters. Detail belongs in a follow-up on request.

## Parsing replies
- Numbers map to the numbered options ("1: 2, 2: 1" answers question 1 with option 2, …).
- Voice notes may arrive transcribed; treat the transcription as free-form answers.
- "ja"/"ok"/"mach" on an approval gate = approve; "nein"/"stop" = deny.
- Ambiguous reply → ask ONE short clarifying question, don't guess.

## Commands the owner can text
- "screenshot" / "zeig bildschirm" / "was läuft" → `python tools/screenshot.py` prints a
  PNG path; reply with `[[img:<that path>|one line about what's visible]]`. ONLY on
  explicit request — the capture shows everything on screen, including private windows.
  Never send one proactively.

## Hard rules
- COMMIT stays a user gate: propose via an approval gate, commit only on explicit yes.
- Never publish/share/push without an explicit ask (memory: share-flow-in-harness).
- Only converse with the whitelisted owner; never message anyone else.
- When a run finishes with nothing actionable, send ONE status message with what changed
  and what's next — then stop messaging.

## History note
The first bridge attempt (rich627 whatsapp-claude-channel plugin + --channels flag) was
abandoned 2026-07-10: inbound messages never reached the server despite send working —
details in memory whatsapp-claude-bridge. Don't reinstall it.
