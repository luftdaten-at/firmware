#!/bin/bash

# variables
target="/media/nik/CIRCUITPY/"
settings="/media/nik/CIRCUITPY/settings.toml"
firmware="../firmware/*"
tmp="0"
tmpSettings="0/settings.toml"

cp $settings $tmp
cp -r $firmware $target
cp $tmpSettings $target

echo "Finished sucessfully ✅"
