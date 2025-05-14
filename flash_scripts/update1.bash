#!/bin/bash

# variables
target="/media/nik/CIRCUITPY1/"
settings="/media/nik/CIRCUITPY1/settings.toml"
firmware="../firmware/*"
tmp="1"
tmpSettings="1/settings.toml"

cp $settings $tmp
cp -r $firmware $target
cp $tmpSettings $target

echo "Finished sucessfully ✅"
