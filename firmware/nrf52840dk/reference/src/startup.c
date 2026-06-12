/*
 * Minimal startup for nRF52840 bare-metal firmware.
 *
 * Provides only the two entries the CPU needs on reset:
 *   [0] Initial stack pointer   -- HW-FIXED (ARMv7-M ARM §B1.5.3)
 *   [1] Reset_Handler address   -- HW-FIXED (ARMv7-M ARM §B1.5.3)
 *
 * All other interrupt vectors are omitted; they default to 0 (unhandled faults
 * are acceptable for this LED-blink demo that never uses interrupts).
 */

/* No <stdint.h>: osx-cross arm-none-eabi-gcc ships without newlib headers.
 * Define only the types we actually use.
 * unsigned int is 32-bit on ARMv7-M -- HW-FIXED (ARMv7-M ARM §A2.1) */
typedef unsigned int  uint32_t;

extern uint32_t _stack_top;  /* defined in nrf52840.ld */
extern void main_app(void);

void Reset_Handler(void)
{
    main_app();
    for (;;);  /* should never return */
}

__attribute__((section(".vectors"), used))
const void * const g_pfnVectors[] = {
    (void *)&_stack_top,    /* initial SP */
    (void *)Reset_Handler,  /* reset vector */
};
