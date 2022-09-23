#!/bin/sh

# Set COVERAGE version and release
source ./version.sh

docker run -it \
    --restart unless-stopped \
    --name coverage-vizgen \
	-v $(pwd)/colormaps/:/vizgen/colormaps/ \
	-v $(pwd)/configs/:/vizgen/configs/ \
	-v $(pwd)/data/:/vizgen/data/ \
	-v $(pwd)/empty_tiles/:/vizgen/empty_tiles/ \
    -v $(pwd)/output/:/vizgen/output/ \
    -v $(pwd)/working/:/vizgen/working/ \
    coverage/vizgen:$VIZGEN_VERSION /bin/bash

    