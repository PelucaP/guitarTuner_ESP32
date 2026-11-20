/*
 * NEMA 17 + DRV8825 on an ESP32-WROOM-32.
 *
 *   ESP32            DRV8825 module
 *   GPIO27  -------> STEP
 *   GPIO26  -------> DIR
 *   GND     -------> GND  (logic + motor supply ground, must be common)
 *
 * Optional: nENBL, M0, M1, M2 - see drv8825_config_t.
 */
#include <inttypes.h>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "drv8825.h"

#define PIN_STEP    GPIO_NUM_18
#define PIN_DIR     GPIO_NUM_19

static const char *TAG = "app";

static drv8825_t s_motor;

void app_main(void)
{
    const drv8825_config_t config = {
        .step_gpio = PIN_STEP,
        .dir_gpio = PIN_DIR,
        .en_gpio = GPIO_NUM_NC,   /* nENBL tied to GND on the module */
        .m0_gpio = GPIO_NUM_NC,   /* microstep pins set by jumpers */
        .m1_gpio = GPIO_NUM_NC,
        .m2_gpio = GPIO_NUM_NC,
        .microstep = DRV8825_MICROSTEP_1_16,
        .dir_cw_level = 0,
        .speed_hz = 2000,         /* microsteps/s -> 0.625 rev/s at 1/16 */
        .accel_steps = 400,
    };
    ESP_ERROR_CHECK(drv8825_init(&s_motor, &config));

    const int32_t rev = drv8825_steps_per_rev(config.microstep);
    ESP_LOGI(TAG, "%" PRId32 " microsteps per revolution", rev);

    while (true) {
        ESP_LOGI(TAG, "one revolution clockwise");
        ESP_ERROR_CHECK(drv8825_move(&s_motor, rev));
        vTaskDelay(pdMS_TO_TICKS(1000));

        ESP_LOGI(TAG, "one revolution counter-clockwise");
        ESP_ERROR_CHECK(drv8825_move(&s_motor, -rev));
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
