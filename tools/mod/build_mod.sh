#!/usr/bin/env bash
# Build the mod fragment, inject it into a copy of the matching ROM, and write the
# BPS patch that turns the original ROM into the result. Also writes a copy of the ROM
# that runs as if the console had no Expansion Pak, for the emulator tests.
# Runs inside the WSL build mirror (see wsl_build.sh mod); expects the stock build
# to exist already.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.."

VERSION="${VERSION:-us}"
VENV="${VENV:-$HOME/.venvs/stadium2}"
PYTHON="$VENV/bin/python3"
OUT=build/mod
GAME_ELF="build/pokestadiumgs-$VERSION.elf"
ROM="build/pokestadiumgs-$VERSION.z64"
MOD_ROM="build/pokestadiumgs-$VERSION-mod.z64"
MOD_ROM_4MB="build/pokestadiumgs-$VERSION-mod-4mb.z64"
PATCH="build/stadium2-rental-editor-$VERSION.bps"
BASEROM="baseroms/$VERSION/baserom.z64"
ASM_DIR="asm/$VERSION"

CC=tools/ido/linux/7.1/cc
AS=mips-linux-gnu-as
LD=mips-linux-gnu-ld
NM=mips-linux-gnu-nm

# Same flags the game is built with (see Makefile).
CFLAGS="-c -G 0 -non_shared -Xcpluscomm -nostdinc -Wab,-r4300_mul -mips2 -EB -O2
        -fullwarn -woff 624,649,838,712,516,513,596,564,594
        -DVERSION_US=1 -D_MIPS_SZLONG=32 -DNDEBUG -D_FINALROM -DN_MICRO -DF3DEX_GBI_2
        -DBUILD_VERSION=VERSION_L -DLANGUAGE_C -D_LANGUAGE_C
        -Imod/include -Imod/data -Iinclude
        -Ilib/ultralib/include -Ilib/ultralib/include/PR -Ilib/ultralib/include/ido"
ASFLAGS="-march=vr4300 -32 -G0 -EB -Iinclude"

for f in "$GAME_ELF" "$ROM"; do
    [[ -f "$f" ]] || { echo "missing $f; build the stock ROM first" >&2; exit 1; }
done

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" tools/mod/modtool.py asm mod/hooks.txt "$ASM_DIR" "$OUT"

objects=()
for source in "$OUT"/entry.s "$OUT"/moved.s mod/src/*.s; do
    object="$OUT/$(basename "${source%.s}").o"
    $AS $ASFLAGS -o "$object" "$source"
    objects+=("$object")
done
for source in mod/src/*.c; do
    object="$OUT/$(basename "${source%.c}").o"
    $CC $CFLAGS -o "$object" "$source"
    objects+=("$object")
done
# Stock functions with instructions changed in place. Not part of the mod fragment:
# inject copies the changed words from this object into the ROM.
$AS $ASFLAGS -o "$OUT/patched.o" "$OUT/patched.s"

# Every global symbol of the game, as linker-script assignments. (ld's --just-symbols
# would be simpler, but it rejects jumps from the fragment to main-segment functions.)
$NM "$GAME_ELF" | awk '$2 ~ /^[A-Z]$/ && $3 ~ /^[A-Za-z_][A-Za-z0-9_]*$/ { print $3 " = 0x" $1 ";" }' \
    > "$OUT/game_syms.ld"

$LD -T mod/mod.ld -T "$OUT/game_syms.ld" --emit-relocs --no-check-sections \
    --accept-unknown-input-arch -e 0 -Map "$OUT/mod.map" -o "$OUT/mod.elf" "${objects[@]}"

"$PYTHON" tools/mod/modtool.py inject --mod-elf "$OUT/mod.elf" --game-elf "$GAME_ELF" \
    --rom "$ROM" --hooks mod/hooks.txt --asm-dir "$ASM_DIR" --out "$MOD_ROM" \
    --patched-obj "$OUT/patched.o"

"$PYTHON" tools/mod/bps.py create "$BASEROM" "$MOD_ROM" "$PATCH"
"$PYTHON" tools/mod/make_4mb_rom.py "$MOD_ROM" "$MOD_ROM_4MB"

# Says whether this build is the one recorded in mod/checksums.txt. A difference is
# expected after changing the mod, and is not an error here; the tests make it one.
"$PYTHON" tools/mod/checksums.py check --root . || true
