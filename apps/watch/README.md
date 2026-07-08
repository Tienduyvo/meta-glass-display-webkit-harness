# Example app: `watch` (read-only feed + video links)

A **push-fed** display: no add bar (`readOnly:true`). Your PC/agent pushes items into the
`watch` collection, and you browse them on the glasses — arrow to a clip, **Enter** on
**▶ Open** to launch the link. Mark **✓ seen** / **★ fav** hands-free on the glasses.

Demonstrates the `video`/`link` field type (a focusable **▶ Open** in the detail view, reachable
with D-pad + Enter) and the thin brain→display bridge `tools/push.py`.

## Feed it
```
set GLASS_API=https://<your-worker>.workers.dev/api        # (macOS/Linux: export)
set GLASS_TOKEN=<your app password>
python tools/push.py watch --file apps/watch/watch.sample.json
```

## Fields
- **Title** (`title`, text)
- **Video** (`url`, video — ▶ Open)
- **Note** (`note`, text)

> Opening a link works; smooth in-glasses video playback is limited by the device (memory,
> additive display) — treat it as "open a link", not a video screen.
