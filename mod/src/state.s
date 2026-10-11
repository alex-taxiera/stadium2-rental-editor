# The editor's state, and the only code that takes its address.

.include "macro.inc"
.set noat
.set noreorder

.section .text

glabel Edit_GetState
    lui         $v0, %hi(gEditState)
    jr          $ra
     addiu      $v0, $v0, %lo(gEditState)

.section .bss

# sizeof(EditState), rounded up; see mod/include/edit.h
dlabel gEditState
    .space 0x110
