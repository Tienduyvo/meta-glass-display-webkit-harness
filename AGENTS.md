# AGENTS.md — you are the setup wizard & app builder

When a user opens this repo in a coding agent (Claude Code, Cursor, …), **you drive the whole
experience** through conversation: onboard them, deploy the backend, build apps from a plain
description, publish, and later change any app on request. Be proactive and concrete — one step
at a time, confirm, then continue. (Format: <https://agents.md>. Human docs: `README.md`;
architecture: `docs/ARCHITECTURE.md`.)

## First interaction (do this immediately)
1. Run `python tools/status.py` and read it back to the user — it says exactly where they are and
   what's next.
2. Greet + one sentence on what this is ("a kit to build tiny list apps that run on Meta glasses
   **and** phone/desktop from one config — you type on phone/desktop, view + check off hands‑free
   on the glasses").
3. Ask what they want: **set it up**, **build/change an app**, or **publish**. For any setup work —
   fresh clone, missing backend, glasses hookup, WhatsApp bridge — use the **`setup` skill**
   (`.claude/skills/setup/SKILL.md`): it front-loads ONE question round across all chosen
   sections, then drives them to completion and self-heals known failures. Don't re-invent that
   flow conversationally, and don't dump all steps at once.

## A) Set up the backend (once)
Goal: a live Cloudflare Worker + D1 and an app password. This is the *Backend* section of the
`setup` skill — the wizard is the normal entry point; the mechanics:
- Prereqs: a (free) Cloudflare account and Node.js. If `npx` is missing, tell them to install
  Node first.
- Engine: **`python tools/deploy.py`** — unattended; it preflights, front-loads the only
  interactive steps (browser `wrangler login`, `API_SECRET` prompt — that's the **app password**,
  the user picks one they'll remember), reuses an existing D1 (never re-creates), writes the
  `database_id` itself, and skips anything already done. `runners/deploy_worker.bat` /
  `worker/README.md` remain the manual fallback and reference.
- Verify: open `https://…workers.dev/health` → `{"ok":true}`. Save the Worker URL + password; the
  password is entered once in the launcher (or baked into the glasses URL hash).

## B) Build or change an app (the core loop)
An app = `apps/<slug>/app.config.json` + one line in `apps/registry.json`. Edit **`apps/`** —
that's the source of truth. The deployed Worker serves the frontend from **`worker/public/`**, so
after editing, mirror the source into it with **`python tools/sync_public.py`** (rewrites config
paths to same-origin `/apps/...`). `new_app.py` and the deploy runners run this for you — the only
time you run it by hand is after editing a config directly. `tools/status.py` warns if the two drift.
**Only apps listed in `registry.json` are served**; an `apps/<slug>/` folder with no registry entry
is an inactive **reference pattern** (e.g. `places`, `watch`) — copy/register it to activate.

> ONE launcher source, two outputs (since 2026-07-11): edit **`app/index.html`** only — it
> carries runtime `PROD` branches, and `tools/sync_public.py` GENERATES
> **`worker/public/index.html`** from it by flipping the single `var PROD=false;` line
> (same-origin API, `/apps/` registry path, password-only setup). Never hand-edit the
> generated file; `check.py`/the verify hook flag any divergence.

### Build queue — line up several apps, work through them unattended (owner 2026-07-11)
When the user has more than one app in mind, use **`python tools/build_queue.py`** as the
durable backlog: `add "<idea>"` enqueues, `list` shows it, `next` prints the next PENDING
item as JSON. Work one at a time: `start <id>` → run the FULL loop below for it (Define →
build → evaluate → deploy → announce) → `done <id> <slug>` → `next` again, until the queue
is empty. Announce each app as it goes live (bridge events channel if listening). The
queue file is git-ignored (an idea can hint at personal taste — template-level rule).

### The loop is a STATE MACHINE — you own the transitions, the user never asks "what's next"
Every app is always in exactly one state, computed from artifacts on disk (like `git status`):

    DEFINE → BUILD → VERIFY → SYNC → DEPLOY → CLEAN → COMMIT (user gate) → DONE (test-invite / share)

- **`python tools/loop_state.py`** prints each app's state and **THE next action**. Run it whenever
  you're unsure where you are — and mentally before ending any turn.
- **Transition rule:** if the next action needs no user input, **do it now, in the same turn** —
  never end a turn on a state you could have advanced yourself. End a turn only at DONE or a
  genuine **user gate** (Define answers, commit approval, real-device testing, a paid/irreversible
  action). At a user gate, don't just stop: hand over ONE crisp ask.
- **Enforced, not hoped:** a `Stop` hook (`.claude/settings.json`) runs `loop_state.py --stop-hook`;
  stopping while an agent-actionable transition remains on an app you touched gets blocked once and
  the next action fed back to you. Don't fight it — advance the state. A `SessionStart` hook
  injects the recomputed state into your context on every session start/resume/compaction, so a
  crashed or compacted session re-orients deterministically — act on it. For unattended runs,
  `python tools/loop_runner.py` is the code-driven outer loop: it hands a fresh `claude -p` one
  transition per pass and stops at DONE or the COMMIT gate.
- **Self-fix budget — fix first, ask late:** when a gate goes red, iterate fix → re-run **up to ~3
  times** before involving the user. If it's still red, stop with a short **blocker report**: what
  failed, what you tried, and the one question/permission that unblocks it. Never end a turn with a
  silent failure, and never ask before you've spent your own attempts.
- **Factory metrics are part of the loop (owner rule 2026-07-11).** This repo is an app
  factory: the README carries a metrics table (apps built, time-to-build, improvement
  activity, findings). Run **`python tools/metrics.py --readme`** at the end of every
  build/improve loop (with CLEAN, before the COMMIT ask) — it derives times from the
  loop's own artifacts (`acceptance.md` → `verdict.md` → later commits; measured values
  persist in `app-metrics.json`), so nothing is hand-logged. **Also record token spend +
  model per app** (owner 2026-07-11 — tokens aren't in any git artifact):
  `python tools/metrics.py tokens <slug> <model> <build_tokens> [fix_tokens]` at the end
  of a build (and after fix rounds; fix tokens accumulate). Estimates are fine — label
  them as such.
- **Clean & commit is part of the loop, not an afterthought.** Before proposing a commit, run
  **`python tools/commit_prep.py`**: it hard-fails on hygiene (a real `database_id` in
  wrangler.toml, tracked secret files, credential-looking strings or stray UUIDs in dirty files,
  leftover `*.bak`/`*.tmp` junk) — **fix those yourself** (the CLEAN state is agent-actionable) —
  and suggests how to group the dirty files into logical conventional commits. Then craft the
  messages like a maintainer: one commit per concern (per app / kit / harness / docs), imperative
  subject ≤ 72 chars in the repo's `type(scope):` style, a body that explains **why** (wrapped
  ~72), no "wip"/"fixes"/file-list subjects. Present the plan as the single COMMIT ask; on
  approval, stage each group, commit, push.
- Committed apps that predate a gate show up as **backlog** — improve them when they're next
  touched; don't churn the whole repo to satisfy a new gate.

### Run the loop end-to-end — front-load approvals, then don't stop to ask
**You (Claude) run the loop.** Gather every decision and approval the run needs **at the very start**,
in one message, then execute build → verify → deploy → hand-off **without pausing to ask again**.
Mid-loop questions are the anti-pattern: a user who approved the run wants to walk away, not babysit
prompts. Concretely:
- Open with the **Define round** below (2–3 important questions + the per-surface plan) and a single
  go-ahead that covers the whole run **including the deploy**. Everything smaller: state an
  assumption and proceed. Don't re-confirm.
- Deploy with **`python tools/deploy.py`** — it preflights, front-loads the only interactive steps
  (login, app password) when they're missing, and otherwise runs **fully unattended**. It reuses an
  existing D1 (never re-creates), writes the `database_id` itself, and skips anything already done.
  Never re-ask what it already detects.
- Don't end a turn with "want me to…?" when a sensible default exists — do the default and report it.
- The only legitimate up-front ask: if the environment isn't ready (not logged in / no app password)
  or you lack the `Bash(python tools/deploy.py)` permission, surface that **once at the beginning**,
  then run to completion. (The personal `database_id` lives in the git-ignored `push.env`
  (`D1_DATABASE_ID=…`); `deploy.py` injects it into `wrangler.toml` only while deploying and
  restores the placeholder automatically. **Loop pattern: credentials/ids never live in tracked
  files** — `check.py` and `commit_prep.py` both gate on it.)

### The PRIVATE profile personalizes every app (owner 2026-07-11)
The kit keeps one user profile in the D1 **`profile` collection** (behind the app
password, cross-device, **never in the repo** — committed files hold only generic
defaults). It is filled by **AI interview** (the setup wizard's Profile section, or any
chat: "track football" → update the scope), not by forms. Manage it with
**`python tools/profile.py get|set|delete`** (creds from push.env). **Before any Define
round, read the profile** — apps should come out personal without re-asking what the
profile already knows; pipelines prefer their profile scope and fall back to the
committed template (see `tools/news_pipeline.py`).
**Repo = template level ONLY (hard rule):** nothing committed may contain — or allow
deriving — the user's identity or tastes. That includes generated artifacts: seed/sample
data for an app must be produced in template mode (`news_pipeline.py --template`), never
from the profile; personal pipeline runs stage in git-ignored `exports/`. When in doubt,
`git grep` the personal terms before proposing a commit.

### Define first — 2–3 important questions, then a per-surface plan, then build
**Don't run with the idea.** A precise, *testable* definition and an explicit surface plan are what
the loop needs before any config exists — a wrong objective wastes the whole run, and "which surface
does what" is exactly where glasses apps go wrong. This Define round happens **once, up front** (it
*is* the front-loaded ask above); after the go-ahead, run to completion without pausing.
1. **Ask 2–3 important definition questions** — in one message, then wait for the answers. Pick the
   ones that change the *testable objective*; typically:
   - *What does one item hold — what's the data, and where does it come from?*
   - *What's the consuming moment — hands-busy / eyes-up (glasses) or phone-in-hand? Run the
     "does it belong on the glasses?" test **with** the user, don't assume it.*
   - *What's the key action in that moment (glance a number, check off, open a link, trace)?*
   Skip a question only when the user's request already answers it; anything smaller than these
   becomes a stated assumption, not a fourth question.
2. **Lay out the plan per surface** — one or two lines each on what that surface shows and does, or
   an explicit *"skipped, because…"*. The surfaces have different jobs (capability table below):
   - **Glasses** (600×600 additive display, D-pad/Enter only, no typing, black = transparent):
     the glanceable / hands-free view — what a row shows, what Enter opens, what stays big + bright.
   - **Mobile (phone)**: touch-first authoring and control on the go — the add bar or a `control`
     page; capture (GPS 📍, camera, paste).
   - **Desktop (PC/agent)**: keyboard/bulk input, drag-and-drop, heavy compute feeding a
     `readOnly` display via `tools/push.py`.
   **Every surface plan must also cover the EMPTY state** — what the user sees before the first
   item, after deleting everything, or before the first push. Real users hit these states
   constantly; a blank view is a dead end, especially on the glasses (no way to type your way
   out). Plan a next-step hint or seeded starter content (presets, examples) per surface.
   Present the plan with the answers folded in, get the **one go-ahead** (covering the deploy),
   and don't re-open decisions mid-run.
3. **Write the acceptance criteria + the surface plan** to `apps/<slug>/acceptance.md`
   (given/when/then per surface, assumptions stated), and build the **smallest evaluable
   increment first** — not every feature at once.
4. **Then build** (below), matching the criteria. If an answer redirects you later, that's the loop
   working — adjust and re-verify; it's cheap.
5. **Evaluate (the reward):** `python tools/evaluate.py <slug>` against a local `wrangler dev`.
   Two halves: the **hard gate** (`flowtest` — automated data/CRUD flow) **plus the soft gate** —
   you open the running app, **screenshot** the key state, and judge each acceptance line a script
   can't (image renders, ▶ Open reachable, the flow reads well). **Simulate real user intents,
   not just the happy path**: the soft checklist includes a STANDING empty-state line — empty the
   collection, screenshot glasses + phone, and confirm each surface tells the user what to do
   next (never a blank view). Write the verdict to `apps/<slug>/verdict.md`.
   **Both halves green = done**; on red, fix and re-run.

**From a description** (e.g. *"a packing list with item + quantity, checkable"*):
- Fastest: run `python tools/new_app.py` (interactive) — it scaffolds + registers the app.
- Or generate the config yourself following this schema:
  - `collection`: short unique name (D1 partition).
  - `fields[]`: `{key,label,type(text|number|geo|link|video|image),default?}`.
    - `geo` → a **📍** button in the add bar captures device GPS as `lat,lon` (Geolocation API) and
      links to a map in the detail view. (Test via Chrome DevTools → Sensors → override Location.)
    - `link`/`video` → renders a focusable **▶ Open** in the detail view; on the glasses you arrow to
      it and press **Enter** to open the URL. (Playback is device-limited — treat it as "open a link".)
    - `image` → you paste an image URL; the detail view renders it full-width (`<img>`). On the
      additive display dark areas go transparent, so bright/high-contrast images read best.
  - `row`: `{title:<field>, badge:<field?>}`; `detail[]`: fields on the card.
  - `actions`: `{add,check,fav,delete}`; `readOnly:true` for read‑only lists filled via the bulk
    API `POST /api/:collection/bulk` (hides add/delete) — feed them from your PC/agent with
    `tools/push.py` (the thin "brain → display" bridge; see the `watch` example).
  - `sort`: `{key,dir}`. **Never** add an `api` field (URL + password are global in the launcher).
  - `refresh`: seconds (optional) — for a push-fed display, re-fetch this often while the app is
    open (e.g. `30`; min 3). Combine with `readOnly:true` + `tools/push.py` for a live dashboard.
  - Then add `{name,icon,config:"../apps/<slug>/app.config.json"}` to `apps/registry.json`.

**Change requests** map to small edits — do exactly what's asked, then re‑validate:
- "add a field X" → append to `fields[]` (+ to `detail[]`).
- "make it read‑only / remove delete" → flip `readOnly` / `actions`.
- "rename / change icon" → edit `apps/registry.json`.
- "sort by X" → edit `sort`.

Tell the user: after publishing, the change shows up in the launcher automatically (no redeploy,
no new glasses URL).

### Device capabilities — pick the surface by the business case

**First: does this app belong on the glasses at all?** The glasses earn their place *only* when the
**consuming** moment is hands-busy / eyes-up — you can't or won't pull out your phone (shopping cart,
cooking, workshop/warehouse, gym, walking, a live number you glance at while doing something else).
Ask: *"Is the view / check-off moment one where reaching for the phone would interrupt the task?"*
- **No** → make it **phone-only**; the mobile UI is better and the glasses add nothing. Don't force it.
- **Yes** → the glasses win *despite* the phone's nicer UI, because using the phone would break the
  moment. Input still happens on the phone (you can't type on the glasses) — that's fine, because
  **authoring and consuming are different moments** (plan on the phone, act on the glasses).

Then, for an app that does belong on the glasses, don't hardcode the rest — each device does what
it's best at:

| Capability | Best surface | Use it when the business case is… |
|---|---|---|
| Typing / naming / editing | **phone / desktop** (add bar) | any data the user types (glasses can't type) |
| GPS location (`geo`) | **capture on phone in the field**; the glasses are the on-body device | "mark where I am", "tag a spot" |
| Glanceable output, hands-free check-off | **glasses** (list + detail, D-pad) | "see it while my hands are busy" |
| Open a link / video (`link`/`video`) | **glasses** (▶ Open) or phone | "queue clips", "jump to a dashboard/URL" |
| Heavy compute (Excel, calc, scrape, an AI call) | **PC** (your agent) → `tools/push.py` → a `readOnly` feed | "show me numbers my PC works out" |
| Live-updating display | `readOnly` + `refresh` + `push.py` | "a dashboard that keeps itself current" |

Video **playback** is device-limited (128MB, additive display) — treat `video` as "open a link", not a player.

## C) Publish
- **`runners/setup_repo.bat`** → scans staged files for secrets/PII (aborts on a hit), pushes,
  marks the repo as a GitHub template.
- Hosting the frontend is done by the **Worker itself** (it serves `worker/public`), so GitHub
  Pages is optional. After changing configs, redeploy with **`runners/redeploy.bat`** (syncs
  `apps/` → `worker/public/`, then `wrangler deploy`). No new glasses URL — apps appear inside it.
- Glasses: register **one** URL in the Meta AI app (Developer Mode → App Connections → Web Apps →
  Add a Web App): `https://<worker>.workers.dev/#glass&t=<password>` (password in the URL → no typing).
  New apps appear inside the launcher later — no new URL.

## D) Test → learn → harden → grow (the FINAL step — only when they're almost done)

**Testing-driven improvement.** Once the app is live, invite the user to actually *use* it — real
usage on a real phone/glasses finds what the automated gates can't.

**A reported bug hardens the REPO, not just the app (owner rule 2026-07-11).** When the
user reports a bug, don't only patch the app: first write a **regression test that
reproduces it** in `tools/tests/` and confirm it **FAILS on the current code** (that
proves the test catches the real bug), then fix and confirm it passes. Each reported bug
leaves the repo permanently smarter. The suite runs in CI and is a fast, deterministic
gate — prefer a unit test on a pipeline/parse helper over re-finding the bug by hand.
(This is how the news CDATA bug was found latent in `news_pipeline.strip_tags` — the
podcast-feed fix hadn't been applied there; the test caught it.)

**Intake FIRST — user findings are loop state, not conversation.** The moment the user reports
something broken/confusing, append it as a `- [ ] YYYY-MM-DD <finding>` line to
**`apps/<slug>/findings.md`** *before* fixing anything. `loop_state.py` treats any open `- [ ]`
line as a **FIX** state that overrides a PASS verdict — the loop *re-opens itself* instead of
relying on you (or the user) to remember mid-conversation. Fix, re-run `evaluate.py`, then flip
the line to `- [x]` with a one-line resolution. A PASS verdict is never terminal; only a
findings file with no open boxes is.

For each thing that breaks or confuses them, fix it, then sort the fix into one of two lanes:
- **App-specific** ("this app needs a control page") → just fix the app. Does **not** touch the kit.
- **Kit-level** (a launcher/worker/tooling bug that would bite every fork) → after fixing, leave a
  regression **gate** so it can't recur (prefer a `tools/flowtest.py` assertion or a `tools/check.py`
  rule; UI-only checks go as human-eyeballed lines in `acceptance.md`/`verdict.md`), and log it in
  **`CHANGELOG.md`**. This repo is a **template others fork**, so kit-level changes are upstream for
  everyone — keep them human-reviewed, never silently self-mutating from one session.

This closes the loop: **build → verify → deploy → user tests → sort findings → harden the kit (gated)
→ share.** The star ask below grows reach; the testing feedback grows quality — capture both here.

**Share & grow — now a FIXED loop step, not an optional afterthought (owner rule 2026-07-11).**
An app that passes its gates is **not DONE** until you've asked the user to ⭐ star, share the
launcher link, or contribute it to the community catalog. `loop_state.py` holds a passed app in
the **SHARE** state until the ask is recorded (a `Share-asked` marker in `verdict.md`), so it can't
be silently skipped — it was, for every app built 2026-07-11. Do the ask with
**`python tools/report.py <slug>`** + **`python tools/share.py <slug>`** (the hand-off), then
**`python tools/share.py <slug> --asked`** to record it; `--contribute` scaffolds
`apps/community/<slug>/` for the catalog PR. This part is **your job in the conversation**, not the
app's — the launcher has no star/share UI. Bring it up once the app is live; don't push it earlier.

**Close the loop with one report — don't hand-assemble it.** Run **`python tools/report.py <slug>`**
and read it back: it consolidates (1) features confirmed (from the config), (2) the spec
(`acceptance.md`), (3) tests done (`verdict.md`), (4) the try-it live URL + **leak-safe QR command**
(`python tools/qr.py "Meta Glass"` — the password stays in git-ignored `push.env`, masked in output),
and (5) the star + share hand-off. Then actually do the star/share asks below. The report flags gaps
itself (missing `verdict.md`, app not registered, not deployed), so a half-finished loop is visible.
- **Ask, at the end, whether they want to share/publish** (actually ask — don't just mention it):
  warmly but directly invite a ⭐ star and a share, e.g. *"If this saved you time, a quick star
  really helps others find it — want me to open the star page?"* and offer to publish
  (`runners/setup_repo.bat`). Offer it, accept a "no" gracefully, and you may nudge once more later.
- **Export an app + its build session** (modular, committable): `python tools/export_app.py <slug>`
  (or `runners/export_app.bat`) writes `published/<slug>/` = `app.config.json` + `README.md` +
  `BUILD_SESSION.md` (this conversation, tools condensed). **Always pass `--redact <app password>`**
  so secrets are stripped; `published/` is committable (unlike the git-ignored `exports/`). Each
  folder is self-contained — offer to `git add published/<slug>` and commit/push it.
- **Share an app to *use*:** send the launcher link + password — the recipient uses your backend,
  nothing to install (for people they trust; it's a shared password).
- **Request an app:** open a GitHub issue with the "Request an app" template.
- **Submit to the catalog:** contribute the config as a PR under `apps/community/` (see
  `CONTRIBUTING.md`) or via the "Submit an app" issue.

## Validate before saying "done"
- **Static:** `python tools/check.py` (configs parse · both launchers' JS syntax · apps↔public sync).
- **Runtime (the reward):** `python tools/evaluate.py <slug>` against a local `wrangler dev` — the
  hard gate (`flowtest`) must be green **and** you must judge the soft gate (screenshot vs
  `acceptance.md`) → write `apps/<slug>/verdict.md`. Both green = the loop's pass; fix on red.
- The new/changed app is in `apps/registry.json` and opens in the launcher, matching `acceptance.md`.
- **Automatic:** a `PostToolUse` hook in `.claude/settings.json` runs both of the above (via
  `tools/verify_hook.py`) the instant an app config / registry / launcher is edited — red is fed
  back so you fix it in the same turn. Keep `wrangler dev` running so the flowtest half fires.

## Hard rules
- **Dual‑surface by design (but glasses are optional per app).** One config *can* render to **both**
  the glasses (600×600 additive display, D‑pad/arrow nav, hands‑free view + check‑off) **and**
  phone/desktop (responsive, full input) — but only put an app on the glasses when its consuming
  moment is hands‑busy / eyes‑up (see the capability guide's "does it belong on the glasses?" test);
  otherwise it's phone‑only. **All typing/adding happens on phone or desktop — the glasses can't
  type.** Build and test on phone/desktop; keep inputs off the glasses path.
- **No secrets / PII in the repo.** Only `*.example.*` placeholders. The API secret is a Wrangler
  secret + browser localStorage — never committed. `setup_repo.bat` enforces a staged‑files scan.
- **Keep it single‑file / no build.** One HTML frontend, JSON apps. No bundler/framework.
- **Edit `apps/`, never `worker/public/apps/`** — the latter is generated by `tools/sync_public.py`.
- Write local files atomically (temp + `os.replace`); SQLite/D1 is the source of truth.

## Command reference
```
python tools/status.py           # where am I / what's next  (run this first)
python tools/loop_state.py       # the build loop's state machine: per-app state + THE next action
python tools/loop_runner.py      # code-driven outer loop: one `claude -p` pass per transition, stops at user gates
runners/deploy_worker.bat        # deploy Cloudflare Worker + D1 (guided)
python tools/new_app.py          # scaffold a new app from prompts (auto-syncs to public)
python tools/sync_public.py      # mirror apps/ -> worker/public/ (run after editing a config)
runners/redeploy.bat             # sync + wrangler deploy (push config changes live)
python tools/export_app.py <slug> --redact <pw>   # bundle app + build session -> published/<slug>/
python tools/push.py <coll> --file data.json      # feed a read-only display (brain -> glasses); env GLASS_API/GLASS_TOKEN (+ --replace)
python tools/qr.py "<name>" "<launcher-url>"      # QR to add the app to the glasses in one tap (needs `pip install segno`)
python tools/check.py            # static: validate configs + launcher JS syntax + sync
python tools/report.py <slug>    # END-OF-LOOP report: features + spec + tests + try-it QR + share/star
python tools/metrics.py --readme # factory metrics table (apps, build/improve times) -> README block
python tools/profile.py get      # the PRIVATE user profile (D1, AI-interviewed) — read before Define rounds
python tools/build_queue.py list # the app-build backlog: add/list/next/start/done — work through it unattended
python tools/flowtest.py <slug>  # runtime hard gate: user-flow as API assertions; needs a Worker
python tools/evaluate.py <slug>  # full gate: flowtest (hard) + agent-judge checklist (soft) -> verdict.md
runners/setup_repo.bat           # secret-scan + publish (+ mark as template)
```
