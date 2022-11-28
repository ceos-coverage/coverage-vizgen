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

import sys
import os
import math
import json
import colorsys
from xml.dom import minidom


HELP_STRING =	("\nHOW TO USE:\n" + 
				"\t./color_map_gen.py [input options] [csv_file] [output options]\n\n" + 
				"\t[csv_file]: the file containing your color,value pairings.\n\n" + 
				"\tinput options:\n" + 
				"\t\t-c: specifies a CSV format (EX. #ffffff,0.0) input file (default)\n" + 
				"\t\t-s: specifies an SLD format input file\n\n" + 
				"\toutput options:\n" + 
				"\t\t-stops: the output file for the color:stop pairs (Ex. [{\"color\": \"#ffffff\", \"stop\": \"0.0000\"}]) (json format)\n" + 
				"\t\t-ranges: the output file for the color:range pairs (Ex. {\"#ffffff\": \"0,1\"}) (json format) \n" + 
				"\t\t-geoserverCSS: the output file for the geoserver style (geoserver css format)\n" +
				"\t\t-geoserverSLD: the output file for the geoserver style (geoserver sld format)\n" +
				"\t\t-LUT: the output file for the GDAL LUT syle\n" +
				"\t\t-gibs: the output file for the GIBS colomap style\n")

MAX_NUM_COLORS = 255
COLOR_VAL_MAP = {}
CSS_COLOR_MAP = []
GEO_SERVER_STYLE = {"css_string":"", "sld_string":"", "lut_string":"", "gibs_string":""}

'''read and parse the csv file defining the colors and stop values'''
def read_csv_file(filename):
	if not os.path.isfile(filename):
		print(HELP_STRING)
		sys.exit()

	parsed_lines = []
	content = []
	with open(filename) as f:
		content = f.readlines()
	parsed_lines = [line.strip("\n").split(",") for line in content]
	return parsed_lines

'''read and parse the sld file defining the colors and stop values'''
def read_sld_file(filename):
	if not os.path.isfile(filename):
		print(HELP_STRING)
		sys.exit()

	parsed_lines = []
	f = open(filename, "r")
	dom = minidom.parseString(f.read())
	f.close()
	color_stops = dom.getElementsByTagName("sld:ColorMapEntry")
	for entry in color_stops:
		color = entry.getAttribute("color")
		opacity = entry.getAttribute("opacity")
		quantity = entry.getAttribute("quantity")
		parsed_lines.append([color, quantity, opacity])
	return parsed_lines


''' "#FFFFFF" -> [255,255,255] '''
def hex_to_RGB(hex):
	# Pass 16 to the integer function for change of base
	return [int(hex[i:i+2], 16) for i in range(1,6,2)]


''' [255,255,255] -> "#FFFFFF" '''
def RGB_to_hex(RGB):
	# Components need to be integers for hex to make sense
	RGB = [int(x) for x in RGB]
	return "#"+"".join(["0{0:x}".format(v) if v < 16 else "{0:x}".format(v) for v in RGB])

'''wrapper function'''
def hsv2rgb(h,s,v):
	return [i * 255 for i in colorsys.hsv_to_rgb(h/360.,s/100.,v/100.)]

'''wrapper function'''
def rgb2hsv(r,g,b):
	h, s, v = colorsys.rgb_to_hsv(r/255., g/255., b/255.)
	return [360 * h, 100 * s, 100 * v]

''' generate a gradient of (n) colors between two
hex colors and store them and their assosiated value
range in the global color-to-value map
based on: http://bsou.io/posts/color-gradients-with-python '''
def generate_gradient_values_hsv(start_hex, finish_hex, start_val, end_val, n):
	# value tracker and increment value for each step
	step_val = start_val
	delta = (end_val - start_val) / n

	# Starting and ending colors in RGB form
	start_rgb = hex_to_RGB(start_hex)
	end_rgb = hex_to_RGB(finish_hex)
	c1 = rgb2hsv(start_rgb[0], start_rgb[1], start_rgb[2])
	c2 = rgb2hsv(end_rgb[0], end_rgb[1], end_rgb[2])

	# determine clockwise and counter-clockwise distance between hues
	distCCW = c1[0] - c2[0] if (c1[0] >= c2[0]) else 1 + c1[0] - c2[0]
	distCW = 1 + c2[0] - c1[0] if (c1[0] >= c2[0]) else c2[0] - c1[0]

	# Calcuate a color at each evenly spaced step from 1 to n
	for step in range(0, n):
		p = step / n

		# interpolate h, s, b
		h = c1[0] + (distCW * p) if (distCW <= distCCW) else c1[0] - (distCCW * p)
		if h < 0:
			h = 1 + h
		if h > 1:
			h = h - 1;
		s = (1 - p) * c1[1] + p * c2[1]
		b = (1 - p) * c1[2] + p * c2[2]

		# normalize back to hex
		rgbColor = hsv2rgb(h,s,b)
		hex_color = RGB_to_hex(rgbColor)

		# format the data values covered
		upper_bound = step_val + delta
		val_range = "{0:10.6f}".format(step_val) + "," + "{0:10.6f}".format(upper_bound)
		step_val += delta
		COLOR_VAL_MAP[hex_color] = val_range

''' generate a gradient of (n) colors between two
hex colors and store them and their assosiated value
range in the global color-to-value map
based on: http://bsou.io/posts/color-gradients-with-python '''
def generate_gradient_values(start_hex, finish_hex, start_val, end_val, n, start_opacity, end_opacity, exclude_end):
	# value tracker
	step_val = start_val

	# increment value (account for including/excluding end)
	delta = (end_val - start_val) / (n - 1)
	if exclude_end: 
		delta = (end_val - start_val) / (n)

	# increment value (account for including/excluding end)
	opacity_val = start_opacity
	opacity_delta = (end_opacity - start_opacity) / (n - 1)
	if exclude_end: 
		opacity_delta = (end_opacity - start_opacity) / (n)	

	# Starting and ending colors in RGB form
	s = hex_to_RGB(start_hex)
	f = hex_to_RGB(finish_hex)

	# Calcuate a color at each evenly spaced value of t from 1 to n
	for t in range(0, n):
		# only use opacity value for first color
		# opacityStr = str(opacity_val)
		# opacity_val += opacity_delta
		# opacity_val = end_opacity if t == n - 2 else opacity_val
		opacityStr = str(start_opacity) if t == 0 else str(end_opacity) if t == n - 1 else "1"

		# Interpolate RGB vector for color at the current value of t
		curr_vector = []
		if exclude_end:
			curr_vector = [ int(s[j] + (float(t)/(n))*(f[j]-s[j])) for j in range(3) ]
		else:
			curr_vector = [ int(s[j] + (float(t)/(n-1))*(f[j]-s[j])) for j in range(3) ]

		hex_color = RGB_to_hex(curr_vector)

		# increment the upper bound and correct for rounding errors
		upper_bound = step_val + delta if step_val + delta <= end_val else end_val
		upper_bound = end_val if t == n - 2 else upper_bound

		val_range = ("{0:10.10f}".format(step_val)).strip() + "," + ("{0:10.10f}".format(upper_bound)).strip()
		step_val += delta
		stop_str = ("{0:10.10f}".format(step_val - delta)).strip()
		COLOR_VAL_MAP[hex_color] = val_range
		CSS_COLOR_MAP.append({"color": hex_color, "stop": stop_str})
		GEO_SERVER_STYLE["css_string"] += "\n\tcolor-map-entry(\"" + hex_color + "\"," + stop_str + "," + opacityStr + ")"
		GEO_SERVER_STYLE["sld_string"] += "\n\t\t\t\t\t<sld:ColorMapEntry color=\"" + hex_color + "\" opacity=\"" + opacityStr + "\" quantity=\"" + stop_str + "\"/>"
		GEO_SERVER_STYLE["lut_string"] += stop_str + " " + ' '.join([str(v) for v in curr_vector]) + " " + ("0" if float(opacityStr) == 0 else "255") + "\n"
		GEO_SERVER_STYLE["gibs_string"] += '\t<ColorMapEntry rgb="' + ','.join([str(v) for v in curr_vector]) + '" transparent="' + ('true' if float(opacityStr) == 0 else 'false') + '" label="' + stop_str +'"/>\n'


''' prep the geoserver style string '''
def start_geoserver_string():
	GEO_SERVER_STYLE["css_string"] = "* {\nraster-channels:auto;\nraster-color-map:"
	GEO_SERVER_STYLE["sld_string"] = ("<?xml version=\"1.0\" encoding=\"UTF-8\"?>" +
										"<sld:UserStyle xmlns=\"http://www.opengis.net/sld\" xmlns:sld=\"http://www.opengis.net/sld\" " +
										"xmlns:ogc=\"http://www.opengis.net/ogc\" xmlns:gml=\"http://www.opengis.net/gml\">\n" +
										"\t<sld:Name>Default Styler</sld:Name>\n" +
										"\t<sld:FeatureTypeStyle>\n" +
										"\t\t<sld:Name>name</sld:Name>\n" +
										"\t\t<sld:Rule>\n" +
										"\t\t\t<sld:RasterSymbolizer>\n" +
										"\t\t\t\t<sld:ColorMap type=\"intervals\">")
	GEO_SERVER_STYLE["gibs_string"] = ('<?xml version="1.0" encoding="UTF-8"?>\n' +
										'<ColorMap xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation=' + 
										'"http://gibs.earthdata.nasa.gov/schemas/ColorMap_v1.0.xsd">\n')
''' complete the geoserver style string '''
def finish_geoserver_string():
	GEO_SERVER_STYLE["css_string"] += ";\nraster-color-map-type:intervals;\n}"
	GEO_SERVER_STYLE["sld_string"] += ("\n\t\t\t\t</sld:ColorMap>\n" +
										"\t\t\t</sld:RasterSymbolizer>\n" +
										"\t\t</sld:Rule>\n" +
										"\t</sld:FeatureTypeStyle>\n" +
										"</sld:UserStyle>\n")
	GEO_SERVER_STYLE["gibs_string"] += ('</ColorMap>')

''' reads a csv of color:values, creates bin stop values
then kicks of the actual 'gradient' generation'''
def run(args):
	# get the filename
	input_file = args[1]
	if input_file in ["-c", "-s"]:
		input_file = args[2]

	# read in the file
	lines = None
	if "-s" in args:
		lines = read_sld_file(input_file)
	else :
		lines = read_csv_file(input_file)

	# sort the lines
	lines = sorted(lines, key=lambda x: float(x[1]))

	# prep the bins
	num_groups = len(lines) - 1
	bins_per_group = int(math.ceil(MAX_NUM_COLORS / num_groups))
	bins_remaining = MAX_NUM_COLORS

	# prep the geoserver style string
	start_geoserver_string()

	for line_index in range(0,num_groups):
		line_a = lines[line_index]
		line_b = lines[line_index + 1]
		start_val = float(line_a[1])
		end_val = float(line_b[1])
		start_color = line_a[0]
		end_color = line_b[0]
		start_opacity = float(line_a[2]) if len(line_a) > 2 else 1
		end_opacity = float(line_b[2]) if len(line_b) > 2 else 1
		num_bins = bins_per_group if bins_remaining >= bins_per_group * 2 else bins_remaining
		bins_remaining -= num_bins
		if(line_index == (num_groups - 1)):
			generate_gradient_values(start_color, end_color, start_val, end_val, num_bins, start_opacity, end_opacity, False)
		else:
			generate_gradient_values(start_color, end_color, start_val, end_val, num_bins, start_opacity, end_opacity, True)

	# finish the geoserver style string
	finish_geoserver_string()

	if "-stops" in args:
		outfile = args[args.index("-stops") + 1]
		f = open(outfile, "w")
		f.write(json.dumps(CSS_COLOR_MAP))
		f.close()

	if "-ranges" in args:
		outfile = args[args.index("-ranges") + 1]
		f = open(outfile, "w")
		f.write(json.dumps(COLOR_VAL_MAP))
		f.close()

	if "-geoserverCSS" in args:
		outfile = args[args.index("-geoserverCSS") + 1]
		f = open(outfile, "w")
		f.write(GEO_SERVER_STYLE["css_string"])
		f.close()

	if "-geoserverSLD" in args:
		outfile = args[args.index("-geoserverSLD") + 1]
		f = open(outfile, "w")
		f.write(GEO_SERVER_STYLE["sld_string"])
		f.close()
		
	if "-LUT" in args:
		outfile = args[args.index("-LUT") + 1]
		f = open(outfile, "w")
		f.write(GEO_SERVER_STYLE["lut_string"])
		f.close()
		
	if "-gibs" in args:
		outfile = args[args.index("-gibs") + 1]
		f = open(outfile, "w")
		f.write(GEO_SERVER_STYLE["gibs_string"])
		f.close()

	print("Complete. Distinct Color Mappings: " + str(len(COLOR_VAL_MAP)))

run(sys.argv)