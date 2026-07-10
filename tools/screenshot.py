# -*- coding: utf-8 -*-
"""Capture the PC screen to a PNG — the bridge's "show me what's on the PC" command.

The WhatsApp agent runs this and attaches the printed path via the reply tool's files[].
Captures the full virtual screen (all monitors) by default; downscaled so it sends fast
and stays readable on a phone.

Usage:
    python tools/screenshot.py                # all monitors, max 1600px wide
    python tools/screenshot.py --full         # no downscale
    python tools/screenshot.py --out shot.png

Prints the absolute path of the written PNG.
"""
import os, sys, time, argparse, tempfile

from PIL import ImageGrab

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--full", action="store_true", help="keep original resolution")
    p.add_argument("--max", type=int, default=1600, help="max width in px (default 1600)")
    p.add_argument("--out", help="output PNG path")
    a = p.parse_args()

    img = ImageGrab.grab(all_screens=True)
    if not a.full and img.width > a.max:
        img = img.resize((a.max, round(img.height * a.max / img.width)))

    out = a.out
    if not out:
        d = os.path.join(tempfile.gettempdir(), "glass-bridge")
        os.makedirs(d, exist_ok=True)
        out = os.path.join(d, "screen-%d.png" % int(time.time()))
    img.save(out, "PNG")
    print(os.path.abspath(out))


if __name__ == "__main__":
    main()
