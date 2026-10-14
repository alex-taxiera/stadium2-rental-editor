/*
 * The five Pokemon a Free Battle has no rental of, in the form of the game's rental
 * tables and in the order of their numbers. Written by hand; mod/tests/test_unlocks.py
 * holds them against the ROM.
 *
 * Mew and Celebi are the game's own, from the table the Prime Cup has in Round 2,
 * byte for byte. They are copied here because asking the archive for that table loads
 * all of it, 6 KB of the entry screen's memory for two records.
 *
 * Mewtwo, Lugia and Ho-Oh are in no table of the game's. They are level 100, as the
 * table they join is, with the stats the game gives those two: no DVs, no Stat Exp,
 * happiness 127, no PP Ups. Their moves are the ones the Rival's own have in Round 2.
 * (His Mewtwo of Round 1 has Hidden Power, which with no DVs is nothing.)
 */
static Rental sExtraRentals[] = {
    /* Mewtwo: Psychic, Submission, Thunderbolt, Recover */
    { 100, 150, 0, 0, { 94, 66, 85, 105 }, 0, 127, { 0, 0, 0, 0, 0 }, 0x0000, { 0, 0 } },
    /* Mew: Psychic, AncientPower, Metronome, Flash */
    { 100, 151, 0, 0, { 94, 246, 118, 148 }, 0, 127, { 0, 0, 0, 0, 0 }, 0x0000, { 0, 0 } },
    /* Lugia: Aeroblast, Earthquake, Psychic, Safeguard */
    { 100, 249, 0, 0, { 177, 89, 94, 219 }, 0, 127, { 0, 0, 0, 0, 0 }, 0x0000, { 0, 0 } },
    /* Ho-Oh: Sacred Fire, Thunder, Earthquake, Giga Drain */
    { 100, 250, 0, 0, { 221, 87, 89, 202 }, 0, 127, { 0, 0, 0, 0, 0 }, 0x0000, { 0, 0 } },
    /* Celebi: Giga Drain, AncientPower, Future Sight, Heal Bell */
    { 100, 251, 0, 0, { 202, 246, 248, 215 }, 0, 127, { 0, 0, 0, 0, 0 }, 0x0000, { 0, 0 } },
};
#define NUM_EXTRA_RENTALS 5
