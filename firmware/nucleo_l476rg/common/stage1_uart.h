#pragma once

#include <stdbool.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>

#define STAGE1_UART_NODE DT_NODELABEL(usart2)

#if !DT_NODE_HAS_STATUS(STAGE1_UART_NODE, okay)
#error "nucleo_l476rg Stage 1 firmware requires USART2 for the ST-LINK VCP path"
#endif

static inline bool stage1_uart_ready(void)
{
    return device_is_ready(DEVICE_DT_GET(STAGE1_UART_NODE));
}

static inline void stage1_uart_write_line(const char *text)
{
    const struct device *uart = DEVICE_DT_GET(STAGE1_UART_NODE);

    if (!device_is_ready(uart)) {
        return;
    }

    for (const char *cursor = text; *cursor != '\0'; ++cursor) {
        uart_poll_out(uart, (unsigned char)*cursor);
    }
}
