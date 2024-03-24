#!/bin/bash

# This script generates MRF data from a config file
cd /mrfgen
# mrfgen, but really GDAL, does not like to overwrite files
# so instead we clean the directories beforehand
rm -rf output/*
rm -rf work/*
rm -rf cache/*
rm -rf log/*

# The pythonpath needs to be set directly for some reason
export PYTHONPATH=/usr/bin

/home/oe2/onearth/src/mrfgen/mrfgen.py -c $1