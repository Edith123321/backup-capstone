// src/Saka_Stethoscope.ino
#include <Arduino.h>
#include <WiFi.h>
#include <WebSocketsServer.h>
#include <ArduinoJson.h>
#include "Config.h"
#include "I2S_Manager.h"
#include "BLE_Handler.h"

// ==================== GLOBAL OBJECTS ====================
I2S_Manager i2sManager;
BLE_Handler bleHandler;
WebSocketsServer webSocket = WebSocketsServer(WS_PORT);

// ==================== GLOBAL VARIABLES ====================
bool isRecording = false;
bool isConnected = false;
unsigned long lastAudioRead = 0;
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
    
    // Setup WiFi (optional - skip if not needed)
    // setupWiFi();
    
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
    DEBUG_PRINT("Starting Access Point mode... ");
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_MODE_SSID, AP_MODE_PASSWORD);
    DEBUG_PRINTF("AP started: %s\n", AP_MODE_SSID);
    digitalWrite(LED_WIFI, HIGH);
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
        DEBUG_PRINTLN("🎙️ Recording started");
        
        String response = "{\"status\":\"recording\",\"sample_rate\":" + String(SAMPLE_RATE) + ",\"bits\":16}";
        webSocket.broadcastTXT(response);
        
    } else if (command == "STOP_RECORDING") {
        isRecording = false;
        DEBUG_PRINTLN("⏹️ Recording stopped");
        
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
String getDeviceStatus() {
    DynamicJsonDocument doc(512);
    doc["device"] = "Saka Stethoscope";
    doc["status"] = isRecording ? "recording" : "idle";
    doc["sample_rate"] = SAMPLE_RATE;
    doc["bits"] = BITS_PER_SAMPLE;
    doc["channels"] = NUM_CHANNELS;
    doc["ble_connected"] = bleHandler.isConnected();
    doc["clients"] = webSocket.connectedClients();
    
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