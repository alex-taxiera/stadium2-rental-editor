#include "clauses.h"

#include "rental_extra.inc.c"

/*
 * Every Pokemon for rent in a Free Battle.
 *
 * Anything Goes and the Prime Cup rent from a table of 246: every Pokemon but Mewtwo,
 * Mew, Lugia, Ho-Oh and Celebi. The game has Mew and Celebi in another table, which
 * only the Prime Cup of Round 2 uses, and the other three in no table at all.
 *
 * The game's tables and rule sets are left as they are, the cups of the Stadium having
 * them too. The entry screen of a Free Battle is given a table of the mod's own in
 * place of that one: its 246 as they are, and the five where their numbers fall. (Not
 * Round 2's table: its Pikachu and Psyduck know other moves.) A Pokemon the rule set
 * in force keeps out is left out of it, as the game's own tables have nobody who may
 * not enter: under the mod's OU Rules the table is the game's 246 again.
 *
 * The picker has room for 0xFE rentals and sorts them itself, by the keys it has for
 * every species, so nothing but the table has to know of the five.
 */

static s32 Rentals_Add(RentalTable *table, s32 count, Rules *rules, Rental *rental) {
    if (count < MAX_RENTALS && SpeciesMask_Has(rules->species, rental->species - 1)) {
        table->rentals[count] = *rental;
        count++;
    }
    return count;
}

/**
 * Stands in for func_80071B20 where the entry screen takes its table of rental Pokemon
 * (mod/asm_patches.txt), which runs as the screen starts, with the mod just loaded. The
 * table is the mod's to keep: it is in memory for as long as the screen is, and
 * nothing reads the table after that.
 */
RentalTable *Mod_RentalTable(void *archive, s32 number) {
    RentalTable *stock = Rentals_Table(archive, number);
    RentalTable *table;
    Rules *rules = Rules_InForce();
    Rental *extra = sExtraRentals;
    s32 extras = 0;
    s32 count = 0;
    s32 i;

    if (number != RENTALS_PRIME_CUP || stock == NULL || rules == NULL ||
        (*(u16 *)(gEntrySettings + ENTRY_SETTINGS_MODE) & 0xFF00) != MODE_FREE_BATTLE) {
        return stock;
    }
    table = Rentals_GetOwn();
    *(u32 *)table = 0;
    for (i = 0; i < stock->count; i++) {
        while (extras < NUM_EXTRA_RENTALS && extra[extras].species < stock->rentals[i].species) {
            count = Rentals_Add(table, count, rules, &extra[extras]);
            extras++;
        }
        count = Rentals_Add(table, count, rules, &stock->rentals[i]);
    }
    while (extras < NUM_EXTRA_RENTALS) {
        count = Rentals_Add(table, count, rules, &extra[extras]);
        extras++;
    }
    table->count = count;
    return table;
}
