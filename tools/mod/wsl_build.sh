#!/usr/bin/env bash
# Build inside WSL from a Windows checkout.
#
# The repo lives on the Windows drive, where WSL file access is slow, so this
# mirrors the sources to a native ext4 directory, builds there, and copies the
# results back:
#
#   tools/mod/wsl_build.sh init        first-time setup: venv, tools, extract, baseline build
#   tools/mod/wsl_build.sh             incremental build (matching, MOD=0)
#   tools/mod/wsl_build.sh -- MOD=1    extra arguments after -- go to make
#   tools/mod/wsl_build.sh pull-asm    copy the extracted asm/ tree back for reading
#
# Environment: MIRROR (default ~/stadium2-build), VENV (default ~/.venvs/stadium2), JOBS.
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MIRROR="${MIRROR:-$HOME/stadium2-build}"
VENV="${VENV:-$HOME/.venvs/stadium2}"
JOBS="${JOBS:-$(nproc)}"
VERSION="${VERSION:-us}"
US_SHA1="d8343e69a7dc63b869cf6361d87cde64444281d3"

APT_LINE="sudo apt update && sudo apt install -y make git build-essential binutils-mips-linux-gnu python3 python3-pip python3-venv"

check_prereqs() {
    local missing=()
    for p in make gcc cpp mips-linux-gnu-ld mips-linux-gnu-as python3 rsync; do
        command -v "$p" >/dev/null || missing+=("$p")
    done
    python3 -c 'import venv, ensurepip' 2>/dev/null || missing+=("python3-venv")
    if ((${#missing[@]})); then
        echo "Missing in WSL: ${missing[*]}" >&2
        echo "Run:  $APT_LINE" >&2
        exit 2
    fi
    local rom="$SRC/baseroms/$VERSION/baserom.z64"
    if [[ ! -f "$rom" ]]; then
        echo "Missing $rom" >&2
        echo "Run:  python3 tools/mod/check_rom.py <path-to-your-rom>" >&2
        exit 3
    fi
    if [[ "$VERSION" == us ]] && [[ "$(sha1sum "$rom" | cut -d' ' -f1)" != "$US_SHA1" ]]; then
        echo "baserom.z64 does not match the expected US ROM sha1" >&2
        exit 3
    fi
}

# Sources go Windows -> mirror. Generated trees stay in the mirror only.
push_sources() {
    mkdir -p "$MIRROR"
    rsync -a --delete \
        --exclude='/.git/' --exclude='/build/' --exclude='/asm/' --exclude='/assets/' \
        --exclude='/expected/' --exclude='/.splat/' --exclude='/.venv/' \
        --exclude='/linker_scripts/*/auto/' --exclude='/pokestadiumgs-*.yaml' \
        --exclude='/lib/ultralib/build/' --exclude='/tools/vtxdis' \
        --exclude='__pycache__/' --exclude='*.o' \
        "$SRC/" "$MIRROR/"
    chmod -R u+x "$MIRROR/tools/ido" "$MIRROR/tools/"*.py 2>/dev/null || true
}

pull_artifacts() {
    mkdir -p "$SRC/build"
    local f
    for f in "pokestadiumgs-$VERSION.z64" "pokestadiumgs-$VERSION.map" "pokestadiumgs-$VERSION.elf" \
             "pokestadiumgs-$VERSION-mod.z64"; do
        [[ -f "$MIRROR/build/$f" ]] && cp -f "$MIRROR/build/$f" "$SRC/build/$f"
    done
    return 0
}

run_make() {
    make -C "$MIRROR" -j"$JOBS" VERSION="$VERSION" VENV="$VENV" "$@"
}

cmd="${1:-build}"
[[ $# -gt 0 ]] && shift
[[ "${1:-}" == "--" ]] && shift

case "$cmd" in
    init)
        check_prereqs
        push_sources
        # `make init` is distclean + venv + setup + extract + diff-init, run serially
        # because its sub-steps depend on each other.
        make -C "$MIRROR" VERSION="$VERSION" VENV="$VENV" distclean || true
        make -C "$MIRROR" VERSION="$VERSION" VENV="$VENV" venv
        make -C "$MIRROR" VERSION="$VERSION" VENV="$VENV" setup
        make -C "$MIRROR" VERSION="$VERSION" VENV="$VENV" extract
        run_make "$@"
        pull_artifacts
        ;;
    build)
        check_prereqs
        push_sources
        run_make "$@"
        pull_artifacts
        ;;
    pull-asm)
        rsync -a --delete "$MIRROR/asm/" "$SRC/asm/"
        echo "asm/ copied to $SRC/asm"
        ;;
    shell)
        cd "$MIRROR" && exec bash
        ;;
    *)
        echo "usage: $0 [init|build|pull-asm|shell] [-- make-args...]" >&2
        exit 64
        ;;
esac
