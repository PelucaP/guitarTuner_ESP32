/*
 * Guitar tuner front end - ESP32-D0WD-V3 (WROOM-32E), MAX4466 OUT -> GPIO34.
 *
 * Everything except the detector itself is an Espressif-official building block:
 *
 *   Capture   adc_continuous + adc_continuous_parse_data
 *             $IDF_PATH/examples/peripherals/adc/continuous_read
 *   Level     adc_cali line fitting (eFuse VRef) -> real millivolts
 *   Filter    esp-dsp: dsps_biquad_gen_notch_f32 + dsps_biquad_f32 (LX6 asm)
 *             managed_components/espressif__esp-dsp/examples/iir
 *   Correlate esp-dsp: dsps_dotprod_f32 (LX6 asm), NSDF numerator
 *             managed_components/espressif__esp-dsp/examples/dotprod
 *
 * Espressif publishes no pitch/tuner library, so the detector is McLeod's MPM
 * (NSDF + first key maximum + parabolic interpolation) on top of the above.
 *
 * Chain: 20 kHz DMA -> 2048-sample window (102 ms) -> mains notch ->
 * DC removal -> MPM over lags 14..285 (70..1400 Hz) -> note + cents.
 *
 * GPIO34 is ADC1_CH6: no strapping, not shared with the radio, and eFuse VRef
 * calibration applies. VCC of the MAX4466 must be 3V3; its output idles at
 * ~Vcc/2. Mains hum is the accuracy killer: 60 Hz at half the guitar's
 * amplitude pulls the NSDF peak ~12 cents sharp. Set MAINS_HZ to 50 where the
 * grid is 50 Hz.
 */

#include <math.h>
#include <stdint.h>
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_continuous.h"
#include "esp_log.h"
#include "dsps_biquad.h"
#include "dsps_biquad_gen.h"
#include "dsps_dotprod.h"

#define MIC_ADC_UNIT    ADC_UNIT_1
#define MIC_ADC_CHANNEL ADC_CHANNEL_6   /* GPIO34 = ADC1_CH6 */

#define ADC_SAMPLE_HZ 20000             /* adc_continuous floor on ESP32 */
#define WINDOW        2048              /* 102 ms -> ~8 periods of E2 */
#define FRAME_BYTES   512               /* multiple of 4; 256 samples */

#define F_MIN       70.0f               /* below drop-D 73.4 Hz */
#define F_MAX       1400.0f             /* above E6 1318.5 Hz */
#define LAG_MIN     14                  /* ADC_SAMPLE_HZ / F_MAX */
#define LAG_MAX     285                 /* ADC_SAMPLE_HZ / F_MIN */
#define MPM_K       0.90f               /* first key max >= K * best */
#define CLARITY_MIN 0.80f               /* below this: no pitch */
#define RMS_MIN_MV  5

#define MAINS_HZ 60                     /* 50 where the grid is 50 Hz */
#define NOTCH_Q  8.0f                   /* ~MAINS_HZ/Q wide */

static const char *TAG = "pitch";
static const char *NOTE_NAME[12] = {"C", "C#", "D", "D#", "E", "F",
                                    "F#", "G", "G#", "A", "A#", "B"};

/* Filtered, DC-free analysis window and its prefix sums of squares, rebuilt
 * every window. sq[] turns the NSDF denominator into two lookups. */
static float x[WINDOW];
static float scratch[WINDOW];
static float sq[WINDOW + 1];

static float notch1_coef[5], notch2_coef[5];
static float notch1_w[2], notch2_w[2];

/*
 * McLeod Pitch Method over a DC-free window. Returns f0 in Hz, or 0 if the
 * NSDF never gets clear enough. *clarity gets the best NSDF value (0..1).
 *
 * nsdf(t) = 2*sum(x[j]*x[j+t]) / sum(x[j]^2 + x[j+t]^2)
 * Numerator: esp-dsp dot product. Denominator: prefix sums, because
 * sum(x[j+t]^2, j < N-t) is sq[N-t] + (sq[N] - sq[t]).
 */
static float detect_pitch(const float *v, float *clarity)
{
    static float nsdf[LAG_MAX + 2];
    float best = 0.0f;

    for (int tau = LAG_MIN - 1; tau <= LAG_MAX + 1; tau++) {
        float ac = 0.0f;
        ESP_ERROR_CHECK(dsps_dotprod_f32(v, &v[tau], &ac, WINDOW - tau));
        float m = sq[WINDOW - tau] + (sq[WINDOW] - sq[tau]);
        nsdf[tau] = (m > 1e-6f) ? 2.0f * ac / m : 0.0f;
        if (nsdf[tau] > best) {
            best = nsdf[tau];
        }
    }
    *clarity = best;

    if (best < CLARITY_MIN) {
        return 0.0f;
    }

    /* First (shortest-lag) strong maximum: avoids reporting the octave below. */
    float thresh = MPM_K * best;
    for (int tau = LAG_MIN; tau <= LAG_MAX; tau++) {
        if (nsdf[tau] < thresh || nsdf[tau] <= nsdf[tau - 1] || nsdf[tau] < nsdf[tau + 1]) {
            continue;
        }
        float y0 = nsdf[tau - 1], y1 = nsdf[tau], y2 = nsdf[tau + 1];
        float den = y0 - 2.0f * y1 + y2;
        float d = 0.0f;
        if (fabsf(den) > 1e-6f) {
            d = 0.5f * (y0 - y2) / den;
            if (d > 0.5f) d = 0.5f;
            if (d < -0.5f) d = -0.5f;
        }
        return (float)ADC_SAMPLE_HZ / ((float)tau + d);
    }
    return 0.0f;
}

void app_main(void)
{
    adc_continuous_handle_t adc = NULL;
    adc_continuous_handle_cfg_t hcfg = {
        .max_store_buf_size = 8192,     /* 205 ms of backlog */
        .conv_frame_size = FRAME_BYTES,
    };
    ESP_ERROR_CHECK(adc_continuous_new_handle(&hcfg, &adc));

    adc_digi_pattern_config_t pattern = {
        .atten = ADC_ATTEN_DB_12,
        .channel = MIC_ADC_CHANNEL,
        .unit = MIC_ADC_UNIT,
        .bit_width = SOC_ADC_DIGI_MAX_BITWIDTH,
    };
    adc_continuous_config_t cfg = {
        .pattern_num = 1,
        .adc_pattern = &pattern,
        .sample_freq_hz = ADC_SAMPLE_HZ,
        .conv_mode = ADC_CONV_SINGLE_UNIT_1,
    };
    ESP_ERROR_CHECK(adc_continuous_config(adc, &cfg));

    adc_cali_handle_t cali = NULL;
    adc_cali_line_fitting_config_t cali_cfg = {
        .unit_id = MIC_ADC_UNIT,
        .atten = ADC_ATTEN_DB_12,
        .bitwidth = ADC_BITWIDTH_DEFAULT,
        .default_vref = 1100,           /* only used if eFuse VRef is absent */
    };
    ESP_ERROR_CHECK(adc_cali_create_scheme_line_fitting(&cali_cfg, &cali));

    ESP_ERROR_CHECK(adc_continuous_start(adc));

    /* Normalised frequency (the generator takes fs = 1), unity depth. */
    ESP_ERROR_CHECK(dsps_biquad_gen_notch_f32(notch1_coef, (float)MAINS_HZ / ADC_SAMPLE_HZ, 0.0f, NOTCH_Q));
    ESP_ERROR_CHECK(dsps_biquad_gen_notch_f32(notch2_coef, 2.0f * (float)MAINS_HZ / ADC_SAMPLE_HZ, 0.0f, NOTCH_Q));

    ESP_LOGI(TAG, "GPIO34/ADC1_CH6, %d Hz, %d-sample window, notches %d+%d Hz",
             ADC_SAMPLE_HZ, WINDOW, MAINS_HZ, 2 * MAINS_HZ);

    static uint8_t frame[FRAME_BYTES] __attribute__((aligned(4)));
    static int16_t raw[WINDOW];
    static adc_continuous_data_t parsed[FRAME_BYTES / SOC_ADC_DIGI_RESULT_BYTES];

    for (;;) {
        int fill = 0;
        while (fill < WINDOW) {
            uint32_t n = 0;
            esp_err_t err = adc_continuous_read(adc, frame, FRAME_BYTES, &n, 1000);
            if (err != ESP_OK) {
                ESP_LOGW(TAG, "adc read: %s", esp_err_to_name(err));
                vTaskDelay(pdMS_TO_TICKS(100));
                continue;
            }
            uint32_t ns = 0;
            ESP_ERROR_CHECK(adc_continuous_parse_data(adc, frame, n, parsed, &ns));
            for (uint32_t i = 0; i < ns && fill < WINDOW; i++) {
                if (parsed[i].valid && parsed[i].channel == MIC_ADC_CHANNEL) {
                    raw[fill++] = (int16_t)parsed[i].raw_data;
                }
            }
        }

        for (int i = 0; i < WINDOW; i++) {
            x[i] = (float)raw[i];
        }
        ESP_ERROR_CHECK(dsps_biquad_f32(x, scratch, WINDOW, notch1_coef, notch1_w));
        ESP_ERROR_CHECK(dsps_biquad_f32(scratch, x, WINDOW, notch2_coef, notch2_w));

        float sum = 0.0f;
        for (int i = 0; i < WINDOW; i++) {
            sum += x[i];
        }
        float mean = sum / WINDOW;
        sq[0] = 0.0f;
        for (int i = 0; i < WINDOW; i++) {
            x[i] -= mean;
            sq[i + 1] = sq[i] + x[i] * x[i];
        }

        /* Level from eFuse calibration: slope of the raw->mV curve at the bias. */
        int rms_codes = (int)lroundf(sqrtf(sq[WINDOW] / WINDOW));
        int bias = (int)lroundf(mean);
        int dc_mv = 0, hi_mv = 0;
        int hi = (bias + rms_codes < 4095) ? bias + rms_codes : 4095;
        ESP_ERROR_CHECK(adc_cali_raw_to_voltage(cali, bias, &dc_mv));
        ESP_ERROR_CHECK(adc_cali_raw_to_voltage(cali, hi, &hi_mv));
        int rms_mv = hi_mv - dc_mv;

        if (rms_mv < RMS_MIN_MV) {
            ESP_LOGI(TAG, "no signal (rms=%d mV, dc=%d mV)", rms_mv, dc_mv);
            continue;
        }

        float clarity = 0.0f;
        float f = detect_pitch(x, &clarity);
        if (f < F_MIN * 0.5f) {
            ESP_LOGI(TAG, "no pitch (rms=%d mV, dc=%d mV, clarity=%d%%)",
                     rms_mv, dc_mv, (int)(clarity * 100.0f));
            continue;
        }

        float midi_f = 69.0f + 12.0f * log2f(f / 440.0f);
        int midi = (int)lroundf(midi_f);
        if (midi < 0 || midi > 127) {
            ESP_LOGI(TAG, "no pitch (rms=%d mV, clarity=%d%%)", rms_mv, (int)(clarity * 100.0f));
            continue;
        }
        int cents = (int)lroundf((midi_f - (float)midi) * 100.0f);
        int hz10 = (int)lroundf(f * 10.0f);

        ESP_LOGI(TAG, "%s%d  %d.%d Hz  %+d cents  rms=%d mV  dc=%d mV  clarity=%d%%",
                 NOTE_NAME[midi % 12], midi / 12 - 1, hz10 / 10, hz10 % 10, cents,
                 rms_mv, dc_mv, (int)(clarity * 100.0f));
    }
}
