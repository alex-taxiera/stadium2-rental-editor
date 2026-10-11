/*
 * The rental editor's fragment: id 0x40, linked at 0x85000000.
 * Layout matches the stock fragments: header, code, data, read-only data, and then
 * BSS starting where the relocation table is stored in ROM.
 */

SECTIONS
{
    .modfrag 0x85000000 : SUBALIGN(16)
    {
        FILL(0x00000000);
        build/mod/entry.o(.text);
        *(.text*);
        . = ALIGN(16);
        *(.data*);
        . = ALIGN(16);
        *(.rodata*);
        *(.late_rodata*);
        . = ALIGN(16);
    }

    .modfrag_bss (NOLOAD) : SUBALIGN(16)
    {
        *(.bss*);
        *(COMMON);
        *(.sbss*);
        *(.scommon*);
        . = ALIGN(16);
    }

    /DISCARD/ :
    {
        *(.reginfo);
        *(.MIPS.abiflags);
        *(.mdebug*);
        *(.pdr);
        *(.comment);
        *(.options);
        *(.gptab*);
        *(.gnu.attributes);
        *(.note*);
    }
}
