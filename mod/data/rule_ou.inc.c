/*
 * The mod's rule set for Free Battle, shaped like the second generation's OU: Anything
 * Goes, without the five Pokemon the cups keep out, and with the move clauses. Written
 * by hand; mod/tests/test_clauses.py holds it against the game's own records.
 *
 * It is of Anything Goes's kind, and so it is Anything Goes to everything that asks
 * what kind of rules a battle has: any number of Pokemon up to six, all of which
 * fight, one to four players, the same registered teams. See mod/src/rules.c.
 */
static Rules sOuRules = {
    "OU Rules",
    /* Everyone but Mewtwo, Mew, Lugia, Ho-Oh and Celebi: the Poke Cup's own mask. */
    { 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
      0xFF, 0xFF, 0xF9, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0x00 },
    RULES_ANYTHING_GOES,
    0,   /* levels, their total, the background and the rental table as Anything Goes has them */
    100,
    600,
    10,
    1,
    -1,  /* named by its own name */
    /* Anything Goes's flags: a short team, a species twice, an item twice and held items
     * are all allowed. */
    0xEFFF0000 | CLAUSE_EVASION | CLAUSE_OHKO | CLAUSE_TRAP_PASS,
};
