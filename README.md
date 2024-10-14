# Circuitpython Firmware

Firmware for Luftdaten.at devices in Circuitpython.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)

## Installation

Here is the English translation of your markdown:

## 1 - Download CircuitPython Version

Download link: https://circuitpython.org/board/espressif_esp32s3_devkitc_1_n8r8/

At least CircuitPython 9.1.0 is required. Due to a bug in CircuitPython, only <= 9.1.0 or >= 9.2.0 can currently be used. Download the `.bin` file, where `circuitpython.bin` is the path to the downloaded CircuitPython file.

## 2 - Install CircuitPython

### on Mac
Connect the Mac and ESP32 via USB C. Press the Reset button while also holding down the Boot button.

If not already installed, install esptool.py:

```bash
pip3 install esptool
```

Find the port of the ESP32:

```bash
ls /dev/tty.*
```

The ESP32 should appear as a USB device, e.g., /dev/tty.usbmodem101.

Erase the ESP32 flash memory:

```bash
esptool.py --port /dev/tty.usbmodem101 erase_flash
```

Flash CircuitPython onto the ESP32:

```bash
esptool.py --port /dev/tty.usbmodem101 write_flash -z 0x0 circuitpython.bin
```

### on Windows

Connect Windows and the ESP32 via USB C. Press the Reset button while also holding down the Boot button.

If not already installed, install esptool.py. Open the command prompt (CMD) and install esptool:

```CMD
pip install esptool
```

Find the port of the ESP32.
Open the Device Manager and look under “Ports (COM & LPT)” for your ESP32. There should be an entry like COM3 or COM5.

Erase the ESP32 flash memory:
Replace COM3 with the actual COM port of your ESP32:

```CMD
esptool.py --port COM3 erase_flash
```

Flash CircuitPython onto the ESP32:
Use the correct path to the downloaded CircuitPython file and the corresponding COM port:

```CMD
esptool.py --port COM3 write_flash -z 0x0 circuitpython.bin
```

### on Linux

Connect Linux and the ESP32 via USB C. Press the Reset button while also holding down the Boot button.

If not already installed, install esptool.py. Open a terminal and install esptool:

```bash
pip install esptool
```

Find the port of the ESP32.
Run the following command in the terminal:

```bash
ls /dev/tty*
```

The ESP32 should appear as a device, e.g., /dev/ttyUSB0 or /dev/ttyACM0.

Erase the ESP32 flash memory:
Replace /dev/ttyUSB0 with the actual device name:

```bash
esptool.py --port /dev/ttyUSB0 erase_flash
```

Flash CircuitPython onto the ESP32:
Use the correct path to the downloaded CircuitPython file and the correct device name:

```bash
esptool.py --port /dev/ttyUSB0 write_flash -z 0x0 circuitpython.bin
```

## 3 - Copy Files

Download the latest [Release](https://github.com/luftdaten-at/firmware/releases)  and copy all files from the firmware folder to the ESP32.

## 4 - Start and Configure

Configure the device using the app. You can find it in the Google Play or Apple App Store. [Links here](https://luftdaten.at/mobile-app/)

## Contributing

We use GitHub Flow for our development process. Please open an issue oder write us.

## License

This project is licensed under the AGPL 3.0 License - see the [LICENSE](LICENSE) file for details.