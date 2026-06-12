/*
 * LED chase blink + UART output -- nRF52840-DK reference firmware
 *
 * LED behaviour: cycles LED1→LED2→LED3→LED4→LED3→LED2, ~0.5 s per step.
 * UART: prints which LED is active on every step at 115200 8N1.
 *   Open /dev/cu.usbmodem0010502864803 (or ...801) at 115200 to read it.
 *
 * No SDK, no RTOS, no interrupts -- pure register access.
 *
 * ---------- GPIO P0 -- HW-FIXED (nRF52840 PS §GPIO, Table 1) ----------
 *   Base 0x50000000  OUTSET +0x508  OUTCLR +0x50C  DIRSET +0x518
 *
 * ---------- LED pins -- HW-FIXED (nRF52840-DK schematic, active-low) ---
 *   LED1 P0.13  LED2 P0.14  LED3 P0.15  LED4 P0.16
 *
 * ---------- UART0 -- HW-FIXED (nRF52840 PS §UART, base 0x40002000) -----
 *   TASKS_STARTTX +0x008  EVENTS_TXDRDY +0x11C  ENABLE +0x500
 *   PSEL.TXD +0x50C  PSEL.RXD +0x514  TXD +0x51C  BAUDRATE +0x524
 *
 * ---------- UART pins -- HW-FIXED (nRF52840-DK schematic) ---------------
 *   TX P0.06  RX P0.08
 */

/* No <stdint.h>: osx-cross arm-none-eabi-gcc ships without newlib headers.
 * unsigned int = 32-bit, unsigned char = 8-bit on ARMv7-M -- HW-FIXED */
typedef unsigned int   uint32_t;
typedef unsigned char  uint8_t;

/* -------------------------------------------------------------------------
 * GPIO
 * ---------------------------------------------------------------------- */
#define GPIO_P0_BASE  0x50000000UL  /* HW-FIXED */
#define P0_OUTSET  (*(volatile uint32_t *)(GPIO_P0_BASE + 0x508u))
#define P0_OUTCLR  (*(volatile uint32_t *)(GPIO_P0_BASE + 0x50Cu))
#define P0_DIRSET  (*(volatile uint32_t *)(GPIO_P0_BASE + 0x518u))

#define LED1_PIN  13u  /* HW-FIXED */
#define LED2_PIN  14u  /* HW-FIXED */
#define LED3_PIN  15u  /* HW-FIXED */
#define LED4_PIN  16u  /* HW-FIXED */
#define LED_MASK  ((1u<<LED1_PIN)|(1u<<LED2_PIN)|(1u<<LED3_PIN)|(1u<<LED4_PIN))

/* -------------------------------------------------------------------------
 * UART0
 * ---------------------------------------------------------------------- */
#define UART0_BASE       0x40002000UL  /* HW-FIXED */
#define UART_STARTTX     (*(volatile uint32_t *)(UART0_BASE + 0x008u))
#define UART_TXDRDY      (*(volatile uint32_t *)(UART0_BASE + 0x11Cu))
#define UART_ENABLE      (*(volatile uint32_t *)(UART0_BASE + 0x500u))
#define UART_PSELTXD     (*(volatile uint32_t *)(UART0_BASE + 0x50Cu))
#define UART_PSELRXD     (*(volatile uint32_t *)(UART0_BASE + 0x514u))
#define UART_TXD         (*(volatile uint32_t *)(UART0_BASE + 0x51Cu))
#define UART_BAUDRATE    (*(volatile uint32_t *)(UART0_BASE + 0x524u))

/* HW-FIXED (nRF52840-DK schematic): UART routed to J-Link virtual COM port */
#define UART_TX_PIN  6u   /* P0.06 */
#define UART_RX_PIN  8u   /* P0.08 */

/* HW-FIXED (nRF52840 PS Table 559): baudrate register value for 115200 */
#define BAUD_115200  0x01D7E000u

/* UART ENABLE value 4 = enable -- VENDOR-FIXED (nRF52840 PS §UART.ENABLE) */
#define UART_ENABLE_VAL  4u

static void uart_init(void)
{
    UART_PSELTXD  = UART_TX_PIN;
    UART_PSELRXD  = UART_RX_PIN;
    UART_BAUDRATE = BAUD_115200;
    UART_ENABLE   = UART_ENABLE_VAL;
    UART_STARTTX  = 1u;
}

static void uart_putc(uint8_t c)
{
    UART_TXDRDY = 0u;
    UART_TXD    = (uint32_t)c;
    while (UART_TXDRDY == 0u) { }
}

static void uart_puts(const char *s)
{
    while (*s) {
        uart_putc((uint8_t)*s++);
    }
}

/* -------------------------------------------------------------------------
 * Delay
 * ---------------------------------------------------------------------- */
/* At the nRF52840 default 64 MHz clock, ~1 200 000 NOPs ≈ 0.5 s.
 * Exact timing UNVERIFIED on real hardware; tune DELAY_TICKS if needed. */
#define DELAY_TICKS  1200000u  /* PROJECT-DEFINED, UNVERIFIED */

static void delay(volatile uint32_t ticks)
{
    while (ticks--) {
        __asm__ volatile ("nop");
    }
}

/* -------------------------------------------------------------------------
 * Entry point
 * ---------------------------------------------------------------------- */
void main_app(void)
{
    /* LED outputs */
    P0_DIRSET = LED_MASK;
    P0_OUTSET = LED_MASK;   /* all off (active-low) */

    uart_init();
    uart_puts("nRF52840-DK blink firmware starting\r\n");

    static const uint8_t chase[] = {
        LED1_PIN, LED2_PIN, LED3_PIN, LED4_PIN, LED3_PIN, LED2_PIN
    };
    static const char * const labels[] = {
        "LED1 on (P0.13)\r\n",
        "LED2 on (P0.14)\r\n",
        "LED3 on (P0.15)\r\n",
        "LED4 on (P0.16)\r\n",
        "LED3 on (P0.15)\r\n",
        "LED2 on (P0.14)\r\n",
    };
    uint32_t step = 0;

    for (;;) {
        uint32_t idx = step % (sizeof chase / sizeof chase[0]);
        P0_OUTSET = LED_MASK;
        P0_OUTCLR = (1u << chase[idx]);
        uart_puts(labels[idx]);
        delay(DELAY_TICKS);
        step++;
    }
}
