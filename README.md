# COVERAGE Visualization Generation Pipeline

The COVERAGE Visualization Generation Pipeline (coverage-vizgen) is a software package containing a comprehensive set of utility tools for generating tiled map imagery in the Meta Raster Format (MRF) from NetCDF data files. It is packaged as a Docker container that may be configured to automatically produce imagery from a forward data stream of NetCDF files. This software was developed for the CEOS Ocean Variables Enabling Research and Applications for GEO (COVERAGE) initiative.

## Tools

The included tools are:

* **vizingest.py** - Checks for new input files and kicks off vizgen when found
* **vizgen.py** - Reads NetCDF files and generates MRF visualizations based on dataset configuration
* **vizcolormapgen.py** - Generates txt and xml colormaps from common Matplotlib colormaps
* **vizclean.py** - Removes NetCDF files that have already been processed

The following are additional utilities:

* **color_map_gen.py** - Generates txt, xml, sld, and css colormaps from an input csv containing color bins
* [oe_generate_empty_tile.py](https://github.com/nasa-gibs/onearth/blob/main/src/empty_tile/README.md) - Generates an empty (nodata) tile for use by OnEarth

## Quick Start

### Build

* Execute `build.sh` from the root directory to build the coverage-vizgen Docker image. The version number is sourced from the `version.sh` file.

### Run

1. Create a `vizgen` home directory on your local computer, e.g., `/home/vizgen`.
2. The following directories must be created and exist in the `vizgen` home directory:

   * `colormaps/` - Directory containing txt and xml colormaps used for MRF generation
   * `configs/` - Directory containing vizgen YAML configuration cifles
   * `data/` - Location of input NetCDF files
   * `empty_tiles/` - Directory containing empty tiles used for MRF generation
   * `output/` - Location of output MRF files
   * `working/` - Directory used to store working temp files
   * `idx/` - Optional directory for MRF index files that are ready by OnEarth (may be configured as an external directory)

3. Optional `cron.sh` file can be placed in the `vizgen` home directory to configure cron jobs for automated ingestion (see [docker/cron.sh](./docker/cron.sh) for an example).
4. Execute `run.sh` from the `vizgen` home directory (the `docker run` command may be customized as necessary).

### Process

1. Run docker exec to access container: `docker exec -it coverage-vizgen /bin/bash`
2. Generate txt and xml colormaps for the dataset by running the `vizcolormapgen.py` tool: `vizcolormapgen.py -c jet --min 0 --max 20 -o SAMPLE_DATA_var`
3. Generate empty tiles for the dataset by running the `oe_generate_empty_tile` tool: `./oe_generate_empty_tile.py -c SAMPLE_DATA_var.xml -o ../empty_tiles/SAMPLE_DATA_var.png`
4. Run `vizingest.py` on a dataset of NetCDF files to produce MRFs: `vizingest.py --config configs/SAMPLE_CONFIG.yaml -i data/SAMPLE_DATA/`
5. An associated `.skip` file is placed next to input files that have been processed. The `vizclean.py` tool can be run on the input directory to clean up all processed files (note this will delete the NetCDF input files).

## Configuration

coverage-vizgen uses a YAML dataset configuration file to specify settings for producing MRF files from NetCDF input. This configuration file consists of the following parameters:

* `layer_prefix` - The prefix for the layer identifier
* `projection` - The EPSG map projection code (default `EPSG:4326`)
* `tilematrixset` - WMTS tilematrixset (commonly used by OnEarth)
* `colormap_prefix` - Common prefix used by the txt and xml colormaps
* `vars` - List of variables to produce MRF image layers (1 MRF per variable)
* `working_dir` - Directory used to store working temp files
* `output_dir` - Location of output MRF files
* `nodata` - Nodata value used by the NetCDF input dataset
* `extents` - Geospatial bounds of the dataset
* `empty_tile` or `empty_tile_prefix` - Empty tile location used for MRF generation (use `empty_tile_prefix` when there are multiple empty tiles for multiple variables)
* `mrf_suffix` - The suffix or timestring format used by MRF files
* `date_match` - The timestring format found in NetCDF file names
* `dimensions` - Used to specify dimension variable names for non-standard NetCDF files
* `s_srs` - Source SRS projection if data must be reprojected
* `t_srs` - Destination SRS projection if data must be reprojected
* `time_bands` - A list of time steps to process if the input NetCDF file contains multiple time steps
* `s3_prefix` - S3 URI to upload MRFs to (if specified)
* `idx_dir` - OnEarth idx directory to move MRF idx files to (if specified)
* `is360` - Convert dataset from 0-360 bounds to -180 - 180 if true
* `speed_vars` - List of `u` and `v` variables to use for converting to speed and direction

### Example Configurations

```YAML
layer_prefix: "GHRSST-UKMO_L4_SST-GMPE_v3.0"
projection: "EPSG:4326"
tilematrixset: "16km"
colormap_prefix: "/vizgen/colormaps/GHRSST-UKMO_L4_SST-GMPE_v3.0"
vars:
  - "analysed_sst"
working_dir: "/vizgen/working/"
output_dir: "/vizgen/output/EPSG4326/"
extents: "-180,-90,180,90"
empty_tile: "/vizgen/empty_tiles/GHRSST-UKMO_L4_SST-GMPE_v3.0.png"
mrf_suffix: "%Y%j_.mrf"
date_match: "%Y%m%d%H%M%S"
```

```YAML
layer_prefix: "RSS_CCMP_WINDS_V2.1"
projection: "EPSG:4326"
tilematrixset: "16km"
colormap_prefix: "/vizgen/colormaps/RSS_CCMP_WINDS_V2.1"
vars:
  - "uwnd"
  - "vwnd"
speed_vars:
  - "uwnd"
  - "vwnd"
is360: true
nodata: -9999
working_dir: "/vizgen/working/"
output_dir: "/vizgen/output/EPSG4326/"
extents: "0,-78.375, 360, 78.375"
empty_tile_prefix: "/vizgen/empty_tiles/RSS_CCMP_WINDS_V2.1"
mrf_suffix: "-%Y%j%H%M%S.mrf"
date_match: "%Y%m%d"
dimensions:
  - "time"
  - "latitude"
  - "longitude"
```

## Automated Ingest

Modify the `cron.sh` file in the `vizgen` home directory to configure cron jobs for automated ingestion (see [docker/cron.sh](./docker/cron.sh) for an example). Add and modify the following line to `cron.sh` for each dataset that should be automatically ingested:

`/usr/local/bin/vizingest.py --config /vizgen/configs/config.yaml -i /vizgen/data/layername/ >> /vizgen/logs/layername.log 2>&1`

The `crontab` is configured to run daily at midnight local time, but may be modified as necessary.

The following lines may be added to `cron.sh` to ensure file cleanup:

`rm -rf /vizgen/working/*`

`/usr/local/bin/vizclean.py --input_dir /vizgen/data/ >> /vizgen/logs/vizclean.log 2>&1`
