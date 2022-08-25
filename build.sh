#!/bin/sh

# Set COVERAGE version and release
source ./version.sh

# Build the coverage/onearth image
docker build \
    --no-cache \
    -f ./docker/Dockerfile \
    -t coverage/vizgen:$COVERAGE_VERSION \
    .