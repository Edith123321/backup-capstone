// src/I2S_Manager.cpp
#include "I2S_Manager.h"
#include <math.h>

I2S_Manager::I2S_Manager() : _isRunning(false) {
    _initFilter();
    
    // Initialize history arrays
    for (int i = 0; i < 5; i++) {
        _x[i] = 0.0f;
        _y[i] = 0.0f;
    }
}

I2S_Manager::~I2S_Manager() {
    end();
}

bool I2S_Manager::begin() {
    // Configure I2S pins
    _pinConfig = {
        .bck_io_num = I2S_BCK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_DOUT_PIN,
        .data_in_num = I2S_DIN_PIN
    };
    
    // Configure I2S settings
    _i2sConfig = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_I2S | I2S_COMM_FORMAT_I2S_MSB),
        .intr_alloc_flags = 0,
        .dma_buf_count = 8,
        .dma_buf_len = 64
    };
    
    // Install and start I2S driver
    esp_err_t err = i2s_driver_install(I2S_NUM_0, &_i2sConfig, 0, NULL);
    if (err != ESP_OK) {
        DEBUG_PRINTF("I2S driver install failed: %d\n", err);
        return false;
    }
    
    err = i2s_set_pin(I2S_NUM_0, &_pinConfig);
    if (err != ESP_OK) {
        DEBUG_PRINTF("I2S pin config failed: %d\n", err);
        i2s_driver_uninstall(I2S_NUM_0);
        return false;
    }
    
    _isRunning = true;
    DEBUG_PRINTLN("I2S initialized successfully");
    return true;
}

int I2S_Manager::readAudio(int16_t* buffer, int bufferSize) {
    if (!_isRunning) return 0;
    
    size_t bytesRead = 0;
    esp_err_t err = i2s_read(I2S_NUM_0, buffer, bufferSize * sizeof(int16_t), &bytesRead, portMAX_DELAY);
    
    if (err != ESP_OK) {
        DEBUG_PRINTF("I2S read error: %d\n", err);
        return 0;
    }
    
    int samplesRead = bytesRead / sizeof(int16_t);
    return samplesRead;
}

int I2S_Manager::readAudioFloat(float* buffer, int bufferSize) {
    if (!_isRunning) return 0;
    
    int16_t* intBuffer = new int16_t[bufferSize];
    int samplesRead = readAudio(intBuffer, bufferSize);
    
    for (int i = 0; i < samplesRead; i++) {
        buffer[i] = (float)intBuffer[i] / 32768.0f;
    }
    
    delete[] intBuffer;
    return samplesRead;
}

void I2S_Manager::end() {
    if (_isRunning) {
        i2s_driver_uninstall(I2S_NUM_0);
        _isRunning = false;
        DEBUG_PRINTLN("I2S stopped");
    }
}

float I2S_Manager::getRMS(int16_t* buffer, int bufferSize) {
    float sum = 0.0f;
    for (int i = 0; i < bufferSize; i++) {
        float sample = (float)buffer[i] / 32768.0f;
        sum += sample * sample;
    }
    return sqrt(sum / bufferSize);
}

void I2S_Manager::_initFilter() {
    // Simple bandpass filter coefficients for 20-400 Hz at 4kHz sample rate
    // Using a simple IIR filter
    _b[0] = 0.0012f; _b[1] = 0.0f;   _b[2] = -0.0024f; _b[3] = 0.0f;   _b[4] = 0.0012f;
    _a[0] = 1.0f;    _a[1] = -3.5801f; _a[2] = 4.8723f;   _a[3] = -2.9961f; _a[4] = 0.7042f;
}

void I2S_Manager::bandpassFilter(float* data, int length) {
    for (int n = 0; n < length; n++) {
        data[n] = _filterSample(data[n]);
    }
}

float I2S_Manager::_filterSample(float input) {
    // Shift input history
    _x[4] = _x[3];
    _x[3] = _x[2];
    _x[2] = _x[1];
    _x[1] = _x[0];
    _x[0] = input;
    
    // Shift output history
    _y[4] = _y[3];
    _y[3] = _y[2];
    _y[2] = _y[1];
    _y[1] = _y[0];
    
    // Apply filter
    _y[0] = _b[0] * _x[0] + _b[1] * _x[1] + _b[2] * _x[2] + _b[3] * _x[3] + _b[4] * _x[4]
            - _a[1] * _y[1] - _a[2] * _y[2] - _a[3] * _y[3] - _a[4] * _y[4];
    
    return _y[0];
}