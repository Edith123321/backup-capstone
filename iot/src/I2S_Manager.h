// src/I2S_Manager.h
#ifndef I2S_MANAGER_H
#define I2S_MANAGER_H

#include <Arduino.h>
#include <driver/i2s.h>
#include "Config.h"

class I2S_Manager {
public:
    I2S_Manager();
    ~I2S_Manager();

    // Initialize I2S for audio input
    bool begin();
    
    // Read audio data from microphone
    int readAudio(int16_t* buffer, int bufferSize);
    
    // Read audio data and convert to float (normalized)
    int readAudioFloat(float* buffer, int bufferSize);
    
    // Stop I2S and clean up
    void end();
    
    // Check if I2S is running
    bool isRunning() const { return _isRunning; }
    
    // Get sample rate
    int getSampleRate() const { return SAMPLE_RATE; }
    
    // Get RMS (Root Mean Square) of current audio
    float getRMS(int16_t* buffer, int bufferSize);
    
    // Apply bandpass filter (20-400 Hz)
    void bandpassFilter(float* data, int length);
    
private:
    bool _isRunning;
    i2s_pin_config_t _pinConfig;
    i2s_config_t _i2sConfig;
    
    // IIR filter coefficients for bandpass
    float _b[5];  // Numerator coefficients
    float _a[5];  // Denominator coefficients
    float _x[5];  // Input history
    float _y[5];  // Output history
    
    void _initFilter();
    float _filterSample(float input);
};

#endif // I2S_MANAGER_H