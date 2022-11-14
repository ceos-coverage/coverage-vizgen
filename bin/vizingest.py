#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
# http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Check for new files and generate MRFs when found
"""
from pathlib import Path
import os
import sys
import argparse
import yaml
import vizgen

RESOLUTIONS = {
    "16km": [2560, 1280],
    "8km": [5120, 2560],
    "4km": [10240, 5120],
    "2km": [20480, 10240],
    "1km": [40960, 20480],
    "500m": [81920, 40960],
    "250m": [163840, 81920]
}


class LayerConfig():
    """
    LayerConfig is a class containing MRF layer configurations
    """

    def __init__(self, config):

        layer_config = config['config']

        self.layer_prefix = layer_config['layer_prefix']
        self.target_x = RESOLUTIONS[layer_config['tilematrixset']][0]
        self.target_y = RESOLUTIONS[layer_config['tilematrixset']][1]
        self.colormap_prefix = layer_config['colormap_prefix']
        self.vars = layer_config['vars']
        self.working_dir = layer_config['working_dir']
        self.output_dir = layer_config['output_dir']
        self.nodata = layer_config.get('nodata')
        self.extents = layer_config.get('extents', '-180,-90,180,90')
        self.empty_tile = layer_config.get('empty_tile', 'transparent.png')
        self.mrf_suffix = layer_config.get('mrf_suffix', '%Y%j_.mrf')
        self.date_match = layer_config.get('date_match', '%Y%m%d')
        self.dimensions = layer_config.get('dimensions')
        self.s_srs = layer_config.get('s_srs')
        self.t_srs = layer_config.get('t_srs', 'EPSG:4326')
        self.time_bands = layer_config.get('time_bands', [''])
        self.s3_prefix = layer_config.get('s3_prefix')
        self.idx_dir = layer_config.get('idx_dir')

    def __str__(self):
        return str(self.__dict__)


def get_layer_config(layer_config_path):
    with layer_config_path.open() as f:
        config = yaml.safe_load(f.read())
    return {'path': layer_config_path, 'config': config}


def crawl_files(input_dir):
    input_files = []
    print(input_dir)
    if os.path.isdir(input_dir):
        for path in Path(input_dir).rglob('*.nc'):
            if not os.path.isfile(path.name.replace('.nc', '.skip')):
                input_files.append(str(path.absolute()))
        for path in Path(input_dir).rglob('*.nc4'):
            if not os.path.isfile(path.name.replace('.nc4', '.skip')):
                input_files.append(str(path.absolute()))
    else:
        input_files = [input_dir]
    return input_files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This script reads NetCDF files and generates MRF visualizations.')
    parser.add_argument(
        '--config',
        dest='config',
        help='Config to use',
        action='store')
    parser.add_argument(
        '-c',
        '--create_cog',
        help='Generate additional cloud-optimized GeoTIFF',
        action='store_true')
    parser.add_argument(
        '-i',
        '--input_dir',
        dest='input_dir',
        help='Input directory to convert to GIS data',
        action='store')
    parser.add_argument(
        '-l',
        '--limit',
        default='-1',
        dest='limit',
        help='Limit the number of records to process',
        action='store')
    parser.add_argument(
        '-p',
        '--process_existing',
        help='Process existing files',
        action='store_true')

    args = parser.parse_args()

    if not args.config:
        print('--config is required')
        sys.exit(1)

    config = LayerConfig(get_layer_config(Path(args.config)))

    print(f'\nUsing {args.config}\n')
    print(config)

    input_files = crawl_files(args.input_dir)
    limit = int(args.limit)
    counter = 0
    for input_file in input_files:
        if counter < limit or limit == -1:
            print(f'\nProcessing {input_file}\n')
            vizgen.nc2tiff(input_file, config, args.process_existing, limit, args.create_cog)
            counter += 1
