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

import argparse
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import cm

# https://matplotlib.org/stable/gallery/color/colormap_reference.html
cmaps = [('Perceptually Uniform Sequential', [
            'viridis', 'plasma', 'inferno', 'magma', 'cividis']),
         ('Sequential', [
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn']),
         ('Sequential (2)', [
            'binary', 'gist_yarg', 'gist_gray', 'gray', 'bone', 'pink',
            'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
            'hot', 'afmhot', 'gist_heat', 'copper']),
         ('Diverging', [
            'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
            'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']),
         ('Cyclic', ['twilight', 'twilight_shifted', 'hsv']),
         ('Qualitative', [
            'Pastel1', 'Pastel2', 'Paired', 'Accent',
            'Dark2', 'Set1', 'Set2', 'Set3',
            'tab10', 'tab20', 'tab20b', 'tab20c']),
         ('Miscellaneous', [
            'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
            'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
            'gist_rainbow', 'rainbow', 'jet', 'turbo', 'nipy_spectral',
            'gist_ncar'])]


class MplColorHelper:

    def __init__(self, cmap_name, start_val, stop_val):
        self.cmap_name = cmap_name
        self.cmap = plt.get_cmap(cmap_name)
        self.norm = mpl.colors.Normalize(vmin=start_val, vmax=stop_val)
        self.scalarMap = cm.ScalarMappable(norm=self.norm, cmap=self.cmap)

    def get_rgb(self, val):
        return self.scalarMap.to_rgba(val)


def colormapgen(output, colormap, min, max, nodata, percent):
    print('min: ' + str(min))
    print('max: ' + str(max))
    range_min = 0
    range_max = 255
    if percent is True:
        min = 0
        max = 100

    xml = open(output + '.xml', 'w+')
    xml.write('''<?xml version="1.0" encoding="UTF-8"?>
<ColorMap xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://gibs.earthdata.nasa.gov/schemas/ColorMap_v1.0.xsd">
    <ColorMapEntry rgb="0,0,0" transparent="true" label="no data"/>
''')

    out = open(output + '.txt', 'w+')
    if not str(nodata) == 'nv':
        if float(nodata) <= min:
            out.write(f'{str(nodata)} 0 0 0 0\n')
    else:
        out.write('nv 0 0 0 0\n')
    mch = MplColorHelper(colormap, min, max)
    for i in range(range_min, range_max):
        val = ((i / (range_max-1)) * (max - min)) + min
        rgba = (mch.scalarMap.to_rgba(val))
        r = round(rgba[0] * 255)
        g = round(rgba[1] * 255)
        b = round(rgba[2] * 255)
        a = round(rgba[3] * 255)
        out_str = ' '.join([str(val) + ('%' if percent else ''), str(r), str(g), str(b), str(a)])
        out.write(out_str + '\n')
        xml_str = f'    <ColorMapEntry rgb="{str(r)},{str(g)},{str(b)}" transparent="false" label="{str(val)+("%" if percent else "")}"/>'
        xml.write(xml_str + '\n')

    if not str(nodata) == 'nv':
        if float(nodata) >= max:
            out.write(f'{str(nodata)} 0 0 0 0\n')
    out.seek(0)
    print(out.read())
    out.close()

    xml.write('</ColorMap>')
    xml.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='This script reads NetCDF files and generates MRF visualizations.')
    parser.add_argument(
        '-c',
        '--colormap',
        default='gist_ncar',
        dest='colormap',
        help='Input directory to convert to GIS data',
        action='store')
    parser.add_argument(
        '--min',
        default=0,
        dest='min',
        help='Minimum value',
        action='store')
    parser.add_argument(
        '--max',
        default=100,
        dest='max',
        help='Maximum value',
        action='store')
    parser.add_argument(
        '-o',
        '--output',
        dest='output',
        default='output',
        help='Output filename without extension',
        action='store')
    parser.add_argument(
        '-n',
        '--nodata',
        dest='nodata',
        default='nv',
        help='nodata value',
        action='store')
    parser.add_argument(
        '-p',
        '--percent',
        dest='percent',
        help='Use percent instead of min/max',
        action='store_true')

    args = parser.parse_args()

    colormapgen(args.output, args.colormap, float(args.min), float(args.max), args.nodata, args.percent)
    print('Created ' + args.output + '.xml and ' + args.output + '.txt')
