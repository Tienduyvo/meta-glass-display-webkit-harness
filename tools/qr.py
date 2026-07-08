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


import re
def mask_secret(url):
    """Replace the password in a launcher URL (`…t=<pw>`) with **** for display/logging.
    The real value still goes into the QR image; it just never gets printed."""
    return re.sub(r'(?i)([?#&]t=)[^&\s]+', r'\1****', url)


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
    # Build the glasses launcher URL. Prefer an explicit arg or GLASS_LAUNCHER; otherwise derive the
    # base from GLASS_API (…/api -> origin). If the URL carries no token yet and GLASS_TOKEN is set
    # (from git-ignored push.env), append #glass&t=<token> HERE — so the password lives only in the
    # env file and is never typed on the command line or seen by an assistant driving the tool.
    app_url = argv[1] if len(argv) > 1 else os.environ.get("GLASS_LAUNCHER", "")
    tok = os.environ.get("GLASS_TOKEN", "")
    if not app_url:
        api = os.environ.get("GLASS_API", "").rstrip("/")
        app_url = api[:-4].rstrip("/") if api.endswith("/api") else api
    if app_url and "t=" not in app_url and tok:
        app_url = app_url.rstrip("/") + "/#glass&t=" + tok
    if not app_url:
        print("No launcher URL. Pass it as the 2nd arg, or set GLASS_LAUNCHER (or GLASS_API) +")
        print("GLASS_TOKEN in push.env (git-ignored) so the password stays off the command line.")
        return 2
    if "t=" not in app_url:
        print("Note: URL has no password — set GLASS_TOKEN in push.env, or include #glass&t=… yourself.\n")

    link = deep_link(name, app_url)                 # REAL link — goes into the QR image only
    has_secret = bool(re.search(r'(?i)[?#&]t=[^&\s]+', app_url))
    print("Deep link (add-to-glasses):\n  " + deep_link(name, mask_secret(app_url)) + "\n")

    try:
        import segno
        q = segno.make(link, error="m")
        png = os.path.join(ROOT, "qr.png")
        svg = os.path.join(ROOT, "qr.svg")
        q.save(png, scale=6, border=2)
        q.save(svg, scale=6, border=2)
        print("Wrote " + png + " and " + svg + " — open on your desktop and scan with your phone.")
        if has_secret:
            print("(ASCII QR suppressed — it would encode your password; scan the PNG instead.)")
        else:
            try: q.terminal(compact=True)
            except Exception: pass
    except ImportError:
        print("(no QR image — `pip install segno` for qr.png/qr.svg.)")

    if has_secret:
        print("\nSECURITY: your password is written ONLY into the QR image (qr.png), never printed here")
        print("(it's masked in this output). Keep qr.png private — don't commit or post it.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
