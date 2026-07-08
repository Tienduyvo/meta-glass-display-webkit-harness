# Meta Glass Display WebKit Harness

<!-- Badges/links point at Tienduyvo/… — if you reuse this template, swap in your GitHub user. -->
[![CI](https://github.com/Tienduyvo/meta-glass-display-webkit-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/Tienduyvo/meta-glass-display-webkit-harness/actions/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](./LICENSE)

[![Star](https://img.shields.io/github/stars/Tienduyvo/meta-glass-display-webkit-harness?style=social)](https://github.com/Tienduyvo/meta-glass-display-webkit-harness/stargazers)
· [Fork](https://github.com/Tienduyvo/meta-glass-display-webkit-harness/fork)
· [Use this template](https://github.com/Tienduyvo/meta-glass-display-webkit-harness/generate)
· [Request an app](https://github.com/Tienduyvo/meta-glass-display-webkit-harness/issues/new?template=request-an-app.yml)

A **starter kit for building your own tiny CRUD list apps** that run on Meta Ray‑Ban Display
glasses and phones — shopping lists, to‑do lists, packing lists, watchlists, whatever you like.

**You build the apps.** Describe an app (or answer a few prompts) → get a working glasses + mobile
app. No framework, no build step: apps are just JSON config, served as one static HTML file and
backed by a tiny serverless CRUD API — both from a single Cloudflare Worker. Ship as many apps as
you want from one launcher.

**One config, two surfaces.** Because you **can't type on the glasses**, every app is built to run
on **phone/desktop *and* glasses in parallel**: you add and edit items on the phone or desktop
(full keyboard), and **view + check them off hands‑free on the glasses**. You develop and test the
whole thing in a normal browser; the glasses layout renders from the exact same config (600×600
additive display, arrow/D‑pad nav), following Meta's display guidelines.

> **This is the kit, not a finished product.** You (the builder) set it up once. The people who
> *use* your finished apps never touch GitHub — they just open a link (or you add it to your
> glasses). See *Who does what* below.

<sub>Deep dive: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · building apps with an AI agent:
[`AGENTS.md`](AGENTS.md)</sub>

---

## What you can build

Any small list you want on your face and in your pocket. The **glasses superpower** is hands‑free
check‑off while your hands are busy — walking the aisles, cooking, at the gym, picking in a
warehouse.

**Check‑off lists (full CRUD — add / check / delete):**
- 🛒 **Shopping / grocery list** — tick items off as you grab them
- ✅ **To‑do / tasks** for the day
- 🎒 **Packing list** for a trip
- 🍳 **Recipe steps** — hands‑free while cooking
- 🏋️ **Workout checklist** — sets/reps
- 🎁 **Gift ideas**, 🍷 **tasting log**, 💊 **meds/supplements**

**Read‑mostly lists (mark seen / favorite):** set `readOnly:true` and fill the collection from an
external source via the bulk API (`POST /api/:collection/bulk`) — e.g. a watchlist, a price/stock
feed, a reading list.

**Trackers:** 🔁 habits / streaks, 💼 job applications, 📦 inventory (pantry, tools, collectibles).

Every one of these is just an `app.config.json`. Tell the agent *"build a to‑do list"* or run
`python tools/new_app.py` — and it shows up in the launcher next to the others, no new setup.
Active in the launcher: **buy-list** (full CRUD), **to-do** (task · priority · due), and
**wallpaper** (an `image` gallery). Also in `apps/` as **unregistered reference patterns** (copy
into a slug + add to `apps/registry.json` to activate): **places** (a 📍 GPS `geo` field) and
**watch** (a read-only, auto-refreshing feed fed from your PC via `tools/push.py`, with ▶ Open
video/link items). Only registered apps are served.

---

## Fastest path — let an agent set you up

One place in, one place to change things — like Claude Code or Cursor:

```bash
git clone <your copy of this repo> && cd meta-glass-display-webkit-harness
# open the folder in Claude Code or Cursor, then just say:
#   "set me up"      or      "add a packing list with item + quantity, checkable"
```

The agent follows [`AGENTS.md`](AGENTS.md) / [`CLAUDE.md`](CLAUDE.md): it runs `python
tools/status.py` to see where you are, walks you through deploying the backend, **builds or
changes apps from your description**, and publishes — all in the same conversation. Want to add a
field or a new list later? Just say so, in the same place.

> Not using an agent? Run `python tools/status.py` anytime — it prints your status and the exact
> next command. The manual steps are below.

---

## Get your own copy (manual path)

Click **“Use this template” → Create a new repository** at the top of this repo (or `gh repo
create --template …`). You now own a copy to build in. *(No need to fork.)*

## Build your first app (3 steps)

**1 — Deploy the backend once.** Double‑click **`runners/deploy_worker.bat`** → it walks you
through Cloudflare login, creates a D1 database, sets your **app password** (`API_SECRET`), and
deploys. You get a Worker URL that serves both the launcher and the API.

**2 — Make an app.** Either:
- **Generator:** double‑click **`runners/new_app.bat`** → answer a few prompts (name, fields,
  read‑only?) → it writes `apps/<name>/app.config.json`, registers it, and syncs it into
  `worker/public`. No JSON by hand.
- **AI agent:** point any coding agent at this repo and say *“add a packing‑list app with item +
  quantity, checkable”*. It follows [`AGENTS.md`](AGENTS.md) and generates the config.
- **By hand:** copy `app/app.config.example.json`, add a line to `apps/registry.json`, then run
  `python tools/sync_public.py`.

**3 — Push it live.** Double‑click **`runners/redeploy.bat`** (syncs `apps/` → `worker/public` and
redeploys). New apps appear in the launcher automatically — no new glasses URL. To open‑source your
kit, run **`runners/setup_repo.bat`** (scans for secrets, pushes, marks the repo as a template).

That's it. Add more apps anytime with `new_app.bat` + `redeploy.bat`.

---

## Who does what

| Role | Does | Touches GitHub / deploy? |
|---|---|---|
| **Builder** (you) | uses this kit, deploys the Worker once, builds apps | yes, once |
| **User** of a finished app (you, or people you share with) | opens the launcher **link**; on glasses, registers **one** URL in Developer Mode | **no** |

So: to hand an app to a friend or family, you send them **the link** — not this repo. They don't
install anything. (Making apps installable by *strangers who set up their own backend* is out of
scope — that would need multi‑user accounts / hosted SaaS.)

## Using a finished app

- **Set up once (per device):** open the Worker URL on the phone; it asks once for your **password**
  (stored in the browser — the API URL is the site itself). For glasses, register one URL that
  carries the login in the hash: `https://<worker>.workers.dev/#glass&t=<password>` (no typing on
  the glasses). Or run `python tools/qr.py "Meta Glass" "<that URL>"` and **scan the QR with your
  phone to add it in one tap** (opens the Meta AI app via its deep link).
- **Launcher → pick an app → use it.** Glasses controls: **▲▼** move · **Enter** open/detail ·
  **◀** back · **Space/c** check · **f** favorite · **Del** delete. Phone: tap tiles/rows, use the
  ✓ / ★ / 🗑 buttons and the add bar. **Offline‑tolerant** — edits queue and sync when online.

## Layout

```
worker/          Cloudflare Worker: CRUD API on D1 + serves the frontend from worker/public
  public/        the launcher (index.html) + synced app configs the Worker serves
app/             local-dev launcher (one HTML file; you type the Worker URL)
apps/            your apps: <name>/app.config.json + registry.json (only registered ones are served; places/watch are inactive patterns)
tools/           status.py · new_app.py · sync_public.py · push.py · qr.py · export_app.py
                 check.py · flowtest.py · evaluate.py  (the define→test→verify build loop)
runners/         deploy_worker.bat · new_app.bat · redeploy.bat · export_app.bat · setup_repo.bat
```

## Rules of the kit
- **No secrets / PII in the repo.** Only `*.example.*` placeholders. The password is a Wrangler
  secret + browser localStorage — never committed. `setup_repo.bat` scans staged files first.
- **No build step.** One HTML file + JSON. Don't add a bundler/framework.
- **Edit `apps/`, then sync.** `worker/public/apps/` is generated by `tools/sync_public.py` — never
  edit it by hand.

## License
MIT — see [`LICENSE`](LICENSE).
