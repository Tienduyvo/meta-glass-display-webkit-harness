# Stencil — verdict

**Result: PASS** (both halves green) — evaluated against a local `wrangler dev` (ephemeral D1),
control page served from the Worker at `/apps/stencil/control.html`, driven end-to-end in
headless Edge (Playwright, real clicks/keys/screenshots).

## HARD gate — flowtest
`python tools/flowtest.py stencil` → **PASS** (11/11: config conformance, create via POST,
list appearance, `image`/`label` round-trip, delete, bulk-replace persistence, soft-delete +
bulk-upsert-undelete regressions).

## SOFT gate — agent-judge (screenshots of the running app vs acceptance.md)

### Glasses surface (600×600, `#glass`)
- [x] Stencil tile (✏️) appears in the launcher; D-pad focus ring (bright cyan glow) reachable
  by arrows; Enter opens the app.
- [x] List row: **label as the big element** ("Star") + stencil thumbnail; focus ring; Enter →
  fullscreen.
- [x] Fullscreen: bright white star outline on **pure black** edge-to-edge — exactly the
  additive-display projection the app exists for. No chrome over the artwork (only the dim
  footer line, same as Wallpaper).
- [x] **Live swap**: with the glasses sitting on the fullscreen stencil, a new stencil POSTed
  from the phone replaced the display within one `refresh:3` cycle (cross → X, item count
  5, no interaction). Newest-first sort makes the top item the live surface.

### Control page (`control.html`)
- [x] Opens directly from the phone/desktop launcher with creds carried in the hash
  (zero-setup); Backend fieldset stays hidden when creds exist.
- [x] **Shapes**: 16-shape library; picking ☆ renders the star preview identically to what the
  glasses later showed. Line width / size sliders re-render live (visually confirmed at
  defaults; slider wiring shared by all modes).
- [x] **Text**: typing "HI" renders large auto-fitted outline letters.
- [x] **Photo**: uploading a test photo (dark circle + triangle on white) produced clean white
  edge line art of both shapes — Sobel + detail slider works.
- [x] **Send to glasses**: POST succeeded ("Star is on the glasses (top of the list)"), item
  landed in the collection and at the top of the glasses list.
- [x] Saved list loads from the collection (thumbnails + names, ✕ delete wired to DELETE).
- [~] Delete button exercised via flowtest's DELETE assertion, not clicked in the UI (low risk).

## Update (v2): redefined after the user's Define answers (photos first · glasses-driven · D-pad)
The launcher gained a fullscreen-app capability (both launchers, kit-level, see CHANGELOG
2026-07-09) and the control page now defaults to Photo. Verified in headless Edge against the
local worker (5 stencils in the collection):
- [x] Opening Stencil on the glasses lands **directly in the fullscreen stencil view** — no list
  step; footer reads `1/5 · Stencil · [↑↓] switch`.
- [x] **D-pad ↓** switches to the next stencil (X → cross, footer `2/5`), **↑** wraps back to
  `1/5` — one stencil at a time, never leaving the AR view.
- [x] **←** still backs out to the list (footer flips to `Stencil · 5 · [←] apps`), then launcher.
- [x] Control page opens with the **Photo tab first and active** (drop zone + edge-detail slider
  visible before any interaction); Shapes/Text demoted to secondary tabs.
- [x] Full flowtest re-run across all six registered apps after the launcher edit — all PASS
  (Wallpaper shares the fullscreen code path).

## Known constraints (by design — see acceptance.md)
- The overlay is head-locked (hardware): the user keeps their head still while tracing and
  re-aligns by eye. No anchoring.
- Colors restricted to bright white/green/cyan/amber — no dark fills (additive display).

## Eval environment note
`wrangler dev` initially crashed at startup (`workerd` std::terminate) — fixed by moving the
stale `worker/.wrangler` state aside and re-applying `schema.sql` to the fresh local D1
(`npx wrangler d1 execute glass_crud --local --file=schema.sql`).
