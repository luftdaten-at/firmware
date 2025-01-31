#!/bin/bash

# variables
port="/dev/ttyACM0"
circuitpython="Downloads/adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-en_US-9.2.1.bin"
firmware="/home/nik/Documents/firmware/firmware/*"
target="/media/nik/CIRCUITPY/"
settings="/home/nik/Documents/firmware/flash_scripts/settings.toml"


esptool.py --port $port erase_flash
esptool.py --port $port write_flash -z 0x0 $circuitpython

# reset device and wait for reconnection
sleep 15

cp -r $firmware $target
cp $settings $target
