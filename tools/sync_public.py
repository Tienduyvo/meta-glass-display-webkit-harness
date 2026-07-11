# -*- coding: utf-8 -*-
"""Mirror app configs from the source tree into the Worker's served tree.

The deployed Worker serves the frontend from ``worker/public`` (see the
``[assets]`` block in ``worker/wrangler.toml``). The apps you edit live in the
source tree ``apps/``. This script keeps the two in sync so a change under
``apps/`` actually reaches the live frontend:

- copies every ``apps/<slug>/app.config.json`` -> ``worker/public/apps/<slug>/app.config.json``
- regenerates ``worker/public/apps/registry.json`` from ``apps/registry.json``,
  rewriting each ``config`` path from ``../apps/<slug>/..`` (relative — the local
  dev launcher ``app/index.html``) to ``/apps/<slug>/..`` (absolute, same-origin —
  the production launcher ``worker/public/index.html``).
- prunes orphan app folders under ``worker/public/apps`` that no longer exist in ``apps/``.

- generates ``worker/public/index.html`` from ``app/index.html`` (owner decision
  2026-07-11 — maintaining two launcher copies by hand doubled every UI change):
  the launcher is a SINGLE SOURCE with runtime ``PROD`` branches; this script flips
  exactly one line (``var PROD=false`` -> ``true``). Edit only ``app/index.html``.

Run by hand, or automatically from ``tools/new_app.py`` and the deploy runners:
    python tools/sync_public.py
"""
import os, re, json, sys, shutil

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_APPS = os.path.join(ROOT, "apps")
SRC_REG = os.path.join(SRC_APPS, "registry.json")
PUB_APPS = os.path.join(ROOT, "worker", "public", "apps")
PUB_REG = os.path.join(PUB_APPS, "registry.json")
SRC_LAUNCHER = os.path.join(ROOT, "app", "index.html")
PUB_LAUNCHER = os.path.join(ROOT, "worker", "public", "index.html")
PROD_FLAG, PROD_ON = "var PROD=false;", "var PROD=true;"


def gen_launcher_text():
    """The production launcher = the dev launcher with the PROD flag flipped.
    Fails loudly if the flag is missing/duplicated — that means app/index.html
    was restructured and the single-source contract broke."""
    t = open(SRC_LAUNCHER, encoding="utf-8").read()
    n = t.count(PROD_FLAG)
    if n != 1:
        raise SystemExit("sync_public: expected exactly one %r in app/index.html, found %d"
                         % (PROD_FLAG, n))
    return t.replace(PROD_FLAG, PROD_ON, 1)


def atomic_write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def to_abs(cfg_path):
    """'../apps/todo/app.config.json' -> '/apps/todo/app.config.json' (same-origin)."""
    m = re.search(r"apps/.*$", cfg_path or "")
    return "/" + m.group(0) if m else cfg_path


def _read_json(path):
    return json.load(open(path, encoding="utf-8"))


# Servable per-app assets for "page apps" (their own HTML endpoint, e.g. the timer's control.html).
# app.config.json is mirrored separately; dev-only docs (*.md) are deliberately NOT served.
ASSET_EXTS = (".html", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico")


def asset_files(slug):
    d = os.path.join(SRC_APPS, slug)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d)
                  if os.path.isfile(os.path.join(d, f)) and f.lower().endswith(ASSET_EXTS))


def _copy_bytes_if_changed(src, pub, actions, label):
    with open(src, "rb") as f:
        data = f.read()
    if (not os.path.exists(pub)) or open(pub, "rb").read() != data:
        os.makedirs(os.path.dirname(pub), exist_ok=True)
        tmp = pub + ".part"
        with open(tmp, "wb") as f:
            f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, pub)
        actions.append("copied " + label)


def source_slugs():
    """Slugs REGISTERED in apps/registry.json that also have a config file.
    Unregistered apps/<slug>/ folders are inactive reference patterns — neither
    served into worker/public nor shown in the launcher (register them to activate)."""
    try:
        reg = json.load(open(SRC_REG, encoding="utf-8"))
    except Exception:
        return []
    out = []
    for a in reg.get("apps", []):
        m = re.search(r"apps/([^/]+)/", a.get("config", ""))
        slug = m.group(1) if m else None
        if slug and os.path.isfile(os.path.join(SRC_APPS, slug, "app.config.json")):
            out.append(slug)
    return out


def drift():
    """Return a list of human-readable reasons the served tree is out of sync.
    Empty list means apps/ and worker/public/apps/ match."""
    issues = []
    for slug in source_slugs():
        src = os.path.join(SRC_APPS, slug, "app.config.json")
        pub = os.path.join(PUB_APPS, slug, "app.config.json")
        if not os.path.exists(pub):
            issues.append(f"{slug}: missing in worker/public")
        elif open(src, encoding="utf-8").read() != open(pub, encoding="utf-8").read():
            issues.append(f"{slug}: config differs from worker/public")
        # per-app page assets (control.html etc.)
        assets = asset_files(slug)
        for fn in assets:
            ap = os.path.join(PUB_APPS, slug, fn)
            if not os.path.exists(ap):
                issues.append(f"{slug}/{fn}: missing in worker/public")
            elif open(os.path.join(SRC_APPS, slug, fn), "rb").read() != open(ap, "rb").read():
                issues.append(f"{slug}/{fn}: differs from worker/public")
        # extra served files not backed by source (e.g. a renamed/removed page)
        pubdir = os.path.join(PUB_APPS, slug)
        if os.path.isdir(pubdir):
            keep = set(assets) | {"app.config.json"}
            for fn in sorted(os.listdir(pubdir)):
                if os.path.isfile(os.path.join(pubdir, fn)) and fn not in keep:
                    issues.append(f"{slug}/{fn}: orphan file in worker/public (not in apps/)")
    # registry
    try:
        want = {"apps": [{"name": a.get("name"), "icon": a.get("icon"),
                          "config": to_abs(a.get("config", ""))}
                         for a in _read_json(SRC_REG).get("apps", [])]}
        have = _read_json(PUB_REG)
        if have.get("apps") != want["apps"]:
            issues.append("registry.json differs from worker/public")
    except Exception:
        issues.append("registry.json unreadable in one of the trees")
    # orphans
    if os.path.isdir(PUB_APPS):
        src_set = set(source_slugs())
        for name in sorted(os.listdir(PUB_APPS)):
            d = os.path.join(PUB_APPS, name)
            if os.path.isdir(d) and name not in src_set:
                issues.append(f"{name}: orphan folder in worker/public (not in apps/)")
    # generated launcher (hand-edits to worker/public/index.html get flagged here)
    try:
        if open(PUB_LAUNCHER, encoding="utf-8").read() != gen_launcher_text():
            issues.append("index.html: worker/public copy differs from generated (edit app/index.html, then sync)")
    except SystemExit as e:
        issues.append(str(e))
    except OSError:
        issues.append("index.html: missing in worker/public")
    return issues


def sync(verbose=True):
    """Make worker/public/apps mirror apps/. Returns the list of actions taken."""
    actions = []
    slugs = source_slugs()

    # 1) copy each app config
    for slug in slugs:
        src = os.path.join(SRC_APPS, slug, "app.config.json")
        pub = os.path.join(PUB_APPS, slug, "app.config.json")
        text = open(src, encoding="utf-8").read()
        if not os.path.exists(pub) or open(pub, encoding="utf-8").read() != text:
            atomic_write(pub, text)
            actions.append(f"copied {slug}/app.config.json")
        # copy per-app page assets (control.html etc.), and prune served files no longer in source
        assets = asset_files(slug)
        for fn in assets:
            _copy_bytes_if_changed(os.path.join(SRC_APPS, slug, fn),
                                   os.path.join(PUB_APPS, slug, fn), actions, f"{slug}/{fn}")
        pubdir = os.path.join(PUB_APPS, slug)
        if os.path.isdir(pubdir):
            keep = set(assets) | {"app.config.json"}
            for fn in sorted(os.listdir(pubdir)):
                fp = os.path.join(pubdir, fn)
                if os.path.isfile(fp) and fn not in keep:
                    os.remove(fp)
                    actions.append(f"pruned {slug}/{fn}")

    # 2) regenerate registry with same-origin (absolute) config paths
    src_reg = _read_json(SRC_REG)
    out_reg = {
        "_comment": "GENERATED by tools/sync_public.py from apps/registry.json — do not edit by hand. "
                    "Served by the Worker at the same origin; config paths are absolute (site root).",
        "apps": [{"name": a.get("name"), "icon": a.get("icon"),
                  "config": to_abs(a.get("config", ""))}
                 for a in src_reg.get("apps", [])],
    }
    out_text = json.dumps(out_reg, ensure_ascii=False, indent=2) + "\n"
    if not os.path.exists(PUB_REG) or open(PUB_REG, encoding="utf-8").read() != out_text:
        atomic_write(PUB_REG, out_text)
        actions.append("wrote registry.json")

    # 3) generate the production launcher from the single-source dev launcher
    gen = gen_launcher_text()
    if not os.path.exists(PUB_LAUNCHER) or open(PUB_LAUNCHER, encoding="utf-8").read() != gen:
        atomic_write(PUB_LAUNCHER, gen)
        actions.append("generated index.html (PROD)")

    # 4) prune orphan app folders
    if os.path.isdir(PUB_APPS):
        src_set = set(slugs)
        for name in sorted(os.listdir(PUB_APPS)):
            d = os.path.join(PUB_APPS, name)
            if os.path.isdir(d) and name not in src_set:
                shutil.rmtree(d)
                actions.append(f"pruned orphan {name}/")

    if verbose:
        if actions:
            for a in actions:
                print("  " + a)
            print(f"Synced worker/public/apps  ({len(actions)} change(s)). Redeploy to go live.")
        else:
            print("worker/public/apps already in sync.")
    return actions


if __name__ == "__main__":
    sync()
