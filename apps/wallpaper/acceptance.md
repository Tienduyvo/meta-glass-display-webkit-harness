# Acceptance criteria — Wallpaper (ambient)

**Business case:** an **ambient image in your field of view while wearing the glasses** — a
"wallpaper" you glance at. A real glasses case (ambient view). Input happens on the phone.

**Increments (smallest evaluable first):**
- **Increment 1 (built):** add by **image URL**, **fullscreen** ambient view, **thumbnails** in list.
- **Increment 2 (next):** **drop / choose an image FILE** → browser downscales (~1024px) to a data
  URI stored inline (no external host; large photos get compressed — fine for ambient).

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
