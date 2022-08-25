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
Delete MRF skip files
"""
from pathlib import Path
import os
import sys
import argparse


def delete_files(input_dir):
    input_files = []
    print(input_dir)
    if os.path.isdir(input_dir):
        for path in Path(input_dir).rglob('*.skip'):
            print(f'Removing {path.absolute()}')
            os.remove(path.absolute())
            data_file = str(Path(path).absolute().parent) + '/' + str(Path(path).stem) + '.nc'
            print(f'Removing {data_file}')
            os.remove(data_file)
    else:
        input_files = [input_dir]
        print(f'Removing {input_dir}')
        os.remove(input_dir)
    return input_files


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This script reads NetCDF files and generates MRF visualizations.')
    parser.add_argument(
        '-i',
        '--input_dir',
        dest='input_dir',
        help='Input directory to convert to GIS data',
        action='store')

    args = parser.parse_args()

    if not args.input_dir:
        print('--input_dir is required')
        sys.exit(1)

    deleted_files = delete_files(args.input_dir)
    print('All files deleted')
