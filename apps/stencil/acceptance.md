# Stencil — acceptance criteria

**What it is:** a drawing projector. The glasses show a bright line-art stencil on a black
(= transparent on the additive display) background, so the outline appears to float on the
paper in front of you — an AR tracing effect. The phone is setup-only: a control page turns
**your photos** (primary), shapes, or text into stencils and sends them to the glasses.

## Definition (user-answered, 2026-07-09)

1. *What's the content?* → **Photos/images first** — converting the user's own pictures to
   traceable line art is the main job; the shape library and outline text are secondary.
2. *Which surface drives?* → **Glasses are the main driver (the AR effect); phone is only for
   setup** (choose photo, tune, send).
3. *Interaction model?* → **Keep it simple: one stencil at a time**, fullscreen; **D-pad
   ↑/↓ moves to the next/previous stencil** without leaving the view.

## Surface plan

- **Glasses (primary):** opening Stencil lands **directly in the fullscreen stencil view**
  (newest first) — no list step. ↑/↓ = next/prev stencil (wraps), ← = back (list, then
  launcher). Footer shows `n/total`. Bright lines on pure black only.
- **Phone (setup only):** control page opens from the launcher with creds carried over.
  **Photo tab first + default** (choose / drag / paste → Sobel line art, edge-detail slider);
  Shapes and Text tabs behind it; line width / size / bright-color controls; Send; saved list
  with delete.
- **Desktop:** same control page (drag & drop convenient); no bulk/agent feed — skipped,
  nothing in this app needs PC compute.

## Assumptions (defaulted, not asked)

- Stencils are pre-rendered 600×600 PNG data URLs (bright strokes on black) in the `stencil`
  collection — the glasses only display images.
- `refresh: 3` keeps the open view live: a new send from the phone appears on the glasses
  within ~3 s (newest-first = top item).
- Stroke colors limited to white/green/cyan/amber (additive display; no dark fills).
- No mirroring — you look *through* the glasses at the paper, tracing is direct.

## Flow (given / when / then)

- **Given** the launcher on the glasses, **when** I open Stencil, **then** I land directly in
  the fullscreen stencil view (newest stencil) — bright lines on pure black, no list step.
- **Given** the fullscreen view with several stencils saved, **when** I press D-pad ↓ (or ↑),
  **then** the next (or previous) stencil replaces the view and the footer shows `n/total`.
- **Given** the launcher on phone/desktop, **when** I tap Stencil, **then** the control page
  opens directly, credentials carried over, with the **Photo tab already active**.
- **Given** the Photo tab, **when** I choose, drag or paste a photo, **then** the preview
  shows its edges as bright line art, tunable with the edge-detail slider.
- **Given** the Shapes / Text tabs, **when** I pick a shape or type a word, **then** the
  preview shows it as bright strokes / large auto-fitted outline letters.
- **Given** any preview, **when** I adjust size or line width, **then** it re-renders live.
- **Given** any preview, **when** I press "Send to glasses", **then** a new item lands in the
  `stencil` collection and becomes the glasses' displayed stencil within ~3 s.
- **Given** saved stencils in the control page list, **when** I tap ✕, **then** the item is
  removed from the collection and from the glasses rotation.

## Out of scope (first increment)

- Anchoring the overlay to the paper (display is head-locked; keep your head still and
  re-align by eye — inherent to the hardware).
- Multi-step guided drawing sequences (proportions → details); revisit after real tracing use.
