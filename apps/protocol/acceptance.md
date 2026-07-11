# Protocol — acceptance criteria

## Definition (Define round, 2026-07-11; owner is a PhD chemist, IT-life-science)
A **lab safety + procedure companion** for the glasses: run a synthesis/analysis
procedure as a **hands-free step checklist** (gloves on, eyes up), with each reagent's
**official hazard classification** and key properties surfaced from an authoritative
free source, and per-step amounts. Claude assists a qualified professional — it surfaces
public safety data and helps structure procedures the chemist provides/approves; it does
not invent routes for making hazardous or restricted substances. The emphasis is
**safety and correctness in a real lab**, not capability expansion.

- **One item = one procedure STEP:** `n` (step number, badge), `step` (the instruction),
  `reagent` (optional compound name), `amount` (optional, e.g. "2.5 g / 0.043 mol"),
  `hazard` (GHS pictograms + H-codes for the reagent, from PubChem), `note`, plus the
  standard `seen` (checked off).
- **Hazard data source:** PubChem (NIH, keyless PUG REST) — name → CID → GHS
  classification + MolecularFormula/MolecularWeight. Amounts/stoichiometry computed from
  MW when a target mol/mass is given. Papers (optional context) via Europe PMC/Crossref.
- **Procedures come from the user** (dictated/typed on the phone, or a JSON the chemist
  supplies); Claude formats steps, attaches hazards, checks stoichiometry — the chemist
  reviews and owns the final procedure. A committable template holds a GENERIC, harmless
  example procedure only (e.g. a recrystallization of a common salt) — no personal or
  sensitive protocols in the repo.

## Surface plan
- **Glasses** (checklist, D-pad — the recipe-steps use case): each row shows `n` BIG
  (badge) + the step instruction; ✓ checks it off hands-free (space/Enter). Enter →
  detail with the full step, reagent + `amount`, and the **hazard block** (GHS codes)
  bright and legible; ← back. **Empty state:** launcher hint — "load a procedure from
  your phone". Reagent hazards must be glanceable *before* you handle the bottle.
- **Mobile (phone):** the add bar builds/edits steps (step text, reagent, amount, note);
  a `control.html` "New procedure" helper is phase 2 (dictate a prep → Claude fills
  steps + hazards). Check-off syncs both ways.
- **Desktop (PC/agent):** `python tools/protocol_pipeline.py --push --procedure <file>`
  takes a procedure spec (steps + reagents + a target scale), enriches each step with
  PubChem hazards + computed amounts, pushes the checklist. `--template` for the seed.

## Given / when / then
- **Given** a procedure spec with reagents, **when** the pipeline runs, **then** the
  `protocol` collection holds one row per step with `n`, `step`, and — where a reagent
  is named and resolves on PubChem — a non-empty `hazard` (GHS H-codes) and `amount`
  scaled from MW; unknown reagents degrade gracefully (step still shows, hazard blank).
- **Given** steps exist, **when** the glasses open Protocol, **then** rows show step
  number big + instruction, ✓ checks off and persists, Enter shows the hazard block.
- **Given** an empty collection, **then** both surfaces show a worded empty state.
- **Given** the seed is committable, **then** it is a generic, non-sensitive example
  (`--template`), never a real/personal protocol.

## Safety note (standing)
This app surfaces PUBLIC hazard data (PubChem GHS) to make real lab work safer and
formats procedures the qualified user provides. It is an assistant to a professional
chemist, not a source of novel synthesis routes for dangerous materials; requests of the
latter kind are declined regardless of the app.
