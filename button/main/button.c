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

typedef struct {
    const char *name;
    float       hz;
} guitar_string_t;

static const guitar_string_t GUITAR_STRINGS[] = {
    {"E2",  82.41f},
    {"A2", 110.00f},
    {"D3", 146.83f},
    {"G3", 196.00f},
    {"B3", 246.94f},
    {"E4", 329.63f},
};
#define GUITAR_STRING_COUNT (sizeof(GUITAR_STRINGS) / sizeof(GUITAR_STRINGS[0]))

static size_t s_string_idx;   /* 0 = E2, the low string */

static void select_next_string(void)
{
    s_string_idx = (s_string_idx + 1) % GUITAR_STRING_COUNT;
    ESP_LOGI(TAG, "target %s: %.2f Hz", GUITAR_STRINGS[s_string_idx].name,
             GUITAR_STRINGS[s_string_idx].hz);
}

static void on_button_event(void *handle, void *usr_data)
{
    (void)usr_data;
    button_event_t event = iot_button_get_event((button_handle_t)handle);

    if (event == BUTTON_SINGLE_CLICK) {
        select_next_string();
    } else {
        ESP_LOGI(TAG, "%s", iot_button_get_event_str(event));
    }
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

    ESP_LOGI(TAG, "ready on GPIO%d (active %s); start on %s (%.2f Hz), single click cycles",
             (int)BUTTON_GPIO, BUTTON_ACTIVE_LEVEL ? "HIGH" : "LOW",
             GUITAR_STRINGS[s_string_idx].name, GUITAR_STRINGS[s_string_idx].hz);
}
