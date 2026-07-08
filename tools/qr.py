# -*- coding: utf-8 -*-
"""Make a QR that adds your app to the Meta Ray-Ban Display glasses in one tap.

Scanning the QR with your *phone* opens the Meta AI app and adds the web app to
the glasses (Developer Mode + a public HTTPS URL required). The QR just encodes
Meta's official deep link:

    fb-viewapp://web_app_deep_link?appName=<name>&appUrl=<url-encoded-https-url>

(format per facebookincubator/meta-wearables-webapp / wearables.developer.meta.com)

Usage:
    python tools/qr.py "Meta Glass" "https://<worker>.workers.dev/#glass&t=<password>"
    # or take the launcher URL from an env var and just name it:
    GLASS_LAUNCHER="https://<worker>.workers.dev/#glass&t=<password>" python tools/qr.py "Meta Glass"

Writes qr.png + qr.svg next to the repo if the pure-Python `segno` lib is present
(`pip install segno`); always prints the deep link and an ASCII QR fallback.

SECURITY: the launcher URL carries your password in the hash, so the deep link and
the QR image are secret — don't post them publicly.
"""
import os, sys, urllib.parse

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def deep_link(name, app_url):
    return ("fb-viewapp://web_app_deep_link?appName="
            + urllib.parse.quote(name, safe="")
            + "&appUrl=" + urllib.parse.quote(app_url, safe=""))


def main(argv):
    if not argv:
        print('usage: qr.py "<App Name>" "<launcher URL with #glass&t=PASSWORD>"')
        print('   or: set GLASS_LAUNCHER and pass just the name')
        return 2
    name = argv[0]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import push
        push._load_creds_file()
    except Exception:
        pass
    app_url = argv[1] if len(argv) > 1 else os.environ.get("GLASS_LAUNCHER", "")
    if not app_url:
        print("No launcher URL. Pass it as the 2nd arg or set GLASS_LAUNCHER.")
        return 2

    link = deep_link(name, app_url)
    print("Deep link (add-to-glasses):\n  " + link + "\n")

    try:
        import segno
        q = segno.make(link, error="m")
        png = os.path.join(ROOT, "qr.png")
        svg = os.path.join(ROOT, "qr.svg")
        q.save(png, scale=6, border=2)
        q.save(svg, scale=6, border=2)
        print("Wrote " + png + " and " + svg + " — open on your desktop and scan with your phone.\n")
        try:
            q.terminal(compact=True)
        except Exception:
            pass
    except ImportError:
        print("(no QR image — `pip install segno` for qr.png/qr.svg, or paste the deep link above")
        print(" into any QR generator, then scan it with your phone.)")

    print("\nSECURITY: this deep link contains your password — keep it private.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
