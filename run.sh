#!/bin/sh

# Set COVERAGE version and release
source ./version.sh

docker run -d \
    --restart unless-stopped \
    --name coverage-vizgen \
	-v $(pwd)/colormaps/:/vizgen/colormaps/ \
	-v $(pwd)/configs/:/vizgen/configs/ \
	-v $(pwd)/data/:/vizgen/data/ \
	-v $(pwd)/empty_tiles/:/vizgen/empty_tiles/ \
    -v $(pwd)/output/:/vizgen/output/ \
    -v $(pwd)/working/:/vizgen/working/ \
    -v $(pwd)/idx/:/granules/idx/ \
    -v $(pwd)/cron.sh:/vizgen/cron.sh \
    coverage/vizgen:$VIZGEN_VERSION /bin/bash

    