#!/usr/bin/env python3
"""Drive the game in BizHawk through mod/lua/remote.lua. Runs on Windows, not in WSL.

    tools/mod/emu.py start [rom]        launch BizHawk with the remote script (default: built mod ROM)
    tools/mod/emu.py run 'press A' 'wait 60' 'shot title'    run commands, print their output
    tools/mod/emu.py script mod/lua/goto_rental.txt          run the commands in a file
    tools/mod/emu.py stop

Commands are documented at the top of mod/lua/remote.lua. Screenshots, savestates and
dumps land in the remote directory, .emu/remote unless --dir says otherwise.

The script and this program talk through files in that directory: commands are written
to cmd.txt, and done.txt appears with their output once all have run.

Tests use the Emulator class directly; see mod/tests/emu. Standard library only.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BIZHAWK = REPO_ROOT / ".emu" / "BizHawk"
EMUHAWK = BIZHAWK / "EmuHawk.exe"
REMOTE_LUA = REPO_ROOT / "mod" / "lua" / "remote.lua"
DEFAULT_DIR = REPO_ROOT / ".emu" / "remote"
DEFAULT_ROM = REPO_ROOT / "build" / "pokestadiumgs-us-mod.z64"

# BizHawk stops at this box when Windows has no audio device, before any script runs.
SOUND_DIALOG_TITLE = "Initialization Error"


class EmulatorError(RuntimeError):
    pass


def dismiss_sound_dialog() -> bool:
    """Presses OK on BizHawk's sound-device error box, if it is showing."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = wintypes.HWND
    dialog = user32.FindWindowW(None, SOUND_DIALOG_TITLE)
    if not dialog:
        return False

    buttons = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def visit(window, _):
        text = ctypes.create_unicode_buffer(16)
        user32.GetWindowTextW(window, text, len(text))
        if text.value == "OK":
            buttons.append(window)
        return True

    user32.EnumChildWindows(dialog, visit, 0)
    for button in buttons:
        user32.SendMessageW(wintypes.HWND(button), 0x00F5, 0, 0)   # BM_CLICK
    return bool(buttons)


def make_config(source: Path, dest: Path, controllers: int = 1) -> Path:
    """A copy of a BizHawk config with this many controllers plugged in, so a test never
    changes the user's own settings. BizHawk also saves its settings to the copy on exit."""
    text = source.read_text(encoding="utf-8")
    # The first player's entry is left alone: it is always plugged in.
    for player in range(2, 5):
        text, count = re.subn(rf'("P{player}Controller": )\d+', rf"\g<1>{1 if player <= controllers else 0}", text)
        if count != 1:
            raise EmulatorError(f"expected one P{player}Controller setting in {source}, found {count}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


class Emulator:
    """One BizHawk instance and the directory it is driven through."""

    def __init__(self, directory: Path = DEFAULT_DIR, config: Path = None, stepping: bool = False):
        """With `stepping` the game only runs while commands do, which makes runs
        repeatable frame for frame; see mod/lua/remote.lua."""
        self.dir = Path(directory)
        self.config = config
        self.stepping = stepping
        self.process = None

    def _file(self, name: str) -> Path:
        return self.dir / name

    def _wait_for(self, name: str, timeout: float, starting: bool = False) -> None:
        path = self._file(name)
        deadline = time.monotonic() + timeout
        while not path.exists():
            if time.monotonic() > deadline:
                raise EmulatorError(f"timed out after {timeout:g}s waiting for {name}")
            if starting:
                dismiss_sound_dialog()
                if self.process is not None and self.process.poll() is not None:
                    raise EmulatorError(f"BizHawk exited with code {self.process.returncode} while starting")
            time.sleep(0.2 if starting else 0.01)

    @property
    def running(self) -> bool:
        return self._file("ready.txt").exists()

    def start(self, rom: Path = DEFAULT_ROM, timeout: float = 120) -> str:
        """Launches BizHawk on `rom` and returns the system it reports, e.g. "N64"."""
        if not EMUHAWK.exists():
            raise EmulatorError(f"BizHawk is not installed at {BIZHAWK}")
        rom = Path(rom).resolve()
        if not rom.exists():
            raise EmulatorError(f"no ROM at {rom}")
        self.stop()
        self.dir.mkdir(parents=True, exist_ok=True)
        arguments = [str(EMUHAWK), f"--lua={REMOTE_LUA}"]
        if self.config is not None:
            arguments.append(f"--config={Path(self.config).resolve()}")
        flags = 0
        if sys.platform == "win32":
            # Not tied to this console, so it outlives `emu.py start`.
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        environment = dict(os.environ, S2_REMOTE_DIR=str(self.dir), S2_REMOTE_STEP="1" if self.stepping else "0")
        self.process = subprocess.Popen(arguments + [str(rom)], env=environment,
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL, creationflags=flags, cwd=str(BIZHAWK))
        self._wait_for("ready.txt", timeout, starting=True)
        return self._file("ready.txt").read_text().strip()

    def run(self, *commands: str, timeout: float = 120) -> list:
        """Runs commands in order and returns the lines they printed."""
        if not self.running:
            raise EmulatorError("emulator not started")
        commands = [c for c in commands if c.strip() and not c.lstrip().startswith("#")]
        self._file("done.txt").unlink(missing_ok=True)
        self._file("cmd.tmp").write_text("\n".join(commands) + "\n", encoding="utf-8", newline="\n")
        os.replace(self._file("cmd.tmp"), self._file("cmd.txt"))
        self._wait_for("done.txt", timeout)
        # The script renames the finished file into place, but give Windows a moment.
        for _ in range(50):
            try:
                return self._file("done.txt").read_text(encoding="utf-8", errors="replace").splitlines()
            except PermissionError:
                time.sleep(0.01)
        raise EmulatorError("could not read done.txt")

    def script(self, path: Path, timeout: float = 600) -> list:
        """Runs the commands in a file, one per line; # starts a comment."""
        return self.run(*Path(path).read_text(encoding="utf-8").splitlines(), timeout=timeout)

    def reboot(self, timeout: float = 60) -> None:
        """Power-cycles the console. Save data on the cartridge survives; nothing else does."""
        self.run("reboot", timeout=timeout)
        # The reboot happens just after the answer is written. Wait for the script to
        # answer again before anything is asked of the fresh console.
        deadline = time.monotonic() + timeout
        while True:
            time.sleep(0.5)
            try:
                self.run("frame", timeout=5)
                return
            except EmulatorError:
                if time.monotonic() > deadline:
                    raise

    def stop(self) -> None:
        """Asks BizHawk to close, then makes sure: a leftover instance would answer the
        next commands."""
        if self.running:
            self._file("cmd.txt").write_text("exit\n")
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if self.process is not None and self.process.poll() is not None:
                    break
                time.sleep(0.1)
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/IM", EMUHAWK.name, "/F"], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, check=False)
        elif self.process is not None and self.process.poll() is None:
            self.process.kill()
        self.process = None
        for name in ("ready.txt", "cmd.txt", "cmd.tmp", "done.txt"):
            self._file(name).unlink(missing_ok=True)


def fresh_rom(rom: Path, name: str, directory: Path) -> Path:
    """Copies `rom` to `directory/name` and deletes that name's save file, so the game
    starts as it does out of the box. BizHawk names save files after the ROM file."""
    directory.mkdir(parents=True, exist_ok=True)
    copy = directory / name
    shutil.copyfile(rom, copy)
    for save in (BIZHAWK / "N64" / "SaveRAM").glob(f"{copy.stem}.SaveRAM*"):
        save.unlink()
    return copy


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="remote directory (default: .emu/remote)")
    parser.add_argument("--timeout", type=float, default=float(os.environ.get("TIMEOUT", 120)),
                        help="seconds to wait for the emulator (default: 120)")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start", help="launch BizHawk with the remote script")
    p.add_argument("rom", type=Path, nargs="?", default=DEFAULT_ROM)
    p = sub.add_parser("run", help="run commands and print their output")
    p.add_argument("commands", nargs="+")
    p = sub.add_parser("script", help="run the commands in a file")
    p.add_argument("file", type=Path)
    sub.add_parser("stop", help="close BizHawk")
    args = parser.parse_args()

    emulator = Emulator(args.dir)
    try:
        if args.command == "start":
            print(f"emulator ready: {emulator.start(args.rom, args.timeout)}")
        elif args.command == "run":
            print("\n".join(emulator.run(*args.commands, timeout=args.timeout)))
        elif args.command == "script":
            print("\n".join(emulator.script(args.file, timeout=args.timeout)))
        else:
            emulator.stop()
    except EmulatorError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
