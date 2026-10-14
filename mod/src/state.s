# The mod's state, and the only code that takes its addresses.

.include "macro.inc"
.set noat
.set noreorder

.section .text

glabel Edit_GetState
    lui         $v0, %hi(gEditState)
    jr          $ra
     addiu      $v0, $v0, %lo(gEditState)

glabel Trainer_GetState
    lui         $v0, %hi(gTrainerState)
    jr          $ra
     addiu      $v0, $v0, %lo(gTrainerState)

glabel Rentals_GetOwn
    lui         $v0, %hi(gRentalTable)
    jr          $ra
     addiu      $v0, $v0, %lo(gRentalTable)

# Where C code would reach into a stock fragment's data at more than one offset, the
# address is taken here as well: the compiler may share one `lui` between the offsets,
# which the loader can get wrong for a fragment as it can for the mod.

# The rule viewer's state (fragment 83).
glabel RuleViewer_GetState
    lui         $v0, %hi(D_82C04C38)
    jr          $ra
     addiu      $v0, $v0, %lo(D_82C04C38)

# The rule editor's page (fragment 82).
glabel RuleEdit_GetPage
    lui         $v0, %hi(D_82D23830)
    jr          $ra
     addiu      $v0, $v0, %lo(D_82D23830)

# The rectangle of that page's window (fragment 82).
glabel RuleEdit_PageWindow
    lui         $v0, %hi(D_82D07174)
    jr          $ra
     addiu      $v0, $v0, %lo(D_82D07174)

# Called from func_8130DEB8, the detail panel's drawing, where it set the colour of a
# move's name from the move's type (mod/asm_patches.txt). The loop it is in has the
# Pokemon's record plus the slot in $s1 and four times the slot in $s3.
glabel Mod_PanelMoveColorShim
    or          $a1, $s1, $zero
    j           Mod_PanelMoveColor
     or         $a2, $s3, $zero

.section .bss

# sizeof(EditState), rounded up; see mod/include/edit.h
dlabel gEditState
    .space 0x180

# sizeof(TrainerState), rounded up; see mod/include/trainer.h
.balign 16
dlabel gTrainerState
    .space 0x20C0

# A table of MAX_RENTALS rental Pokemon, rounded up; see mod/src/rentals.c
.balign 16
dlabel gRentalTable
    .space 0x1790
