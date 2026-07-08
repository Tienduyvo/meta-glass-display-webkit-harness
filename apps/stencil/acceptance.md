# Stencil — acceptance criteria

**What it is:** a drawing projector. The glasses show a bright line-art shape on a black
(= transparent on the additive display) background, so the outline appears to float on the
paper in front of you — you trace it with a pencil, hands-free. The phone is the authoring
surface: a control page generates stencils (shape library, outline text, photo→line art)
and sends them to the glasses.

**Does it belong on the glasses?** Yes — the consuming moment is the definition of
hands-busy / eyes-up: one hand holds the pencil, the other the paper, eyes on the page.
Pulling out a phone mid-stroke would break the moment.

## Assumptions (defaulted, not asked)

- Stencils are stored as pre-rendered 600×600 PNG data URLs (white/bright strokes on black)
  in the `stencil` collection — the glasses just display an image, no client-side drawing.
- Newest-first sort + `refresh: 3` gives live control: sending a new stencil from the phone
  while the glasses sit on the top item swaps the displayed stencil within ~3 s.
- Three generator modes cover the use case: **Shapes** (parametric library), **Text**
  (outline letters for lettering practice), **Photo** (edge-detect an uploaded/pasted photo
  into traceable line art).
- Stroke color is limited to bright, additive-display-friendly options (white, green, cyan,
  amber). No dark fills anywhere.
- No mirroring: you look *through* the glasses at the paper, so the overlay is trace-direct.

## Flow (given / when / then)

- **Given** the launcher on the glasses, **when** I open Stencil and Enter on a row,
  **then** the stencil renders fullscreen — bright lines on pure black, no chrome over it.
- **Given** the launcher on phone/desktop, **when** I tap Stencil, **then** the control
  page opens directly with credentials carried over (zero setup).
- **Given** the control page, **when** I pick a shape from the library, **then** the
  600×600 preview shows it as bright strokes on black, exactly as the glasses will.
- **Given** a shape in the preview, **when** I adjust size or line width, **then** the
  preview re-renders live.
- **Given** the Text tab, **when** I type a word, **then** the preview shows large outline
  letters auto-fitted to the canvas.
- **Given** the Photo tab, **when** I choose or paste a photo, **then** the preview shows
  its edges as bright line art, tunable with a detail slider.
- **Given** any preview, **when** I press "Send to glasses", **then** a new item with a
  name + PNG lands in the `stencil` collection and appears at the top of the glasses list.
- **Given** the glasses showing the newest stencil fullscreen, **when** I send another from
  the phone, **then** the glasses display swaps to it within ~3 s (refresh).
- **Given** saved stencils in the control page list, **when** I tap delete, **then** the
  item is removed from the collection and the glasses list.

## Out of scope (first increment)

- Anchoring/stabilizing the overlay to the paper (the display is head-locked; the user
  keeps their head still or re-aligns — that's inherent to the hardware).
- Multi-step tutorials (step 1/2/3 layered drawing guides) — a later increment.
