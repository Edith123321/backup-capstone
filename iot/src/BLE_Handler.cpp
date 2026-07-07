// src/BLE_Handler.cpp
#include "BLE_Handler.h"

BLE_Handler::BLE_Handler() : _isConnected(false), _pendingCommand(0), _pServer(nullptr),
                             _pCharacteristic(nullptr), _pService(nullptr) {}

BLE_Handler::~BLE_Handler() {
    end();
}

bool BLE_Handler::begin() {
    BLEDevice::init(BLE_DEVICE_NAME);
    _pServer = BLEDevice::createServer();
    _pServer->setCallbacks(new ServerCallbacks(this));
    
    _pService = _pServer->createService(BLE_SERVICE_UUID);
    
    _pCharacteristic = _pService->createCharacteristic(
        BLE_CHAR_UUID,
        BLECharacteristic::PROPERTY_READ |
        BLECharacteristic::PROPERTY_WRITE |
        BLECharacteristic::PROPERTY_NOTIFY |
        BLECharacteristic::PROPERTY_INDICATE
    );
    
    _pCharacteristic->setCallbacks(new CharacteristicCallbacks(this));
    _pCharacteristic->addDescriptor(new BLE2902());
    
    _pService->start();
    BLEAdvertising* pAdvertising = _pServer->getAdvertising();
    pAdvertising->addServiceUUID(BLE_SERVICE_UUID);
    pAdvertising->start();
    
    DEBUG_PRINTLN("BLE initialized, waiting for connection...");
    return true;
}

bool BLE_Handler::sendAudioData(uint8_t* data, size_t length) {
    if (!_isConnected || !_pCharacteristic) return false;
    
    _pCharacteristic->setValue(data, length);
    _pCharacteristic->notify();
    return true;
}

bool BLE_Handler::sendStatus(const String& status) {
    if (!_isConnected || !_pCharacteristic) return false;
    
    _pCharacteristic->setValue(status.c_str());
    _pCharacteristic->notify();
    return true;
}

void BLE_Handler::end() {
    if (_pServer) {
        // BLEServer has no stopAdvertising/clearServices; stop advertising via
        // the advertising object and let deinit(true) release the stack.
        BLEDevice::getAdvertising()->stop();
        _pServer = nullptr;
        _pCharacteristic = nullptr;
        _pService = nullptr;
    }
    BLEDevice::deinit(true);
    _isConnected = false;
}

// Server Callbacks
void BLE_Handler::ServerCallbacks::onConnect(BLEServer* pServer) {
    _handler->_isConnected = true;
    DEBUG_PRINTLN("BLE client connected");
    pServer->startAdvertising();
}

void BLE_Handler::ServerCallbacks::onDisconnect(BLEServer* pServer) {
    _handler->_isConnected = false;
    DEBUG_PRINTLN("BLE client disconnected");
}

// Characteristic Callbacks
void BLE_Handler::CharacteristicCallbacks::onWrite(BLECharacteristic* pCharacteristic) {
    std::string value = pCharacteristic->getValue();
    DEBUG_PRINTF("BLE write: %s\n", value.c_str());

    // Record the command; the main sketch consumes it in loop() to start/stop
    // the I2S audio streaming (callbacks run in the BLE task, so keep this light).
    if (value == "START" || value == "START_RECORDING") {
        _handler->_pendingCommand = 1;
    } else if (value == "STOP" || value == "STOP_RECORDING") {
        _handler->_pendingCommand = 2;
    }
}

uint8_t BLE_Handler::consumeCommand() {
    uint8_t cmd = _pendingCommand;
    _pendingCommand = 0;
    return cmd;
}

void BLE_Handler::CharacteristicCallbacks::onRead(BLECharacteristic* pCharacteristic) {
    // Send status response
    String status = "{\"status\":\"ready\",\"sample_rate\":4000,\"bits\":16}";
    pCharacteristic->setValue(status.c_str());
}