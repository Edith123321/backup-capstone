# Saka Stethoscope - IoT Heart Sound Monitor

[![PlatformIO](https://img.shields.io/badge/PlatformIO-ESP32-blue.svg)](https://platformio.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

##  Overview

Saka Stethoscope is an IoT-enabled digital stethoscope designed for heart sound monitoring and RHD (Rheumatic Heart Disease) screening. It captures heart sounds, processes them with a 20-400 Hz bandpass filter, and streams the data via BLE and WebSocket for real-time analysis.

##  Features

- **20-400 Hz Bandpass Filter** - Optimized for heart sound frequencies
- **Real-time Audio Processing** - 4kHz sampling rate with I2S
- **Dual Connectivity** - BLE and WebSocket (WiFi) streaming
- **WebSocket Server** - Stream audio to web clients in real-time
- **BLE Audio Streaming** - Connect to mobile apps
- **LED Status Indicators** - Power, WiFi, BLE, Audio activity
- **ESP32-based** - Low power, compact design
- **JSON Commands** - Control via WebSocket API

##  Hardware Components

| Component | Specification |
|-----------|---------------|
| **Microcontroller** | ESP32 Dev Board |
| **Microphone** | INMP441 I2S MEMS (heart-sound optimized) |
| **I2S Audio** | 4kHz sample rate, 16-bit mono |
| **Power** | 3.7V LiPo or USB |
| **Connectivity** | WiFi (2.4GHz), BLE 4.2 |
| **LEDs** | 4x Status LEDs |
| **Enclosure** | 3D Printed (PLA) |

##  Project Structure


##  Wiring Diagram

| ESP32 Pin | Component |
|-----------|-----------|
| GPIO 25 | I2S WS (Word Select) |
| GPIO 26 | I2S BCK (Bit Clock) |
| GPIO 35 | I2S DIN (Data In - Microphone) |
| GPIO 22 | I2S DOUT (Data Out - Audio Out) |
| GPIO 2 | Built-in LED |
| GPIO 4 | WiFi Status LED |
| GPIO 5 | BLE Status LED |
| GPIO 18 | Audio Activity LED |
| 3.3V | Power |
| GND | Ground |

##  Getting Started

### Prerequisites

1. **PlatformIO IDE** (VS Code extension) or PlatformIO CLI
2. **ESP32 Dev Board**
3. **USB Cable** for programming

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/capstone.git
cd capstone/iot