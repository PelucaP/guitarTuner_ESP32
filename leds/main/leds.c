#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"

#define LED_GPIO    GPIO_NUM_18
#define BUTTON_GPIO GPIO_NUM_4   /* button to 3V3, 10 kOhm pull-down to GND */

static SemaphoreHandle_t s_button_pressed;

static void IRAM_ATTR button_isr(void *arg)
{
    BaseType_t woken = pdFALSE;
    xSemaphoreGiveFromISR(s_button_pressed, &woken);
    portYIELD_FROM_ISR(woken);
}

void app_main(void)
{
    ESP_ERROR_CHECK(gpio_reset_pin(LED_GPIO));
    ESP_ERROR_CHECK(gpio_set_direction(LED_GPIO, GPIO_MODE_OUTPUT));

    gpio_config_t btn = {
        .pin_bit_mask = 1ULL << BUTTON_GPIO,
        .mode         = GPIO_MODE_INPUT,
        .pull_up_en   = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_ENABLE, /* idle = 0 V, press = 3.3 V */
        .intr_type    = GPIO_INTR_POSEDGE,    /* trigger on press */
    };
    ESP_ERROR_CHECK(gpio_config(&btn));

    s_button_pressed = xSemaphoreCreateBinary();
    configASSERT(s_button_pressed);

    ESP_ERROR_CHECK(gpio_install_isr_service(0));
    ESP_ERROR_CHECK(gpio_isr_handler_add(BUTTON_GPIO, button_isr, NULL));

    bool led_on = false;
    while (1) {
        if (xSemaphoreTake(s_button_pressed, portMAX_DELAY) == pdTRUE) {
            vTaskDelay(pdMS_TO_TICKS(30));   /* let the contacts settle */
            if (gpio_get_level(BUTTON_GPIO) == 1) {
                led_on = !led_on;
                ESP_ERROR_CHECK(gpio_set_level(LED_GPIO, led_on));
            }
        }
    }
}
