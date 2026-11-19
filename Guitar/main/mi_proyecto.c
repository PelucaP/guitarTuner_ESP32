#include <stdio.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

// ESP-DSP Component Headers
#include "esp_dsp.h"
#include "dsps_wind_hann.h"
#include "dsps_view.h"

//LSM9DS1


// Etiqueta para identificar tus mensajes en el monitor serie
static const char *TAG = "MI_SISTEMA";

#define FFT_SIZE      1024   // Must be a power of 2 (e.g., 512, 1024, 2048)
#define SAMPLE_RATE   16000  // Sample rate in Hz (common for voice/audio analysis)
#define TARGET_FREQ   1000   // Mock signal frequency in Hz (we will look for this)
#define I2C_SDA 8 //IO8
#define I2C_SCL 9 //IO9
#define LED 40 //IO40

__attribute__((aligned(16))) float input_signal[FFT_SIZE];
__attribute__((aligned(16))) float fft_buffer[FFT_SIZE * 2]; // Needs 2x size for complex pairs
__attribute__((aligned(16))) float window[FFT_SIZE];
__attribute__((aligned(16))) float magnitude[FFT_SIZE / 2];


void app_main(void)
{

    ESP_LOGI(TAG, "Iniciando la aplicacion...");

    if (dsps_fft2r_init_fc32(NULL, CONFIG_DSP_MAX_FFT_SIZE) != ESP_OK) {
        ESP_LOGE(TAG, "Error al inicializar la FFT");
        return;
    }

    dsps_wind_hann_f32(window, FFT_SIZE);

    for (int i = 0; i < FFT_SIZE; i++) {
        float time = (float)i / SAMPLE_RATE;
        // Generación de una señal de prueba de 1000hz
        input_signal[i] = sinf(2 * M_PI * TARGET_FREQ * time); 
    }

    for (int i = 0; i < FFT_SIZE; i++) {
        fft_buffer[i * 2 + 0] = input_signal[i]; // parte real
        fft_buffer[i * 2 + 1] = 0.0f;            // parte imaginaria
    }

    dsps_fft2r_fc32(fft_buffer, FFT_SIZE);

    dsps_bit_rev_fc32(fft_buffer, FFT_SIZE);

    dsps_cplx2reC_fc32(fft_buffer, FFT_SIZE);

    float max_magnitude = 0;
    int peak_bin = 0;

    for (int i = 0; i < FFT_SIZE / 2; i++) {
        float real = fft_buffer[i * 2 + 0];
        float imag = fft_buffer[i * 2 + 1];
        
        // Amplitud = sqrt(real^2 + imag^2)
        magnitude[i] = sqrtf(real * real + imag * imag);

        if (magnitude[i] > max_magnitude) {
            max_magnitude = magnitude[i];
            peak_bin = i;
        }
    }

    
    float detected_frequency = (float)peak_bin * ((float)SAMPLE_RATE / (float)FFT_SIZE);

    ESP_LOGI(TAG, "===============================================");
    ESP_LOGI(TAG, "Dominant Peak detected at Bin: %d", peak_bin);
    ESP_LOGI(TAG, "Estimated Frequency: %.2f Hz (Expected: %d Hz)", detected_frequency, TARGET_FREQ);
    ESP_LOGI(TAG, "Peak Magnitude Value: %.2f", max_magnitude);
    ESP_LOGI(TAG, "===============================================");

}