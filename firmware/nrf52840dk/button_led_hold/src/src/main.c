#include <stddef.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/util.h>

#define BUTTON_LED_PAIR(button_alias, led_alias)                                             \
	{                                                                                    \
		.button = GPIO_DT_SPEC_GET(DT_ALIAS(button_alias), gpios),                   \
		.led = GPIO_DT_SPEC_GET(DT_ALIAS(led_alias), gpios),                         \
	}

BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(sw0), okay), "Board must define sw0");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(sw1), okay), "Board must define sw1");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(sw2), okay), "Board must define sw2");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(sw3), okay), "Board must define sw3");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(led0), okay), "Board must define led0");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(led1), okay), "Board must define led1");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(led2), okay), "Board must define led2");
BUILD_ASSERT(DT_NODE_HAS_STATUS(DT_ALIAS(led3), okay), "Board must define led3");

struct button_led {
	struct gpio_dt_spec button;
	struct gpio_dt_spec led;
};

static const struct button_led pairs[] = {
	BUTTON_LED_PAIR(sw0, led0),
	BUTTON_LED_PAIR(sw1, led1),
	BUTTON_LED_PAIR(sw2, led2),
	BUTTON_LED_PAIR(sw3, led3),
};

int main(void)
{
	for (size_t i = 0; i < ARRAY_SIZE(pairs); i++) {
		if (!gpio_is_ready_dt(&pairs[i].button) || !gpio_is_ready_dt(&pairs[i].led)) {
			return 1;
		}

		if (gpio_pin_configure_dt(&pairs[i].button, GPIO_INPUT) != 0) {
			return 1;
		}

		if (gpio_pin_configure_dt(&pairs[i].led, GPIO_OUTPUT_INACTIVE) != 0) {
			return 1;
		}
	}

	while (1) {
		for (size_t i = 0; i < ARRAY_SIZE(pairs); i++) {
			int pressed = gpio_pin_get_dt(&pairs[i].button);

			if (pressed >= 0) {
				(void)gpio_pin_set_dt(&pairs[i].led, pressed);
			}
		}

		k_msleep(10);
	}

	return 0;
}
