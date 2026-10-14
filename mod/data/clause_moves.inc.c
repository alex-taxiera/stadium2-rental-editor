/*
 * The moves the clauses are about, by the game's move ids. Written by hand, and held
 * against Pokemon Showdown's data by mod/tests/test_clauses.py: each id against its
 * name, and each list against what Showdown says the moves do.
 */

/* Evasion Clause: the moves that raise the user's evasion. */
static const u8 sEvasionMoves[] = {
    104, /* Double Team */
    107, /* Minimize */
};

/* OHKO Clause: the moves that knock out in one hit. Sheer Cold is of a later game. */
static const u8 sOhkoMoves[] = {
    12, /* Guillotine */
    32, /* Horn Drill */
    90, /* Fissure */
};

/* The moves that keep the foe from switching, which Baton Pass would hand on. */
static const u8 sTrappingMoves[] = {
    169, /* Spider Web */
    212, /* Mean Look */
};

#define MOVE_BATON_PASS 226
