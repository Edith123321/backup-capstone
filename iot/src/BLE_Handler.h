// src/BLE_Handler.h
#ifndef BLE_HANDLER_H
#define BLE_HANDLER_H

#include <Arduino.h>
#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEServer.h>
#include <BLE2902.h>   // required for the notify descriptor used in BLE_Handler.cpp
#include "Config.h"

class BLE_Handler {
public:
    BLE_Handler();
    ~BLE_Handler();
    
    // Initialize BLE
    bool begin();
    
    // Send audio data via BLE
    bool sendAudioData(uint8_t* data, size_t length);
    
    // Send status update
    bool sendStatus(const String& status);
    
    // Check if BLE is connected
    bool isConnected() const { return _isConnected; }

    // Consume a pending command written by the client over BLE.
    // Returns 0 = none, 1 = START (begin streaming), 2 = STOP.
    uint8_t consumeCommand();

    // Stop BLE
    void end();

private:
    bool _isConnected;
    volatile uint8_t _pendingCommand;  // set from the BLE callback task
    BLEServer* _pServer;
    BLECharacteristic* _pCharacteristic;
    BLEService* _pService;

    class ServerCallbacks : public BLEServerCallbacks {
        BLE_Handler* _handler;
    public:
        ServerCallbacks(BLE_Handler* handler) : _handler(handler) {}
        void onConnect(BLEServer* pServer) override;
        void onDisconnect(BLEServer* pServer) override;
    };

    class CharacteristicCallbacks : public BLECharacteristicCallbacks {
        BLE_Handler* _handler;
    public:
        CharacteristicCallbacks(BLE_Handler* handler) : _handler(handler) {}
        void onWrite(BLECharacteristic* pCharacteristic) override;
        void onRead(BLECharacteristic* pCharacteristic) override;
    };
};

#endif // BLE_HANDLER_H