#!/usr/bin/env python3
"""WhatsApp bridge setup engine (Windows) — sectioned, idempotent, agent-drivable.

This is the deterministic half of the setup wizard. The conversational half is
the `bridge-setup` skill (.claude/skills/bridge-setup/SKILL.md): a Claude Code
session front-loads the questions, runs these sections, reads their STATE lines,
and self-heals known failures from docs/whatsapp-bridge.md before asking a human.

Sections (each exits 0/1 and prints a final machine-readable `STATE: ...` line):

  check                       prerequisites (git, bun, node, claude)
  install  --dir D [--no-patch]   clone daemon + apply fork patch + deps + tsc
  config   --owner +49...     write ~/.bridge-env.cmd whitelist (idempotent)
  shim                        ~/.local/bin/which.cmd so the daemon finds claude
  pair     [--dir D]          interactive console phase: QR pairing, automatic
                              LID capture, end-to-end verify. Run it in a VISIBLE
                              window (QR renders live); progress mirrors to
                              ~/.whatsapp-claude-agent/setup-state.json so an
                              agent can poll instead of parsing the console.
  autostart                   Startup-folder shortcut for start-bridge.cmd
  all                         classic standalone interactive flow (no agent)

Human-only steps no code can remove: providing the second WhatsApp number,
scanning the pairing QR, and sending the two test messages.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

HARNESS = Path(__file__).resolve().parent.parent
HOME = Path.home()
FORK_URL = "https://github.com/dsebastien/whatsapp-claude-agent.git"
DEFAULT_FORK_DIR = HOME / "Downloads" / "whatsapp-claude-agent"
PATCH = HARNESS / "docs" / "whatsapp-bridge.fork.patch"
ENV_CMD = HOME / ".bridge-env.cmd"
LOCAL_BIN = HOME / ".local" / "bin"
STARTUP_DIR = HOME / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
STATE_FILE = HOME / ".whatsapp-claude-agent" / "setup-state.json"

LID_RE = re.compile(r"Blocked message from non-whitelisted number: (\d+)@lid")
ACCEPTED_RE = re.compile(r"Message from ")
CONNECTED_RE = re.compile(r"WhatsApp connection established")


def state(**kw) -> None:
    """Mirror progress for the driving agent + print the STATE line."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    kw.setdefault("ts", time.time())
    STATE_FILE.write_text(json.dumps(kw), encoding="utf-8")
    print(f"STATE: {json.dumps(kw)}")


def ok(section: str, **kw) -> None:
    state(section=section, status="ok", **kw)
    sys.exit(0)


def fail(section: str, reason: str, **kw) -> None:
    state(section=section, status="fail", reason=reason, **kw)
    sys.exit(1)


def find_exe(name: str, extra: list = ()) -> str | None:
    hit = shutil.which(name)
    if hit:
        return hit
    for p in extra:
        if Path(p).exists():
            return str(p)
    return None


def tool_paths() -> dict:
    return {
        "git": find_exe("git"),
        "bun": find_exe("bun", [r"C:\Program Files\nodejs\node_modules\bun\bin\bun.exe"]),
        "node": find_exe("node"),
        "claude": find_exe("claude", [LOCAL_BIN / "claude.exe"]),
    }


def run(cmd: list, cwd: Path | None = None) -> int:
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run([str(c) for c in cmd], cwd=cwd).returncode


# ---------------------------------------------------------------- sections

def sec_check(_args) -> None:
    tools = tool_paths()
    for name, path in tools.items():
        print(f"  {name:8} {'OK  ' + str(path) if path else 'MISSING'}")
    missing = [n for n, p in tools.items() if p is None]
    if missing:
        fail("check", "missing prerequisites", missing=missing)
    ok("check", tools={k: str(v) for k, v in tools.items()})


def sec_install(args) -> None:
    tools = tool_paths()
    fork = Path(args.dir)
    if not (fork / "src" / "index.ts").exists():
        if run([tools["git"], "clone", "--depth", "1", FORK_URL, fork]) != 0:
            fail("install", "git clone failed")
        if not args.no_patch:
            if not PATCH.exists():
                fail("install", f"patch file missing: {PATCH}")
            if run([tools["git"], "apply", str(PATCH)], cwd=fork) != 0:
                fail("install", "git apply failed (upstream drift? try --no-patch or rebase the patch)")
    else:
        print(f"  daemon already present at {fork} — reusing")
    if run([tools["bun"], "install"], cwd=fork) != 0:
        fail("install", "bun install failed")
    if run([tools["bun"], "x", "tsc", "--noEmit"], cwd=fork) != 0:
        fail("install", "typecheck failed")
    ok("install", dir=str(fork), patched=not args.no_patch)


def sec_config(args) -> None:
    if not re.fullmatch(r"\+\d{8,15}", args.owner):
        fail("config", "owner must be international format like +491701234567")
    if ENV_CMD.exists() and "WA_WHITELIST=" in ENV_CMD.read_text(encoding="ascii", errors="replace"):
        print(f"  {ENV_CMD} already configured — leaving numbers untouched")
        ok("config", file=str(ENV_CMD), existing=True)
    ENV_CMD.write_text(
        f"@echo off\nset WA_WHITELIST={args.owner},{args.owner.lstrip('+')}\n",
        encoding="ascii",
    )
    ok("config", file=str(ENV_CMD), existing=False)


def sec_shim(_args) -> None:
    claude = tool_paths()["claude"]
    if not claude:
        fail("shim", "claude executable not found")
    shim = LOCAL_BIN / "which.cmd"
    if not shim.exists():
        LOCAL_BIN.mkdir(parents=True, exist_ok=True)
        shim.write_text(
            f'@echo off\nif "%1"=="claude" (echo {claude}\n) else (where %1)\n',
            encoding="ascii",
        )
    ok("shim", file=str(shim))


def current_whitelist() -> str:
    m = re.search(r"WA_WHITELIST=(\S+)", ENV_CMD.read_text(encoding="ascii", errors="replace"))
    return m.group(1) if m else ""


def append_lid(lid: str) -> None:
    wl = current_whitelist()
    if lid not in wl.split(","):
        text = ENV_CMD.read_text(encoding="ascii", errors="replace")
        ENV_CMD.write_text(
            text.replace(f"WA_WHITELIST={wl}", f"WA_WHITELIST={wl},{lid}"), encoding="ascii"
        )


def daemon_proc(fork: Path, bun: str) -> subprocess.Popen:
    return subprocess.Popen(
        [bun, "run", str(fork / "src" / "index.ts"),
         "-w", current_whitelist(), "-d", str(HARNESS), "--agent-name", "Claude", "-v"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
    )


def watch(proc: subprocess.Popen, pattern: re.Pattern, timeout_s: int, echo: bool = True):
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        line = proc.stdout.readline()
        if not line:
            if proc.poll() is not None:
                return None
            continue
        if echo:
            print("  | " + line.rstrip())
        m = pattern.search(line)
        if m:
            return m
    return None


def sec_pair(args) -> None:
    if not ENV_CMD.exists():
        fail("pair", "run the config section first (~/.bridge-env.cmd missing)")
    tools = tool_paths()
    fork = Path(args.dir)
    print(
        "\nWhen the QR code appears: BOT phone -> WhatsApp -> Linked devices -> Link a\n"
        "device -> scan. Afterwards force-stop WhatsApp once on YOUR OWN phone and\n"
        "reopen it (stale device cache is a known pitfall).\n"
    )
    state(section="pair", status="running", phase="starting")
    proc = daemon_proc(fork, tools["bun"])
    try:
        if not watch(proc, CONNECTED_RE, 300):
            fail("pair", "no connection within 5 min (QR not scanned, or see troubleshooting)")
        state(section="pair", status="running", phase="connected")
        print("\nPaired. Send ANY message from your own phone to the bot number now.")
        m = watch(proc, LID_RE, 300, echo=False)
        if m:
            lid = m.group(1)
            append_lid(lid)
            state(section="pair", status="running", phase="lid_captured", lid=lid)
            print(f"\nCaptured your privacy ID ({lid}); restarting with it whitelisted.")
            proc.terminate(); proc.wait(timeout=15)
            proc = daemon_proc(fork, tools["bun"])
            print("Send ONE MORE message from your phone to confirm.")
            if not watch(proc, ACCEPTED_RE, 300, echo=False):
                fail("pair", "message after LID whitelist never arrived", lid=lid)
        print("\nMessage accepted — bridge works end-to-end.")
        ok("pair", phase="verified")
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()


def sec_autostart(_args) -> None:
    lnk = STARTUP_DIR / "claude-whatsapp-bridge.lnk"
    target = HARNESS / "start-bridge.cmd"
    ps = (
        f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{lnk}');"
        f"$s.TargetPath='{target}';$s.WorkingDirectory='{HARNESS}';"
        "$s.WindowStyle=7;$s.Save()"
    )
    if run(["powershell", "-NoProfile", "-Command", ps]) != 0:
        fail("autostart", "shortcut creation failed")
    ok("autostart", shortcut=str(lnk))


def sec_all(_args) -> None:
    """Standalone interactive flow for humans without a Claude session."""
    print(__doc__)
    print("Prerequisite reality check: you need a SECOND WhatsApp number for the bot.")
    owner = input("Your phone number (international, e.g. +49...): ").strip()
    autostart = input("Autostart at login? [y/N]: ").strip().lower() == "y"
    for section, argv in [
        ("check", []),
        ("install", ["--dir", str(DEFAULT_FORK_DIR)]),
        ("config", ["--owner", owner]),
        ("shim", []),
        ("pair", ["--dir", str(DEFAULT_FORK_DIR)]),
    ] + ([("autostart", [])] if autostart else []):
        print(f"\n### section: {section}")
        r = subprocess.run([sys.executable, __file__, section, *argv])
        if r.returncode != 0:
            sys.exit(r.returncode)
    print("\nDone. Start the bridge with start-bridge.cmd; runbook: docs/whatsapp-bridge.md")


def main() -> None:
    if os.name != "nt":
        print("ERROR: this wizard targets Windows", file=sys.stderr)
        sys.exit(1)
    p = argparse.ArgumentParser(description="WhatsApp bridge setup engine")
    sub = p.add_subparsers(dest="section", required=True)
    sub.add_parser("check")
    i = sub.add_parser("install")
    i.add_argument("--dir", default=str(DEFAULT_FORK_DIR))
    i.add_argument("--no-patch", action="store_true")
    c = sub.add_parser("config")
    c.add_argument("--owner", required=True)
    sub.add_parser("shim")
    pr = sub.add_parser("pair")
    pr.add_argument("--dir", default=str(DEFAULT_FORK_DIR))
    sub.add_parser("autostart")
    sub.add_parser("all")
    args = p.parse_args()
    {
        "check": sec_check, "install": sec_install, "config": sec_config,
        "shim": sec_shim, "pair": sec_pair, "autostart": sec_autostart, "all": sec_all,
    }[args.section](args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
