#include <stdio.h>
#include <math.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "esp_log.h"

// ESP-DSP Component Headers
#include "esp_dsp.h"
#include "dsps_wind_hann.h"
#include "dsps_view.h"


// Etiqueta para identificar tus mensajes en el monitor serie
static const char *TAG = "MI_SISTEMA";

#define FFT_SIZE      1024   // Must be a power of 2 (e.g., 512, 1024, 2048)
#define SAMPLE_RATE   16000  // Sample rate in Hz (common for voice/audio analysis)
#define TARGET_FREQ   1000   // Mock signal frequency in Hz (we will look for this)


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
        // Generate pure 1000Hz tone
        input_signal[i] = sinf(2 * M_PI * TARGET_FREQ * time); 
    }

    // 5. Pack real samples into the complex buffer as pairs [Real, Imag, Real, Imag...]
    // Because it's a real-valued signal, we set all Imaginary components to 0
    for (int i = 0; i < FFT_SIZE; i++) {
        fft_buffer[i * 2 + 0] = input_signal[i]; // Real part
        fft_buffer[i * 2 + 1] = 0.0f;            // Imaginary part
    }

    // 6. Execute the Complex FFT 
    dsps_fft2r_fc32(fft_buffer, FFT_SIZE);

    // 7. Reorder bit-reversed outputs back into linear frequency bins
    dsps_bit_rev_fc32(fft_buffer, FFT_SIZE);

    // 8. Split the complex spectrum to extract the real signal components
    dsps_cplx2reC_fc32(fft_buffer, FFT_SIZE);

    // 9. Calculate Magnitudes for the unique frequency bins (up to Nyquist frequency: FFT_SIZE / 2)
    float max_magnitude = 0;
    int peak_bin = 0;

    for (int i = 0; i < FFT_SIZE / 2; i++) {
        float real = fft_buffer[i * 2 + 0];
        float imag = fft_buffer[i * 2 + 1];
        
        // Magnitude = sqrt(real^2 + imag^2)
        magnitude[i] = sqrtf(real * real + imag * imag);

        // Keep track of the dominant frequency peak
        if (magnitude[i] > max_magnitude) {
            max_magnitude = magnitude[i];
            peak_bin = i;
        }
    }

    // 10. Convert the peak bin index to actual Hz frequency
    // Formula: Frequency = Bin_Index * (Sample_Rate / FFT_SIZE)
    float detected_frequency = (float)peak_bin * ((float)SAMPLE_RATE / (float)FFT_SIZE);

    ESP_LOGI(TAG, "===============================================");
    ESP_LOGI(TAG, "Dominant Peak detected at Bin: %d", peak_bin);
    ESP_LOGI(TAG, "Estimated Frequency: %.2f Hz (Expected: %d Hz)", detected_frequency, TARGET_FREQ);
    ESP_LOGI(TAG, "Peak Magnitude Value: %.2f", max_magnitude);
    ESP_LOGI(TAG, "===============================================");

}