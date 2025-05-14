#!/bin/bash

# variables
target="/media/nik/CIRCUITPY2/"
settings="/media/nik/CIRCUITPY2/settings.toml"
firmware="../firmware/*"
tmp="2"
tmpSettings="2/settings.toml"

cp $settings $tmp
cp -r $firmware $target
cp $tmpSettings $target

echo "Finished sucessfully ✅"
