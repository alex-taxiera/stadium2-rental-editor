#!/usr/bin/env bash
# Drive the game in BizHawk through mod/lua/remote.lua (run from Git Bash on Windows).
#
#   tools/mod/emu.sh start [rom]        launch BizHawk with the remote script (default: built US ROM)
#   tools/mod/emu.sh run 'press A' 'wait 60' 'shot title'    run commands, print their output
#   tools/mod/emu.sh script mod/lua/goto_rental.txt          run the commands in a file
#   tools/mod/emu.sh stop
#
# Commands are documented at the top of mod/lua/remote.lua. Screenshots, savestates
# and dumps land in .emu/remote.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REMOTE="$ROOT/.emu/remote"
EMUHAWK="$ROOT/.emu/BizHawk/EmuHawk.exe"
TIMEOUT="${TIMEOUT:-120}"

wait_for() {
    local file="$1" i
    for ((i = 0; i < TIMEOUT * 5; i++)); do
        [[ -f "$file" ]] && return 0
        sleep 0.2
    done
    echo "timed out after ${TIMEOUT}s waiting for $(basename "$file")" >&2
    return 1
}

case "${1:-}" in
    start)
        rom="${2:-$ROOT/build/pokestadiumgs-us.z64}"
        "$0" stop
        mkdir -p "$REMOTE"
        export S2_REMOTE_DIR
        S2_REMOTE_DIR="$(cygpath -w "$REMOTE")"
        "$EMUHAWK" "--lua=$(cygpath -w "$ROOT/mod/lua/remote.lua")" "$(cygpath -w "$rom")" >/dev/null 2>&1 &
        disown
        wait_for "$REMOTE/ready.txt"
        echo "emulator ready: $(cat "$REMOTE/ready.txt")"
        ;;
    run)
        shift
        [[ -f "$REMOTE/ready.txt" ]] || { echo "emulator not started" >&2; exit 1; }
        rm -f "$REMOTE/done.txt"
        printf '%s\n' "$@" > "$REMOTE/cmd.tmp"
        mv "$REMOTE/cmd.tmp" "$REMOTE/cmd.txt"
        wait_for "$REMOTE/done.txt"
        cat "$REMOTE/done.txt"
        ;;
    script)
        # Run the commands in a file, one per line.
        mapfile -t lines < <(grep -v -E '^\s*(#|$)' "$2")
        exec "$0" run "${lines[@]}"
        ;;
    stop)
        # Ask nicely, then make sure: a leftover instance would answer the next commands.
        if [[ -f "$REMOTE/ready.txt" ]]; then
            printf 'exit\n' > "$REMOTE/cmd.txt"
            sleep 2
        fi
        taskkill //IM EmuHawk.exe //F > /dev/null 2>&1 || true
        rm -f "$REMOTE/ready.txt" "$REMOTE/cmd.txt" "$REMOTE/done.txt"
        ;;
    *)
        echo "usage: $0 start [rom] | run <command>... | script <file> | stop" >&2
        exit 64
        ;;
esac
