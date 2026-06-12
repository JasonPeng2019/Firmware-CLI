/* Linker script for nRF52840 bare-metal reference firmware
 *
 * Memory layout -- HW-FIXED (nRF52840 Product Specification §Memory):
 *   Flash : 0x00000000, 1 MB
 *   RAM   : 0x20000000, 256 KB
 *
 * Stack size -- PROJECT-DEFINED (2 KB is sufficient for this blink demo)
 */

MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 1024K
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 256K
}

_stack_size = 2048;  /* PROJECT-DEFINED */

SECTIONS
{
    /* Vector table must sit at the flash base so the CPU finds it on reset.
     * HW-FIXED (ARMv7-M ARM §B1.5.3: initial SP at offset 0, Reset at offset 4). */
    .vectors :
    {
        KEEP(*(.vectors))
    } > FLASH

    .text :
    {
        *(.text*)
        *(.rodata*)
    } > FLASH

    .bss (NOLOAD) :
    {
        *(.bss*)
        *(COMMON)
    } > RAM

    /* Stack grows downward from _stack_top. */
    .stack (NOLOAD) :
    {
        . = ALIGN(8);
        . += _stack_size;
        _stack_top = .;
    } > RAM
}
