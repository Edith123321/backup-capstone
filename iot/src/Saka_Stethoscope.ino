// src/Saka_Stethoscope.ino
#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include "Config.h"
#include "I2S_Manager.h"
#include "BLE_Handler.h"
#include "SignalQuality.h"

// ==================== GLOBAL OBJECTS ====================
I2S_Manager i2sManager;
BLE_Handler bleHandler;
WebSocketsServer webSocket = WebSocketsServer(WS_PORT);
SignalQuality sqaMonitor;   // on-device signal quality (see SignalQuality.h)

// ==================== GLOBAL VARIABLES ====================
bool isRecording = false;
bool isConnected = false;
unsigned long lastAudioRead = 0;
unsigned long lastQualityReport = 0;   // last on-device SQA broadcast (ms)
const unsigned long AUDIO_READ_INTERVAL = 50; // ms

// Audio buffer
int16_t audioBuffer[AUDIO_BUFFER_SIZE];
float audioFloatBuffer[AUDIO_BUFFER_SIZE];

// ==================== FUNCTION PROTOTYPES ====================
void setupWiFi();
void setupWebSocket();
void setupLEDs();
void updateLEDs();
void processAudio();
void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length);
void handleCommand(const String& command, const String& params);
void sendAudioToClients(int16_t* data, size_t length);
String getDeviceStatus();

// ==================== SETUP ====================
void setup() {
    Serial.begin(115200);
    delay(1000);
    
    DEBUG_PRINTLN("\n======================================");
    DEBUG_PRINTLN("🫀 SAKA STETHOSCOPE - Heart Sound Monitor");
    DEBUG_PRINTLN("======================================\n");
    
    // Initialize LEDs
    setupLEDs();
    
    // Initialize I2S for microphone
    DEBUG_PRINT("Initializing I2S... ");
    if (i2sManager.begin()) {
        DEBUG_PRINTLN("✅ SUCCESS");
        digitalWrite(LED_AUDIO, HIGH);
    } else {
        DEBUG_PRINTLN("❌ FAILED");
    }
    
    // Setup WiFi (station mode) — prints the device IP over serial on boot.
    setupWiFi();

    // Setup WebSocket
    setupWebSocket();
    
    // Initialize BLE
    DEBUG_PRINT("Initializing BLE... ");
    if (bleHandler.begin()) {
        DEBUG_PRINTLN("✅ SUCCESS");
    } else {
        DEBUG_PRINTLN("❌ FAILED");
    }
    
    DEBUG_PRINTLN("\n======================================");
    DEBUG_PRINTLN("✅ Device ready!");
    DEBUG_PRINTF("BLE Name: %s\n", BLE_DEVICE_NAME);
    DEBUG_PRINTLN("======================================\n");
}

// ==================== LOOP ====================
void loop() {
    // Handle WebSocket clients
    webSocket.loop();

    // Apply any command received over BLE (START/STOP streaming).
    uint8_t bleCmd = bleHandler.consumeCommand();
    if (bleCmd == 1) {
        isRecording = true;
        lastAudioRead = millis();
        sqaMonitor.reset();                 // start fresh quality assessment
        lastQualityReport = millis();
        DEBUG_PRINTLN("🎙️ BLE: recording started");
    } else if (bleCmd == 2) {
        isRecording = false;
        String sqaFinal = sqaMonitor.toJson(true);         // final quality summary
        webSocket.broadcastTXT(sqaFinal);
        DEBUG_PRINTLN("⏹️ BLE: recording stopped");
    }

    // Process audio if recording
    if (isRecording) {
        processAudio();
    }
    
    // Update LEDs
    updateLEDs();
    
    // Small delay to prevent watchdog issues
    delay(10);
}

// ==================== WIFI SETUP ====================
void setupWiFi() {
    // Station mode: join an existing router so the device and the dashboard
    // laptop share a LAN (and the laptop keeps internet). Credentials are in
    // Config.h (WIFI_STA_SSID / WIFI_STA_PASSWORD).
    DEBUG_PRINTF("Connecting to WiFi \"%s\" ", WIFI_STA_SSID);
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_STA_SSID, WIFI_STA_PASSWORD);

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED &&
           millis() - start < (unsigned long)WIFI_TIMEOUT * 1000) {
        delay(500);
        DEBUG_PRINT(".");
    }

    if (WiFi.status() == WL_CONNECTED) {
        digitalWrite(LED_WIFI, HIGH);
        String ip = WiFi.localIP().toString();
        DEBUG_PRINTLN(" ✅");
        DEBUG_PRINTF("📡 Device IP: %s\n", ip.c_str());
        DEBUG_PRINTF("   WebSocket:  ws://%s/audio\n", ip.c_str());
        DEBUG_PRINTF("   Register this IP (%s) in the dashboard.\n", ip.c_str());
    } else {
        // Fallback so the device is never unreachable: bring up its own hotspot.
        DEBUG_PRINTLN(" ❌");
        DEBUG_PRINTLN("⚠️ WiFi connect failed — starting AP hotspot fallback");
        WiFi.mode(WIFI_AP);
        WiFi.softAP(AP_MODE_SSID, AP_MODE_PASSWORD);
        digitalWrite(LED_WIFI, HIGH);
        String ip = WiFi.softAPIP().toString();
        DEBUG_PRINTF("📡 AP \"%s\" (pw %s) IP: %s\n", AP_MODE_SSID, AP_MODE_PASSWORD, ip.c_str());
        DEBUG_PRINTF("   Join that WiFi, then WebSocket: ws://%s/audio\n", ip.c_str());
    }
}

// ==================== WEBSOCKET SETUP ====================
void setupWebSocket() {
    webSocket.begin();
    webSocket.onEvent(handleWebSocketEvent);
    DEBUG_PRINTLN("WebSocket server started");
}

// ==================== WEBSOCKET EVENT HANDLER ====================
void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t* payload, size_t length) {
    switch (type) {
        case WStype_DISCONNECTED:
            DEBUG_PRINTF("[%u] WebSocket disconnected\n", num);
            break;
            
        case WStype_CONNECTED:
            DEBUG_PRINTF("[%u] WebSocket connected\n", num);
            webSocket.sendTXT(num, "{\"status\":\"connected\",\"device\":\"Saka Stethoscope\"}");
            break;
            
        case WStype_TEXT: {
            // Parse JSON command (braces scope the local vars — required in a switch)
            DynamicJsonDocument doc(512);
            DeserializationError error = deserializeJson(doc, (const char*)payload);

            if (!error) {
                String command = doc["command"];
                String params = doc["params"];
                handleCommand(command, params);
            } else {
                DEBUG_PRINTF("JSON parse error: %s\n", error.c_str());
            }
            break;
        }
            
        case WStype_BIN:
            // Binary data (audio stream)
            break;
            
        default:
            break;
    }
}

// ==================== COMMAND HANDLER ====================
void handleCommand(const String& command, const String& params) {
    DEBUG_PRINTF("Command: %s, Params: %s\n", command.c_str(), params.c_str());
    
    if (command == "START_RECORDING") {
        isRecording = true;
        lastAudioRead = millis();
        sqaMonitor.reset();                 // start fresh quality assessment
        lastQualityReport = millis();
        DEBUG_PRINTLN("🎙️ Recording started");

        String response = "{\"status\":\"recording\",\"sample_rate\":" + String(SAMPLE_RATE) + ",\"bits\":16}";
        webSocket.broadcastTXT(response);

    } else if (command == "STOP_RECORDING") {
        isRecording = false;
        DEBUG_PRINTLN("⏹️ Recording stopped");

        // Broadcast the final on-device quality summary (enforces min-duration).
        String sqaFinal = sqaMonitor.toJson(true);
        webSocket.broadcastTXT(sqaFinal);

        String response = "{\"status\":\"idle\",\"message\":\"Recording stopped\"}";
        webSocket.broadcastTXT(response);
        
    } else if (command == "GET_STATUS") {
        String status = getDeviceStatus();
        webSocket.broadcastTXT(status);
        
    } else {
        DEBUG_PRINTF("Unknown command: %s\n", command.c_str());
    }
}

// ==================== AUDIO PROCESSING ====================
void processAudio() {
    // Read audio from I2S
    int samplesRead = i2sManager.readAudio(audioBuffer, AUDIO_BUFFER_SIZE);
    
    if (samplesRead > 0) {
        // Calculate RMS for activity detection
        float rms = i2sManager.getRMS(audioBuffer, samplesRead);

        // On-device Signal Quality Assessment — feed every captured chunk and
        // broadcast a live quality report roughly once a second so the nurse
        // gets instant "too faint / no heartbeat / clipping" feedback.
        sqaMonitor.feed(audioBuffer, samplesRead, SAMPLE_RATE);
        if (millis() - lastQualityReport >= SQA_REPORT_INTERVAL_MS) {
            String sqaLive = sqaMonitor.toJson(false);
            webSocket.broadcastTXT(sqaLive);
            lastQualityReport = millis();
        }

        // If audio is detected, send to clients
        if (rms > RMS_THRESHOLD) {
            // Send audio data to WebSocket clients
            sendAudioToClients(audioBuffer, samplesRead);
            
            // Also send via BLE if connected
            if (bleHandler.isConnected()) {
                bleHandler.sendAudioData((uint8_t*)audioBuffer, samplesRead * sizeof(int16_t));
            }
            
            // Blink LED to indicate audio activity
            digitalWrite(LED_AUDIO, !digitalRead(LED_AUDIO));
        }
    }
}

// ==================== SEND AUDIO TO CLIENTS ====================
void sendAudioToClients(int16_t* data, size_t length) {
    // Send as binary data over WebSocket
    webSocket.broadcastBIN((uint8_t*)data, length * sizeof(int16_t));
}

// ==================== DEVICE STATUS ====================
// ==================== BATTERY MONITOR (Scenario 8) ====================
// Read the battery level as a 0-100 percentage from the ADC divider. Averaged
// over a few samples to smooth ADC noise. Returns 100 if no divider is wired.
int readBatteryPercent() {
    const int samples = 8;
    uint32_t acc = 0;
    for (int i = 0; i < samples; i++) {
        acc += analogReadMilliVolts(BATTERY_ADC_PIN);
    }
    uint32_t mv = (acc / samples) * BATTERY_DIVIDER;   // undo the divider
    if (mv <= BATTERY_MIN_MV) return 0;
    if (mv >= BATTERY_MAX_MV) return 100;
    return (int)(100.0 * (mv - BATTERY_MIN_MV) / (BATTERY_MAX_MV - BATTERY_MIN_MV));
}

String getDeviceStatus() {
    DynamicJsonDocument doc(512);
    doc["device"] = "Saka Stethoscope";
    doc["status"] = isRecording ? "recording" : "idle";
    doc["sample_rate"] = SAMPLE_RATE;
    doc["bits"] = BITS_PER_SAMPLE;
    doc["channels"] = NUM_CHANNELS;
    doc["ble_connected"] = bleHandler.isConnected();
    doc["clients"] = webSocket.connectedClients();

    // Scenario 8 — Device Health telemetry so the dashboard can show a
    // battery/signal status bar and block recording on a dying battery.
    int battery = readBatteryPercent();
    doc["battery_percent"] = battery;
    doc["battery_low"] = battery < BATTERY_CRITICAL_PERCENT;
    doc["rssi"] = WiFi.RSSI();   // signal strength (dBm)

    String output;
    serializeJson(doc, output);
    return output;
}

// ==================== LED SETUP ====================
void setupLEDs() {
    pinMode(LED_BUILTIN, OUTPUT);
    pinMode(LED_WIFI, OUTPUT);
    pinMode(LED_BLE, OUTPUT);
    pinMode(LED_AUDIO, OUTPUT);
    
    // Initial blink test
    for (int i = 0; i < 3; i++) {
        digitalWrite(LED_BUILTIN, HIGH);
        digitalWrite(LED_WIFI, HIGH);
        digitalWrite(LED_BLE, HIGH);
        digitalWrite(LED_AUDIO, HIGH);
        delay(100);
        digitalWrite(LED_BUILTIN, LOW);
        digitalWrite(LED_WIFI, LOW);
        digitalWrite(LED_BLE, LOW);
        digitalWrite(LED_AUDIO, LOW);
        delay(100);
    }
    
    // Set initial states
    digitalWrite(LED_BUILTIN, HIGH); // Device is on
    digitalWrite(LED_WIFI, LOW);
    digitalWrite(LED_BLE, LOW);
    digitalWrite(LED_AUDIO, LOW);
}

// ==================== UPDATE LEDS ====================
void updateLEDs() {
    static unsigned long lastBlink = 0;
    const unsigned long BLINK_INTERVAL = 500;
    
    if (millis() - lastBlink > BLINK_INTERVAL) {
        lastBlink = millis();
        
        // Heartbeat LED (built-in)
        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
        
        // BLE status
        if (bleHandler.isConnected()) {
            digitalWrite(LED_BLE, HIGH);
        } else {
            digitalWrite(LED_BLE, !digitalRead(LED_BLE));
        }
    }
}