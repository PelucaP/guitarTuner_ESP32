#include <inttypes.h>

#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_timer.h"
#include "esp_log.h"

#define BUTTON_GPIO        GPIO_NUM_4
#define DEBOUNCE_MS        50
/* Wiring: 3V3 -> button -> GPIO4, 10k from GPIO4 -> GND (idle LOW, press HIGH).
 * If your button pulls to GND with a 10k pull-up to 3V3, set this to 0. */
#define BUTTON_ACTIVE_HIGH 1

static const char *TAG = "btn-counter";
static QueueHandle_t s_evt_queue;

static void IRAM_ATTR button_isr(void *arg)
{
    uint32_t gpio = (uint32_t)(uintptr_t)arg;
    xQueueSendFromISR(s_evt_queue, &gpio, NULL);
}

void app_main(void)
{
    s_evt_queue = xQueueCreate(8, sizeof(uint32_t));
    configASSERT(s_evt_queue != NULL);

    const gpio_config_t cfg = {
        .pin_bit_mask = 1ULL << BUTTON_GPIO,
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = BUTTON_ACTIVE_HIGH ? GPIO_PULLUP_DISABLE : GPIO_PULLUP_ENABLE,
        .pull_down_en = BUTTON_ACTIVE_HIGH ? GPIO_PULLDOWN_ENABLE : GPIO_PULLDOWN_DISABLE,
        .intr_type    = BUTTON_ACTIVE_HIGH ? GPIO_INTR_POSEDGE : GPIO_INTR_NEGEDGE,
    };
    ESP_ERROR_CHECK(gpio_config(&cfg));
    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(BUTTON_GPIO, button_isr,
                                         (void *)(uintptr_t)BUTTON_GPIO));

    ESP_LOGI(TAG, "ready - press the button on GPIO%d", BUTTON_GPIO);

    uint32_t count = 0;
    int64_t last_edge_us = 0;
    uint32_t gpio;
    for (;;) {
        if (xQueueReceive(s_evt_queue, &gpio, portMAX_DELAY) != pdTRUE) {
            continue;
        }
        int64_t now_us = esp_timer_get_time();
        if (now_us - last_edge_us < DEBOUNCE_MS * 1000) {
            continue;  /* contact bounce */
        }
        last_edge_us = now_us;
        ESP_LOGI(TAG, "count = %" PRIu32, ++count);
    }
}
