# mrfgen-standalone

This repository contains a script that automates the building and running of mrfgen for creating
MRFs from new data sources. It also measures the performance of MRF generation times.

Mrfgen is a tool contained with the GIBS onearth codebase: <https://github.com/nasa-gibs/onearth/tree/main/src/mrfgen>

This script will clone the onearth repository on github.com (not the version on git.earthdata.nasa.gov) to a local directory and build the onearth-tools container to allow you to run mrfgen in a single shot manner without needing to spin up a dev sandbox environment with an ingest service.


## Building and Running

1.  Clone mrfgen-standalone and create a virtual environment:
    ```sh
    git clone https://git.earthdata.nasa.gov/scm/vislabs/mrfgen-standalone.git
    cd mrfgen-standalone
    python3 -m venv mrfgen_venv
    source mrfgen_venv/bin/activate
    ```

2.  Install dependencies:
    ```sh
    python3 -m pip install .
    ```

3.  Build the onearth-tools container:
    ```
    build-mrfgen [-w <workdir>] [--onearth-path <path/to/onearth>] [--nocache]
    ```
    See the arguments section below for more information on arguments, or use `-h` at the command line. None of these arguments are required, so just running `build-mrfgen` is sufficient.

4.  Run your mrfgen for your data set:
    ```
    run-mrfgen <configdir> [--omi | --geos-cf | --hls] [--zoom-level <Z>] [--image-tag <tag>] [--no-download] [--serial]
    ```
    See the arguments section below for more information on arguments, or use `-h` at the command line. The first two arguments, specifying the config directory and the data type, are required. All others are optional.


## Command Line Arguments

### build-mrfgen

- `-w/--workdir`: directory to use for generating mrfs. The default directory will be the current working directory if this argument is not specified. This directory will be populated with a number of subdirectories if they do not already exist: `archive`, `cache`, `colormap`, `config`, `data`, `empty`, `log`, `output`, `work`
- `--onearth-path`: Specify the path to an existing onearth installation (including or excluding the "onearth" directory itself at the end of the path doesn't matter), or the desired install location. The default directory will be the current working directory if this argument is not specified. Onearth will be cloned into this directory if it does not already exist there. 
- `--nocache`: Pass the `--nocache` option to the docker build process for `onearth-tools`. Using `nocache` is important for running a clean build but will take a long time!

### run-mrfgen

- `configdir`: Required path to the config files which will serve as the inputs to MRFgen. Generally this is the `config/` directory inside your MRFgen working directory. See `workdir` from build-mrfgen.
- `--omi | --geos-cf | --hls`: A required tag to specify which type of data is being processed. This will cause the script to use the proper API for downloading your specific data type.
- `--zoom-level`: Zoom level or "pyramid level" of downloaded data tiles. Max value is 8. Higher values take exponentially longer to download and process.
- `--image-tag`: Optional keyword to manually specify the docker image to use for processing this data. The script will attempt to detect the previously built image from build-mrfgen, but it may get confused. Use the `docker images | grep mrfgen` command on the command line to find available choices in your environment. For example, you could say "mrfgen:2.7.9"
- `--no-download`: If you already downloaded the data tiles for your MRFs, and just want to run MRFgen, set this flag. The data downloading step will be bypassed.
- `--serial`: The script will download data tiles in parallel by default, but this can cause a rate-limiting error, i.e. "Max retries exceeded", on some APIs. Parallel download is significantly faster however. Usually the second call in parallel mode will succeed. 