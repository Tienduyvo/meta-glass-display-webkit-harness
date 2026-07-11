# Protocol — evaluation verdict (2026-07-11)

## HARD gate — flowtest
PASS — all assertions green against local `wrangler dev` (CRUD: add/check/fav/delete,
all fields round-trip, bulk replace, soft-delete + un-delete).

## SOFT gate — agent-judge (DOM assertions on the running app; generic example data)
- [x] Pipeline enriches a procedure spec with PubChem (NIH, keyless): reagent name →
      CID → GHS H-codes + MolecularFormula/MolecularWeight; amounts computed from MW
      (benzoic acid 2 g → 0.0164 mol asserted). Unknown reagents degrade gracefully
      (step shows, hazard "no GHS data"). Ubiquitous solvents (water) guarded from
      PubChem's aggregated GHS noise → "low hazard" instead of spurious H-codes.
- [x] Glasses checklist: rows show step number BIG (badge) + instruction; space/Enter
      checks a step off hands-free (asserted persists); Enter → detail with reagent
      (formula), computed amount, and the ⚠ GHS hazard block (H302/H315… asserted).
- [x] Phone: the add bar builds/edits steps (standard CRUD); check-off syncs.
- [x] STANDING — EMPTY STATE: launcher's add-on-phone hint; template seed ships the
      example procedure.
- [x] Repo stays template-level + non-sensitive: the committed example is a textbook
      recrystallization of benzoic acid — no personal or sensitive protocols in git.

## Safety posture (standing)
Surfaces PUBLIC hazard data (PubChem GHS) to make real lab work safer and formats
procedures the qualified chemist provides/approves. Assistant to a professional, not a
source of novel routes for hazardous/restricted substances — such requests are declined
regardless of the app. Hazard codes are directional aids; the chemist owns the final
procedure and consults the primary SDS.

## Known limits
- PubChem GHS is a crowd-aggregated section; H-code sets can be broad (err toward
  over-warning). Reagent must be a name PubChem resolves (common names/CAS work best).

**Overall: PASS** (both halves green).
