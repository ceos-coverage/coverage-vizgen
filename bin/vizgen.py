#!/usr/bin/env python3

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
This script reads NetCDF files and generates MRF visualizations.
"""
import os
import subprocess
import sys
import argparse
import re
import shutil
import string
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path
from datetime import datetime
from datetime import timedelta
from urllib.parse import urlparse
from vizingest import LayerConfig, get_layer_config

MRF_CONFIG_TEMPLATE = string.Template("""
<mrfgen_configuration>
 <date_of_data>${date_of_data}</date_of_data>
 <time_of_data>${time_of_data}</time_of_data>
 <parameter_name>${name}</parameter_name>
 <input_files>
  <file>${input_file}</file>
 </input_files>
 <output_dir>${output_dir}</output_dir>
 <working_dir>${working_dir}</working_dir>
 <logfile_dir>${logfile_dir}</logfile_dir>
 <mrf_blocksize>512</mrf_blocksize>
 <mrf_compression_type>PPNG</mrf_compression_type>
 <overview_resampling>nearest</overview_resampling>
 <resize_resampling>near</resize_resampling>
 <mrf_nocopy>false</mrf_nocopy>
 <target_x>${target_x}</target_x>
 <extents>${extents}</extents>
 <target_extents>-180,-90,180,90</target_extents>
 <mrf_name>{$parameter_name}${mrf_suffix}</mrf_name>
 <colormap>${colormap}</colormap>
 <mrf_empty_tile_filename>${empty_tile}</mrf_empty_tile_filename>
 ${reproject}
</mrfgen_configuration>
""")


def nc2tiff(input_file, config, process_existing=False, limit=-1, create_cog=False):
    output_files = []
    counter = 0
    input_files = []
    if os.path.isdir(input_file):
        for path in Path(input_file).rglob('*.nc'):
            if not os.path.isfile(path.name.replace('.nc', '.skip')):
                input_files.append(str(path.absolute()))
    else:
        input_files = [input_file]
    if not os.path.exists(config.working_dir):
        os.makedirs(config.working_dir)
    for input_file in input_files:
        skip_file = str(Path(input_file).absolute().parent) + '/' + str(Path(input_file).stem) + '.skip'
        # skip file if it has already been processed
        if (os.path.isfile(skip_file) and process_existing is False) or (counter > limit and limit is not -1):
            print(f'Skipping {input_file}')
            continue

        # check if we need to fix dimensions
        temp_nc = None
        if config.dimensions:
            dimensions = ','.join(config.dimensions)
            temp_nc = str(Path(config.working_dir).absolute()) \
                + '/' + str(Path(input_file).stem) + '_temp.nc'
            print('Created temp NetCDF ' + temp_nc)
            ncpdq = ['ncpdq', '-O', '-a', dimensions, input_file, temp_nc]
            print(ncpdq)
            process = subprocess.Popen(ncpdq, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            for output in process.stdout:
                print(output.decode())
            for error in process.stderr:
                print(error.decode())
            print('Created temp NetCDF ' + temp_nc)
            input_file = temp_nc

        # check if we need to reproject
        if config.s_srs:
            projection = config.s_srs
            config.reproject = '<target_epsg>4326</target_epsg>' + \
                               '<source_epsg>' + projection.split(':')[1] + '</source_epsg>'
        else:
            projection = config.t_srs
            config.reproject = ''

        counter += 1
        for band, time in enumerate(config.time_bands):
            if time != '':
                bandstring = '_b' + str(band+1)
            else:
                bandstring = ''
            for var in config.vars:
                output_file = str(Path(config.working_dir).absolute()) \
                            + '/' + str(Path(input_file).stem) + '_' + var + bandstring + '.tiff'
                print('Creating GeoTIFF file ' + output_file)
                if not os.path.isfile(output_file):
                    extents = config.extents.split(',')
                    gdal_translate = ['gdal_translate', '-of', 'GTiff', '-a_srs', projection, '-a_ullr',
                                      extents[0], extents[3], extents[2], extents[1]]
                    if hasattr(config, 'nodata'):
                        gdal_translate.append('-a_nodata')
                        gdal_translate.append(str(config.nodata))
                    if time != '':
                        gdal_translate.append('-b')
                        gdal_translate.append(str(band+1))
                    gdal_translate.append('NETCDF:'+input_file+':'+var)
                    gdal_translate.append(output_file)
                    print(gdal_translate)
                    process = subprocess.Popen(gdal_translate, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.wait()
                    for output in process.stdout:
                        print(output.decode())
                    for error in process.stderr:
                        print(error.decode())
                    print('Created GeoTIFF ' + output_file)

                if create_cog:
                    cog_file = str(Path(config.working_dir).absolute()) \
                            + '/' + str(Path(input_file).stem) + '_' + var + '.cog.tiff'
                    print('Creating Cloud-Optimized GeoTIFF file ' + cog_file)
                    gdal_translate = ['gdal_translate', '-of', 'COG', '-co', 'COMPRESS=LZW', output_file, cog_file]
                    print(gdal_translate)
                    process = subprocess.Popen(gdal_translate, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.wait()
                    for output in process.stdout:
                        print(output.decode())
                    for error in process.stderr:
                        print(error.decode())
                    print('Created GeoTIFF ' + cog_file)

                if config.empty_tile_prefix is not None:
                    empty_tile = config.empty_tile_prefix + '_' + var + '.png'
                else:
                    empty_tile = config.empty_tile

                if config.colormap_prefix is not None:
                    print('Coloring ' + output_file)
                    colormap = f'{config.colormap_prefix}_{var}.txt'
                    colormap_xml = f'{config.colormap_prefix}_{var}.xml'
                    output_file_colored = str(Path(config.working_dir).absolute()) \
                        + '/' + str(Path(input_file).stem) + '_' + var + bandstring + '_.tiff'
                    if process_existing or not os.path.isfile(output_file_colored):
                        print(f'Using colormap:{colormap}')
                        gdaldem_command_list = ['gdaldem', 'color-relief', '-alpha', '-nearest_color_entry',
                                                output_file, colormap, output_file_colored]
                        process = subprocess.Popen(gdaldem_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        process.wait()
                        for output in process.stdout:
                            print(output.decode())
                        for error in process.stderr:
                            print(error.decode())
                        if process.returncode == 0:  # delete if there are no errors
                            print('Created GeoTIFF ' + output_file_colored)
                            try:
                                print('Deleting file ' + output_file)
                                os.remove(output_file)
                            except FileNotFoundError as ex:
                                print(ex)
                    output_files.append(output_file_colored)
                    create_mrf([output_file_colored], config, config.layer_prefix + '_' + var, colormap_xml, empty_tile)
                else:
                    output_files.append(output_file)
                    create_mrf([output_file], config, config.layer_prefix + '_' + var, colormap_xml, empty_tile)
        if temp_nc:
            try:
                print('Deleting file ' + temp_nc)
                os.remove(temp_nc)
            except FileNotFoundError as ex:
                print(ex)
        # create skip file when done
        with open(skip_file, 'w'):
            pass

    return output_files


def create_mrf(input_files, config, layer_name, colormap, empty_tile):
    if not os.path.exists(config.working_dir + '/' + 'configs/'):
        os.makedirs(config.working_dir + '/' + 'configs/')
    if not os.path.exists(config.working_dir + '/' + 'logs/'):
        os.makedirs(config.working_dir + '/' + 'logs/')
    for input_file in input_files:
        print(input_file)
        filename = str(Path(input_file).stem)
        mrf_config = config.working_dir + '/' + 'configs/' + filename + '.xml'
        print('Generating MRF config ' + mrf_config)
        with open(mrf_config, 'w') as conf:
            xml = MRF_CONFIG_TEMPLATE
            match = re.findall(r'(\d{4}-\d{2,}-\d{2,})|(\d{4}-\d{2,})', str(filename))
            if len(match) > 0:
                for m in match[0]:
                    if m != '':
                        datestring = m
                date = datetime.strptime(datestring, config.date_match)
            else:
                match = re.findall(r'(\d{4,}[_-])', str(filename))
                print('\nDetected datestring: ' + match[0].replace('-', ''))
                try:
                    date = datetime.strptime(match[0].replace('_', '').replace('-', ''), config.date_match)
                except ValueError as v:
                    if len(v.args) > 0 and v.args[0].startswith('unconverted data remains: '):
                        extra = v.args[0].split('unconverted data remains: ')[1]
                        print('Extra data string found: ' + extra)
                        date = datetime.strptime(match[0].replace('_', '').replace('-', '').replace(extra, ''),
                                                 config.date_match)
                    else:
                        raise
            date_of_data = date.strftime('%Y%m%d')
            print('Detected date: ' + date_of_data)
            time_of_data = date.strftime('%H%M%S')
            if config.time_bands != [''] and '_b' in filename:
                band = int(filename.split('_b')[1].split('_')[0]) - 1
                addtime = config.time_bands[band]
                time_of_data = (date + timedelta(seconds=addtime)).strftime('%H%M%S')
            output_dir = config.output_dir + '/' + layer_name + '/' + str(date.year)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            xml = MRF_CONFIG_TEMPLATE.safe_substitute(date_of_data=date_of_data,
                                                      time_of_data=time_of_data,
                                                      name=layer_name,
                                                      input_file=input_file,
                                                      output_dir=output_dir,
                                                      working_dir=config.working_dir,
                                                      logfile_dir=config.working_dir+'/logs',
                                                      colormap=colormap,
                                                      target_x=config.target_x,
                                                      extents=config.extents,
                                                      empty_tile=empty_tile,
                                                      reproject=config.reproject,
                                                      mrf_suffix=config.mrf_suffix)
            conf.write(xml)
        mrfgen_command_list = ['mrfgen', '-c', mrf_config]
        try:
            process = subprocess.Popen(mrfgen_command_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            process.wait()
            for output in process.stdout:
                print(output.decode())
            for error in process.stderr:
                print(error.decode())
            if process.returncode == 0:  # delete if there are no errors
                print('Deleting file ' + input_file)
                os.remove(input_file)
                outfile = layer_name + config.mrf_suffix.split('.mrf')[0].replace('%Y%j%H%M%S',date.strftime('%Y%j%H%M%S'))
                mrf_file = outfile + '.mrf'
                data_file = outfile + '.ppg'
                idx_file = outfile + '.idx'
                # upload to s3 if prefix specified
                if config.s3_prefix is not None:
                    try:
                        print('Uploading to ' + config.s3_prefix)
                        s3_prefix = config.s3_prefix + '/' + layer_name + '/' + str(date.year)
                        s3_client = boto3.client('s3')
                        s3_url = urlparse(s3_prefix, allow_fragments=False)
                        s3_path_mrf = os.path.normpath(s3_url.path + '/' + mrf_file).lstrip('/')
                        s3_path_data = os.path.normpath(s3_url.path + '/' + data_file).lstrip('/')
                        s3_path_idx = os.path.normpath(s3_url.path + '/' + idx_file).lstrip('/')
                        print('Uploading ' + s3_path_mrf)
                        mrf_response = s3_client.upload_file(output_dir + '/' + mrf_file,
                                                             s3_url.netloc,
                                                             s3_path_mrf)
                        print(mrf_response)
                        print('Uploading ' + s3_path_data)
                        data_response = s3_client.upload_file(output_dir + '/' + data_file,
                                                              s3_url.netloc,
                                                              s3_path_data)
                        print(data_response)
                        print('Uploading ' + s3_path_idx)
                        data_response = s3_client.upload_file(output_dir + '/' + idx_file,
                                                              s3_url.netloc,
                                                              s3_path_idx)
                        print(data_response)
                        os.remove(output_dir + '/' + mrf_file)
                        os.remove(output_dir + '/' + data_file)
                        if config.idx_dir is None:
                            os.remove(output_dir + '/' + idx_file)
                    except ClientError as ex:
                        print(ex)
                    except NoCredentialsError as ex:
                        print(ex)
                # move idx file if specified
                if config.idx_dir is not None:
                    out_idx_dir = os.path.normpath(config.idx_dir + '/' + layer_name + '/' + str(date.year))
                    if not os.path.exists(out_idx_dir):
                        os.makedirs(out_idx_dir)
                    shutil.move(os.path.normpath(output_dir + '/' + idx_file), out_idx_dir + '/' + idx_file)
                    print('Moved ' + idx_file + ' to ' + out_idx_dir)

        except FileNotFoundError as ex:
            print(ex)
        print('Deleting file ' + mrf_config)
        os.remove(mrf_config)


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
        '--input',
        dest='input_file',
        help='Input file or directory to convert to MRFs',
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

    nc2tiff(args.input_file, args.config, args.process_existing, args.limit, args.create_cog)
