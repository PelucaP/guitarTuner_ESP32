#include "button_gpio.h"
#include "esp_err.h"
#include "esp_log.h"
#include "iot_button.h"

#define BUTTON_GPIO         GPIO_NUM_4
/* Wiring: 3V3 -> button -> GPIO4, 10k from GPIO4 -> GND (idle LOW, press HIGH).
 * Button to GND with a pull-up instead? Set this to 0. */
#define BUTTON_ACTIVE_LEVEL 1
#define BUTTON_SHORT_MS     200
#define BUTTON_LONG_MS      1500

static const char *TAG = "button-test";

static void on_button_event(void *handle, void *usr_data)
{
    (void)usr_data;
    button_event_t event = iot_button_get_event((button_handle_t)handle);
    ESP_LOGI(TAG, "%s", iot_button_get_event_str(event));
}

void app_main(void)
{
    const button_config_t button_cfg = {
        .long_press_time = BUTTON_LONG_MS,
        .short_press_time = BUTTON_SHORT_MS,
    };
    const button_gpio_config_t gpio_cfg = {
        .gpio_num = BUTTON_GPIO,
        .active_level = BUTTON_ACTIVE_LEVEL,
        /* Timer is stopped while idle and restarted by the GPIO edge ISR.
         * The component still samples every 5 ms while a gesture is in progress. */
        .enable_power_save = true,
    };

    button_handle_t btn = NULL;
    ESP_ERROR_CHECK(iot_button_new_gpio_device(&button_cfg, &gpio_cfg, &btn));

    ESP_ERROR_CHECK(iot_button_register_cb(btn, BUTTON_SINGLE_CLICK, NULL, on_button_event, NULL));
    ESP_ERROR_CHECK(iot_button_register_cb(btn, BUTTON_DOUBLE_CLICK, NULL, on_button_event, NULL));
    ESP_ERROR_CHECK(iot_button_register_cb(btn, BUTTON_LONG_PRESS_START, NULL, on_button_event, NULL));

    ESP_LOGI(TAG, "ready on GPIO%d (active %s): short=%dms long=%dms",
             (int)BUTTON_GPIO, BUTTON_ACTIVE_LEVEL ? "HIGH" : "LOW",
             BUTTON_SHORT_MS, BUTTON_LONG_MS);
}
