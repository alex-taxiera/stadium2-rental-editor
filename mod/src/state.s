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

.section .bss

# sizeof(EditState), rounded up; see mod/include/edit.h
dlabel gEditState
    .space 0x180

# sizeof(TrainerState), rounded up; see mod/include/trainer.h
.balign 16
dlabel gTrainerState
    .space 0x20C0
