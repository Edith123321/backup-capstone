# SAKA Stethoscope — Wiring Schematic

Text schematic for the ESP32 + INMP441 build. Pin assignments are the source of
truth in [`../src/Config.h`](../src/Config.h). 
## Connection table

### INMP441 I2S MEMS microphone → ESP32
| INMP441 pin | ESP32 pin | Signal |
|-------------|-----------|--------|
| VDD | 3V3 | Power (3.3 V) |
| GND | GND | Ground |
| SD  | GPIO 35 | I2S data in (`I2S_DIN_PIN`) |
| WS / LRCL | GPIO 25 | Word select (`I2S_WS_PIN`) |
| SCK / BCLK | GPIO 26 | Bit clock (`I2S_BCK_PIN`) |
| L/R | GND | Left channel select (mono) |

### Status LEDs (each via a 220 Ω resistor to GND)
| LED | ESP32 pin |
|-----|-----------|
| Power / heartbeat (built-in) | GPIO 2 (`LED_BUILTIN`) |
| Wi-Fi status | GPIO 4 (`LED_WIFI`) |
| BLE status | GPIO 5 (`LED_BLE`) |
| Audio activity | GPIO 18 (`LED_AUDIO`) |

### Power
| Source | Connection |
|--------|-----------|
| 3.7 V LiPo | TP4056 module → ESP32 5V/VIN (or USB) |
| Common ground | All GND rails tied together |

## ASCII diagram

```
             ┌──────────────────────────┐
   3.3V ─────┤ VDD                       │
   GND ──────┤ GND      INMP441          │
 GPIO35 ─────┤ SD (data)  MEMS mic       │
 GPIO25 ─────┤ WS  (LR clk)              │
 GPIO26 ─────┤ SCK (bit clk)             │
   GND ──────┤ L/R (mono = left)         │
             └──────────────────────────┘
                     │  I2S @ 4 kHz / 16-bit mono
                     ▼
             ┌──────────────────────────┐
             │           ESP32          │
             │        (WROOM-32)        │
             │                          │
   GPIO2  ───┤►│ heartbeat LED          │
   GPIO4  ───┤►│ Wi-Fi LED   (220Ω→GND) │
   GPIO5  ───┤►│ BLE LED     (220Ω→GND) │
   GPIO18 ───┤►│ audio LED   (220Ω→GND) │
             │                          │
             │  BLE  ─── stream ──► app │
             │  WiFi ─── WS:80 ───► web │
             └──────────────────────────┘
                     ▲
   3.7V LiPo ── TP4056 ── 5V/VIN
```

## Acoustic path
Chestpiece → sealed 3D-printed chamber (`../cad/A2D_Chamber_Coupler.stl`) →
INMP441 diaphragm. The firmware applies a 20–400 Hz band-pass
(`BANDPASS_LOW`/`BANDPASS_HIGH` in `Config.h`) to isolate valvular murmurs.
