# Contributing

## ⭐ Support the project
If this is useful, **Star** and **Fork** the repo (buttons at the top of the page) — that's the
whole "engagement" mechanism, no account setup needed on our side.

## Share an app
- **Let someone use it:** send them your launcher link + password — they use your backend, nothing
  to install. (For people you trust; it's a shared password.)
- **Let another builder reuse the config:** open a PR adding `apps/community/<slug>/app.config.json`
  (copy the schema from `app/app.config.example.json`; **no `api`, no password**), or send the
  folder produced by `python tools/export_app.py <slug> --redact <password>`. Keep it generic.

## Request an app
Open an issue with the **“Request an app”** template — say what it should track and which fields.
You (or an agent following `AGENTS.md`) can then build it.

## Ground rules
- **No secrets / PII** in configs (the API URL + password are global, entered once in the launcher).
- Keep apps single‑purpose and small. Be kind in issues/PRs.
