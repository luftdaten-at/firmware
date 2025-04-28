#!/bin/bash
# RUN AS SUPER USER

# variables
circuitpython="circuitpython/adafruit-circuitpython-espressif_esp32s3_devkitc_1_n8r8-en_US-9.2.4.bin"
firmware="../firmware/*" # must no be changed
settings="settings.toml" # change if necessary
port="/dev/ttyACM2" # change depending on operating system
target="/media/nik/CIRCUITPY2/" # change depending on operating system


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

echo "Finished sucessfully ✅"