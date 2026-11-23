/*
 * MAX4466 electret mic amp -> ESP32-WROOM-32 (classic ESP32).
 *
 * Wiring: VCC -> 3V3 (NOT 5V: the amp output can swing to its rail),
 *         GND -> GND, OUT -> GPIO2.
 *
 * GPIO2 is usable but a poor choice on this chip, twice over:
 *   - GPIO2 = ADC2_CH2, and ADC2 is shared with the Wi-Fi driver. Readings fail
 *     with ESP_ERR_TIMEOUT the moment Wi-Fi/BT is initialised. ADC1 never has
 *     this problem: GPIO34/35/32/33 = ADC1_CH6/CH7/CH4/CH5.
 *   - GPIO2 is a strapping pin. It must be high or floating at reset; the amp
 *     holds it at ~Vcc/2 (1.65 V), inside the undefined logic band. If the board
 *     ever refuses to boot, that is why.
 * To move to ADC1: change MIC_ADC_CHANNEL (and the wire). Nothing else.
 *
 * Expected log with silence: dc ~1650 mV, pp < 20 mV.
 * Talk / clap next to it: pp jumps to hundreds of mV.
 * dc near 0 or near 3300 mV = miswired or module unpowered.
 *
 * shortcut: oneshot polling (~tens of kSa/s, jittery) is enough to prove the
 * mic works but cannot measure frequency. Upgrade to ADC continuous mode or
 * I2S when you need real audio for the tuner.
 */

#include <stdbool.h>
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_adc/adc_oneshot.h"

#define MIC_ADC_UNIT    ADC_UNIT_1
#define MIC_ADC_CHANNEL ADC_CHANNEL_2   /* GPIO2 = ADC2_CH2 (see warning above) */
#define WINDOW          1024
#define VREF_MV         3100            /* ~full scale at ADC_ATTEN_DB_12 */

static const char *TAG = "mic";

void app_main(void)
{
    adc_oneshot_unit_handle_t adc;
    adc_oneshot_unit_init_cfg_t unit_cfg = {
        .unit_id = MIC_ADC_UNIT,
    };
    ESP_ERROR_CHECK(adc_oneshot_new_unit(&unit_cfg, &adc));

    adc_oneshot_chan_cfg_t chan_cfg = {
        .atten    = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
    };
    ESP_ERROR_CHECK(adc_oneshot_config_channel(adc, MIC_ADC_CHANNEL, &chan_cfg));

    while (true) {
        int lo = 4095, hi = 0, sum = 0;
        bool ok = true;

        for (int i = 0; i < WINDOW; i++) {
            int raw;
            esp_err_t err = adc_oneshot_read(adc, MIC_ADC_CHANNEL, &raw);
            if (err != ESP_OK) {
                /* On ADC2 this fires once Wi-Fi starts talking. Do not abort(): that reboots. */
                ESP_LOGW(TAG, "adc read: %s", esp_err_to_name(err));
                ok = false;
                break;
            }
            if (raw < lo) lo = raw;
            if (raw > hi) hi = raw;
            sum += raw;
        }

        if (ok) {
            int mean = sum / WINDOW;
            /* Linear, uncalibrated: fine for spotting a dead or miswired module. */
            ESP_LOGI(TAG, "dc=%4d mV  pp=%4d mV",
                     mean * VREF_MV / 4095, (hi - lo) * VREF_MV / 4095);
        }

        vTaskDelay(pdMS_TO_TICKS(200));
    }
}
