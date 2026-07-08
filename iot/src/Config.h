// src/Config.h
#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// ==================== AUDIO CONFIGURATION ====================
#define SAMPLE_RATE         4000        // 4kHz sampling rate for heart sounds
#define BITS_PER_SAMPLE     16          // 16-bit audio
#define NUM_CHANNELS        1           // Mono audio
#define I2S_WS_PIN          GPIO_NUM_25
#define I2S_BCK_PIN         GPIO_NUM_26
#define I2S_DIN_PIN         GPIO_NUM_35   // Microphone input
#define I2S_DOUT_PIN        GPIO_NUM_22   // Audio output (optional)

// ==================== AUDIO BUFFER ====================
#define AUDIO_BUFFER_SIZE   4096         // Audio buffer size in bytes
#define AUDIO_CHUNK_SIZE    512          // Chunk size for transmission
#define MAX_AUDIO_SAMPLES   8192         // Max samples per transmission

// ==================== BLE CONFIGURATION ====================
#define BLE_DEVICE_NAME     "Saka Stethoscope"
#define BLE_SERVICE_UUID    "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define BLE_CHAR_UUID       "beb5483e-36e1-4688-b7f5-ea07361b26a8"

// ==================== WEBSOCKET CONFIGURATION ====================
#define WS_PORT             80
#define WS_SSID             "Saka-Stethoscope"   // AP mode SSID
#define WS_PASSWORD         "saka2026"           // AP mode password

// ==================== NETWORK CONFIGURATION ====================
#define WIFI_TIMEOUT        30                   // WiFi connection timeout in seconds
#define AP_MODE_SSID        "Saka-Stethoscope"
#define AP_MODE_PASSWORD    "saka2026"

// ==================== AUDIO PROCESSING ====================
#define BANDPASS_LOW        20                   // Low frequency cutoff (Hz)
#define BANDPASS_HIGH       400                  // High frequency cutoff (Hz)
#define RMS_THRESHOLD       0.02                 // RMS threshold for detection
#define MIN_SIGNAL_DURATION 0.5                  // Minimum signal duration (seconds)

// ==================== ON-DEVICE SIGNAL QUALITY (SQA) ====================
// First line of defense: cheap running checks on the ESP32 so a garbage/silent/
// clipped/too-short recording is caught at the source, before it is streamed and
// before the backend gate ever sees it. Mirrors backend signal_quality.py.
// NOTE: conservative defaults — re-calibrate with tools/calibrate_sqa.py against
// real field recordings.
#define SQA_FAINT_RMS         0.0032f            // linear RMS ≈ -50 dBFS -> "too faint"
#define SQA_CLIP_LEVEL        0.98f              // |sample| above this counts as clipping
#define SQA_CLIP_RATIO_WARN   0.02f              // >2% clipped samples -> "clipping/jitter"
#define SQA_MIN_DURATION_S    5.0f               // below this -> "too short" (matches backend)
#define SQA_SUBFRAME_MS       20                 // beat-detector analysis window (ms)
#define SQA_BEAT_FACTOR       2.2f               // subframe RMS must exceed baseline * this
#define SQA_BEAT_REFRACT_MS   250                // min gap between beats (=> max 240 BPM)
#define SQA_MIN_BEATS         3                  // fewer than this over the clip -> "no heartbeat"
#define SQA_REPORT_INTERVAL_MS 1000              // how often to broadcast a live quality report

// ==================== LED INDICATORS ====================
#define LED_BUILTIN         2                    // Built-in LED
#define LED_WIFI            4                    // WiFi status LED
#define LED_BLE             5                    // BLE status LED
#define LED_AUDIO           18                   // Audio activity LED

// ==================== BATTERY MONITOR (Scenario 8: Device Health) ====================
// A low battery makes BLE jitter / drop packets, corrupting the audio with
// clicks that can look like murmurs. We report battery so the dashboard can
// grey out the Record button below BATTERY_CRITICAL_PERCENT.
#define BATTERY_ADC_PIN     GPIO_NUM_34          // ADC1 pin on a resistor divider
#define BATTERY_MIN_MV      3300                 // ~empty LiPo (per cell) at divider tap
#define BATTERY_MAX_MV      4200                 // ~full LiPo
#define BATTERY_DIVIDER     2.0                  // 2:1 resistor divider ratio
#define BATTERY_CRITICAL_PERCENT 15              // below this, block recording

// ==================== FEATURE FLAGS ====================
#define ENABLE_BLE          true
#define ENABLE_WEBSOCKET    true
#define ENABLE_WIFI         true
#define ENABLE_SERIAL_DEBUG true

// ==================== DEBUG ====================
#if ENABLE_SERIAL_DEBUG
  #define DEBUG_PRINT(x)      Serial.print(x)
  #define DEBUG_PRINTLN(x)    Serial.println(x)
  #define DEBUG_PRINTF(x, ...) Serial.printf(x, ##__VA_ARGS__)
#else
  #define DEBUG_PRINT(x)
  #define DEBUG_PRINTLN(x)
  #define DEBUG_PRINTF(x, ...)
#endif

#endif // CONFIG_H