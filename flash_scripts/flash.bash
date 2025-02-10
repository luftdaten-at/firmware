#!/bin/bash

# variables
port="/dev/ttyACM0"
circuitpython="/home/nik/Downloads/adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-en_US-9.2.4"
firmware="/home/nik/Documents/firmware/firmware/*"
target="/media/nik/CIRCUITPY/"
settings="/home/nik/Documents/firmware/flash_scripts/settings.toml"


esptool.py --port $port erase_flash
esptool.py --port $port write_flash -z 0x0 $circuitpython

# reset device and wait for reconnection
echo "Press reset key and wait for the filesystem to connect"
echo "After reconnection press the Enter key to continue"

read

echo "Start to copy firmware"
# copy firmware
cp -r $firmware $target

echo "Copy settings.toml"
# copy settings.toml
cp $settings $target
