#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>

int main(void)
{
    while (1) {
        printk("boot ok\n"); /* PROJECT-DEFINED (stable Stage 0 UART signature) */
        k_msleep(1000); /* PROJECT-DEFINED (slow repeat so Stage 0 can catch the line reliably) */
    }

    return 0;
}
