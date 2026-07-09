# Acceptance criteria — Wallpaper (ambient)

**Business case:** an **ambient image in your field of view while wearing the glasses** — a
"wallpaper" you glance at. A real glasses case (ambient view). Input happens on the phone.

**Increments (smallest evaluable first):**
- **Increment 1 (built):** add by **image URL**, **fullscreen** ambient view, **thumbnails** in list.
- **Increment 2 (next):** **drop / choose an image FILE** → browser downscales (~1024px) to a data
  URI stored inline (no external host; large photos get compressed — fine for ambient).

## Definition (consolidated 2026-07-09; rotation from user feedback on live testing)

1. *What's the data?* → **Just an image** per item (URL or downscaled data URI), plus a
   **seeded starter set** of 5 inspiring bright wallpapers ("BEGIN.", "BREATHE.",
   "KEEP GOING.", "SHINE.", "REST WELL." — glowing art on pure black) so it never opens empty.
2. *Consuming moment?* → **Ambient, eyes-up on the glasses** — an image floating in view
   while doing something else; a real glasses case. Input happens on the phone.
3. *Key behavior in the moment?* → **Rotation** (user: "nice inspiring wallpaper rotating"):
   the fullscreen view auto-advances to the next wallpaper every `rotate` seconds (20);
   D-pad ↑/↓ still browses manually.

## Surface plan

- **Glasses (ambient, primary):** opens straight into fullscreen (newest first); auto-rotates
  every 20 s through the set; ↑/↓ manual browse; bright-on-black art suits the additive
  display (black = transparent). Empty collection → kit's "add on your phone" hint.
- **Mobile (authoring):** paste an image URL or drop/choose a file (downscaled to a data URI)
  in the add bar; delete/favorite from the list.
- **Desktop:** same as mobile (drag & drop convenient); optional bulk feed via
  `tools/push.py wallpaper --file apps/wallpaper/seed.json`.

## Design decisions (assumptions, not asked)
- **Item = just an image** (no name/title).
- **Glasses = fullscreen ambient:** opening an item shows the image **filling the whole 600×600
  canvas, edge to edge** (not a padded card). The list shows **thumbnails**.
- **Actions:** favorite ★, delete 🗑. No check-off.

## User flow (given / when / then)
- **Given** the app, **when** I paste an image URL and add, **then** it appears in the list as a
  thumbnail and opens fullscreen.
- **Given** the app, **when** I drop or choose an image file, **then** it is downscaled and added
  the same way (renders identically).
- **Given** an item, **when** I open it on the glasses, **then** the image **fills the 600×600
  canvas** edge to edge.
- **Given** an item, **when** I favorite (★) or delete (🗑) it, **then** the favorite persists /
  the item disappears from the list.

## Hard gate (flowtest — automated)
- create (URL) → appears in list; the `image` value round-trips
- favorite persists; delete removes from list; config conformance

## Soft gate (agent-judge on a screenshot)
- a dropped file is downscaled and renders; **fullscreen view fills the canvas**; list shows thumbnails
