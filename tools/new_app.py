# -*- coding: utf-8 -*-
"""Scaffold a new CRUD list app from a few prompts — no JSON by hand.

Creates apps/<slug>/app.config.json (+ README) and adds it to apps/registry.json,
so it shows up in the launcher automatically. Run via runners/new_app.bat or:
    python tools/new_app.py
"""
import os, re, json, sys
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPS = os.path.join(ROOT, "apps")
REG = os.path.join(APPS, "registry.json")

def ask(prompt, default=""):
    v = input(prompt + (f" [{default}]" if default else "") + ": ").strip()
    return v or default

def slugify(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-") or "app"

def atomic_write(path, text):
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def main():
    print("\n=== New app ===")
    name = ask("App name (e.g. Buy List)")
    if not name:
        print("aborted."); return
    slug = ask("Folder slug", slugify(name))
    icon = ask("Icon (emoji)", "▦")
    coll = ask("Collection name (short, unique)", slugify(name).replace("-", ""))
    readonly = ask("Read-only list? (data comes from a feed) y/N", "N").lower().startswith("y")

    print("\nAdd fields (blank key to finish).")
    fields = []
    while True:
        k = input(f"  field #{len(fields)+1} key: ").strip()
        if not k:
            break
        label = ask("     label", k.capitalize())
        ftype = ask("     type text/number", "text")
        fields.append({"key": k, "label": label, "type": ("number" if ftype.startswith("n") else "text")})
    if not fields:
        fields = [{"key": "name", "label": "Item", "type": "text"}]

    keys = [f["key"] for f in fields]
    num_keys = [f["key"] for f in fields if f["type"] == "number"]
    cfg = {
        "title": name,
        "collection": coll,
        "readOnly": bool(readonly),
        "fields": fields,
        "row": {"title": keys[0], "badge": (num_keys[0] if num_keys else "")},
        "detail": keys,
        "actions": ({"add": False, "check": True, "fav": True, "delete": False}
                    if readonly else
                    {"add": True, "check": True, "fav": False, "delete": True}),
        "sort": {"key": (num_keys[0] if (readonly and num_keys) else "created"),
                 "dir": ("asc" if (readonly and num_keys) else "desc")},
    }
    appdir = os.path.join(APPS, slug)
    os.makedirs(appdir, exist_ok=True)
    atomic_write(os.path.join(appdir, "app.config.json"), json.dumps(cfg, ensure_ascii=False, indent=2) + "\n")
    atomic_write(os.path.join(appdir, "README.md"),
                 f"# {name}\n\nOpen: `app/index.html?config=../apps/{slug}/app.config.json` "
                 f"(add `#glass` for the glasses layout).\n")

    reg = {"apps": []}
    if os.path.exists(REG):
        try: reg = json.load(open(REG, encoding="utf-8"))
        except Exception: pass
    reg.setdefault("apps", [])
    reg["apps"] = [a for a in reg["apps"] if a.get("config") != f"../apps/{slug}/app.config.json"]
    reg["apps"].append({"name": name, "icon": icon, "config": f"../apps/{slug}/app.config.json"})
    atomic_write(REG, json.dumps(reg, ensure_ascii=False, indent=2) + "\n")

    # Mirror into worker/public so the deployed Worker actually serves this app.
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sync_public
        sync_public.sync(verbose=False)
    except Exception as e:
        print(f"(warning: could not sync worker/public automatically: {e})")

    print(f"\nCreated apps/{slug}/app.config.json, registered + synced to worker/public.")
    print("Make it live:  runners/redeploy.bat   (syncs + wrangler deploy)")

if __name__ == "__main__":
    main()
