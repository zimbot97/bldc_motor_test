English | [中文](README_zh.md)

# BLDC Motor Test

Closed-loop FOC velocity control for a 2804 BLDC motor using an ESP32, DRV8313 driver board, and MT6701 magnetic encoder (ABZ mode). Includes a Python UI with a velocity slider for real-time testing.

Built with [SimpleFOC 2.3.3](https://simplefoc.com) and [PlatformIO](https://platformio.org).

---

## Hardware Required

| Component | Details |
|-----------|---------|
| ESP32 Dev Module | Any standard ESP32 dev board |
| DRV8313 motor driver | SimpleFOCMini or equivalent 3-phase driver |
| MT6701 magnetic encoder | Must be configured for ABZ output mode |
| 2804 BLDC motor | 12N14P winding, 7 pole pairs |
| 12V power supply | Powers the motor driver (separate from USB) |

---

## Wiring

### Power

The ESP32 is powered by USB. The motor driver needs a **separate 12V supply** connected to its VM/PVDD pin. Both must share a common GND.

### ESP32 to DRV8313 (Motor Driver)

| ESP32 | DRV8313 | Notes |
|-------|---------|-------|
| GPIO 25 | IN1 | Phase A PWM |
| GPIO 26 | IN2 | Phase B PWM |
| GPIO 27 | IN3 | Phase C PWM |
| GPIO 14 | EN | Driver enable |
| GPIO 4 | nFT | Fault signal (input) |
| 3.3V | VCC | Logic power |
| GND | GND | Common ground |

The nFT pin is open-drain. GPIO 4 has an internal pull-up enabled in firmware — no external resistor needed.

### ESP32 to MT6701 (Encoder)

| ESP32 | MT6701 | Notes |
|-------|--------|-------|
| GPIO 19 | A | Encoder channel A |
| GPIO 18 | B | Encoder channel B |
| GPIO 5 | Z | Index pulse |
| 3.3V | VDD | Sensor power |
| GND | GND | Common ground |

The default PPR (pulses per revolution) is set to **1024** in `src/main.cpp`. Change this if your MT6701 is configured for a different resolution.

---

## Software Setup

**1. Install PlatformIO**

Follow the instructions at [platformio.org](https://platformio.org) for CLI or the VS Code extension.

**2. Install Python dependencies (for the UI)**

```bash
pip install pyserial
```

`tkinter` is included with most Python 3 installations. If it is missing, install it via your system package manager (e.g. `sudo apt install python3-tk` on Ubuntu).

---

## Flash the Firmware

Connect the ESP32 via USB, then run:

```bash
# Compile only
pio run

# Compile and flash
pio run --target upload
```

**Find your serial port:**
- Linux: `/dev/ttyUSB0` or `/dev/ttyUSB1`
- macOS: `/dev/cu.usbserial-XXXX`
- Windows: `COM3`, `COM4`, etc.

Edit `platformio.ini` and set `upload_port` and `monitor_port` to match your device.

---

## First Boot

On every boot or reset, the ESP32 runs an automatic FOC alignment. During this phase the motor will briefly twitch and rotate slowly — this is normal. It typically takes **5 to 10 seconds**.

Watch the serial output. When you see:

```
MOT: PP check: OK!
MOT: Ready.
```

the motor is aligned and ready to receive velocity commands.

To reset at any time, press the **EN** button on the ESP32 board.

---

## Motor UI

Launch the graphical control panel:

```bash
python3 motor_ui.py
```

**Steps:**
1. Set the port field to match your device
2. Click **Connect**
3. Wait for `MOT: Ready.` to appear in the serial log
4. Drag the velocity slider or press a quick-set button

The slider range is **-50 to +50 rad/s**. Positive values spin forward, negative spin in reverse. The region within +/-0.5 rad/s snaps to zero (stop).

---

## Serial Commands

Commands can be typed in the UI manual command box or sent from any serial terminal at **115200 baud**. The motor prefix is `M`.

| Command | Action |
|---------|--------|
| `M5` | Spin at 5 rad/s |
| `M-5` | Spin at -5 rad/s (reverse) |
| `M0` | Stop |
| `MVP0.2` | Set velocity PID P gain to 0.2 |
| `MVI3` | Set velocity PID I gain to 3 |
| `MVD0` | Set velocity PID D gain to 0 |
| `ML4` | Set voltage limit to 4V |
| `MD` | Print current motor status |
| `ME0` | Disable motor |
| `ME1` | Re-enable motor |

---

## Troubleshooting

**Motor does not move after Ready**
- Check that 12V is connected to the driver VM/PVDD pin.
- Try increasing the voltage limit with `ML6` in the serial command box.

**FOC alignment fails or hangs**
- Verify the encoder A, B, Z wires are connected correctly.
- The motor must be free to rotate during alignment — remove any load.

**Upload fails with port error**
- Check that no other program (serial monitor, UI) is holding the port open.
- Click Disconnect in the UI before flashing.

**Encoder reads 0.00 at all times**
- Check that the MT6701 is in ABZ mode, not SPI mode.
- Verify the A and B wires are connected and not swapped.

---

## Notes

- **SimpleFOC 2.3.3 is pinned** — version 2.4.0 and above requires ESP-IDF 5.x, which is incompatible with the current toolchain. Do not change the version in `platformio.ini` without also updating the platform.
- **voltage_limit is set to 4V** — conservative for this motor (Rs = 2.55 ohm, ~1.6A peak). Increase gradually with the `ML` command when tuning.
- **GPIO 35 is not used for the fault pin** — GPIO 34/35/36/39 on ESP32 are input-only and do not support internal pull-ups. The fault pin is on GPIO 4 instead.
