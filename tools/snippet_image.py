# -*- coding: utf-8 -*-
"""Render a code snippet as a syntax-highlighted PNG — WhatsApp shows no code formatting,
but a photo of the code reads perfectly in chat and in a lockscreen notification.

Usage:
    python tools/snippet_image.py <file> [--lines 10-25] [--hl 12,13] [--out out.png]
    echo "code" | python tools/snippet_image.py - --lang javascript [--out out.png]

Prints the absolute path of the written PNG (pass it to the WhatsApp reply tool's files[]).
"""
import os, sys, argparse, tempfile

from pygments import highlight
from pygments.formatters import ImageFormatter
from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer_for_filename

if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass


def default_out(hint):
    d = os.path.join(tempfile.gettempdir(), "glass-bridge")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "%s.png" % hint)


def render(code, lexer, out, first_line=1, hl_lines=()):
    fmt = ImageFormatter(
        font_name="Consolas",
        font_size=16,
        style="monokai",
        line_numbers=True,
        line_number_start=first_line,
        line_number_bg="#1f1f1f",
        line_number_fg="#6a6a6a",
        hl_lines=list(hl_lines),
        hl_color="#3a3222",
        image_pad=14,
        line_pad=5,
    )
    with open(out, "wb") as f:
        f.write(highlight(code, lexer, fmt))
    return os.path.abspath(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("file", help="source file, or - for stdin")
    p.add_argument("--lines", help="1-based inclusive range, e.g. 10-25")
    p.add_argument("--hl", help="comma-separated absolute line numbers to highlight")
    p.add_argument("--lang", help="lexer name (required for stdin, else guessed)")
    p.add_argument("--out", help="output PNG path")
    a = p.parse_args()

    if a.file == "-":
        code, name = sys.stdin.read(), "snippet"
        lexer = get_lexer_by_name(a.lang) if a.lang else TextLexer()
    else:
        code = open(a.file, encoding="utf-8", errors="replace").read()
        name = os.path.splitext(os.path.basename(a.file))[0]
        try:
            lexer = get_lexer_by_name(a.lang) if a.lang else guess_lexer_for_filename(a.file, code)
        except Exception:
            lexer = TextLexer()

    first = 1
    if a.lines:
        lo, hi = (int(x) for x in a.lines.split("-", 1))
        code = "\n".join(code.splitlines()[lo - 1:hi])
        first, name = lo, "%s-%d-%d" % (name, lo, hi)

    hl = [int(x) - first + 1 for x in a.hl.split(",")] if a.hl else []
    out = a.out or default_out(name)
    print(render(code, lexer, out, first_line=first, hl_lines=hl))


if __name__ == "__main__":
    main()
