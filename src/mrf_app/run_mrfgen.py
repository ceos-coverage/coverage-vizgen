#!/usr/bin/env python3
import argparse
import boto3
from datetime import datetime, timedelta
import docker
from pathlib import Path, PurePath
import re
import subprocess
import shutil
from typing import Callable, List, Optional, Tuple
import xml.etree.ElementTree as ET

from mrf_app.data_download import omi_download, hls_download, geoscf_download
from mrf_app.util import copy_empty_tiles, create_layer_archive, upload_files

def find_mrfgen_container(
        ctr_tag: Optional[str] = "") -> docker.models.containers.Container:
    '''
    Find the docker container associated with the running mrfgen image.
    If no specific name is provided, search for the first running container
    called mrfgen* and return that. Should be safe?

    :params ctr_tag: Optionally specify the name of the container directly.
    :return: A docker.Container object for running mrfgen.
    '''
    if ctr_tag == "":
        # Attempt to guess the container name from context...
        # Don't get pwned!
        ctr_pattern = r"mrfgen.*"
    else:
        ctr_pattern = ctr_tag
    client = docker.from_env()
    for ctr in client.containers.list():
        if bool(re.search(ctr_pattern, ctr.name)):
            return ctr
    else:
        raise FileNotFoundError(f"No suitable container named: {ctr_tag} was found." + \
            " Run docker ps and try again.")


def exec_mrfgen_container(
        mrfgen_ctr: docker.models.containers.Container,
        configpath: Path) -> None:
    '''
    Exec in to a running mrfgen container and create a single MRF with parameters from
    the file located at configpath. This function calls a script, run_mrf.sh,
    that cleans the working directories and invokes mrfgen.py within the container.

    :param container: The running mrfgen container from the docker client.
    :param configpath: Path to the .xml file containing inputs to MRFgen.
    :return: None. An MRF and its associated files are created as a side effect.
    '''
    # Convert the config path from a local dir to a directory inside the container
    containerpath = Path("/mrfgen/config") / configpath.name
    # Run the script run_mrf.sh with the provided config
    script_path = "/scripts/run_mrf.sh"
    mrfgen_command = f"{script_path} {containerpath}"
    
    print("Running mrfgen from within the onearth-tools image...")
    mrfgen_ctr.exec_run(
        mrfgen_command,
        detach=True
    )
    for line in mrfgen_ctr.logs(stream=True):
        print(line.decode("utf-8").strip())
    return


def copy_mrf_artifacts(
        workpath: Path,
        bucket: Optional[str] = "") -> None:
    '''
    Copy the mrf files to the archive directory and possibly upload them
    to an S3 bucket, typically the user's dev sandbox bucket.

    :param workpath: Path to the working directory for MRFgen.
    :param bucket: Optionally specify an S3 bucket to upload files.
    :return: None. MRFgen outputs are copied to {workpath}/archive/ and optionally
             uploaded to S3.
    '''
    suffix_whitelist = [".mrf", ".idx", ".lrc", ".ppg", ".ptf", ".pjg", ".pjp"]
    outpath = workpath / "output"
    for outfile in outpath.iterdir():
        if outfile.suffix not in suffix_whitelist:
            print(f"Skipping file: {outfile.name}, extension not in whitelist.")
            continue
        # This is a brittle way of getting the layer name, but will
        # work if the MRF follows the standard naming convention.
        if "-" not in outfile.name:
            raise ValueError(
                f"Output MRF file {outfile.name} does not follow standard " + \
                "naming convention, expected {layer}-YYYYjjjHHMMSS.mrf"
            )
        layer = outfile.name.split("-")[0]
        year = outfile.name.split("-")[1][:4]
        archivepath = create_layer_archive(workpath, layer, year)
        shutil.copy(outfile, archivepath)

    if bucket != "":
        upload_files(archivepath, bucket)
    return


def get_data_type(args: argparse.Namespace) -> Tuple[str, Callable]:
    '''
    Convert the mutually exclusive boolean cli arguments to strings.
    Also specify the method pointer to the data download function that
    should be used for that data type.

    :param args: The argparser namespace from the cli.
    :return: A tuple with the data type as a string and a method pointer to
             the data download function.
    '''
    if args.omi:
        data_type = "omi"
        dl_func = omi_download
    elif args.hls:
        data_type = "hls"
        dl_func = hls_download
    elif args.geos_cf:
        data_type = "geos_cf"
        dl_func = geoscf_download
    return (data_type, dl_func)


def parse_config(cfg: Path) -> Tuple[str, List[int]]:
    '''
    Read a config.xml file used for generating an MRF and
    parse out relevant information for query data access APIs
    such as VEDA.

    :param cfg: Path to the config.xml file.
    :return: A tuple containing the date string and a list of ints
             corresponding to the target extents (bbox).
    '''
    # Read the config xml file and get only the needed tags
    root = ET.parse(cfg).getroot()
    dt_raw = root.find("date_of_data").text
    bbox_raw = root.find("target_extents").text

    # Format the date_of_data as a / separated date string with
    # today and tomorrow's (dtmrw) date
    fstr = "%Y-%m-%dT%H:%M:%SZ"
    dt_year = dt_raw[:4]
    dt_month = dt_raw[4:6]
    dt_day = dt_raw[6:]
    dt_start = datetime(int(dt_year), int(dt_month), int(dt_day))
    dt_end = dt_start + timedelta(days=1)
    dt_range = f"{dt_start.strftime(fstr)}/{dt_end.strftime(fstr)}"

    # Format the target_extents as a list of ints
    bbox = list(map(int, bbox_raw.split(",")))

    return (dt_range, bbox)


def detect_image_tag(tag_arg: str) -> Tuple[str, str]:
    '''
    Detects the tag used for the onearth-tools image built from
    build-mrfgen. 

    :param tag_arg: tag specified for the image from the cli. May be None.
    :return: A tuple with a verified image tag name and its ID or two empty
             strings if no image is found.
    '''
    image_tuple = ("", "")
    client = docker.from_env()

    # Check the tag argument provided in the cli
    if tag_arg is not None:
        image_tag = tag_arg
        # Let this fail if the user inputs a bad image tag    
        image = client.images.get(image_tag)
        return (image_tag, image.id)
    
    # No argument provided, detect the tag by looking for an image with
    # the mrfgen:* tag signature
    images = client.images.list()
    for im in images:
        tag_list = im.tags
        if tag_list[0].startswith("mrfgen:"):
            image_tag = tag_list[0]
            image_tuple = (image_tag, im.id)
            break

    return image_tuple


def run_mrfgen(args: argparse.Namespace) -> None:
    '''
    Run all data download and mrf generation steps for creating a single MRF.
    Copy the data to the archive when the product is complete.

    :param args: The argparser namespace from the cli.
    :return: None. An MRF comprised of an image product, .mrf, and .idx are copied to
             the archive/ directory in the workdir and can also be found in output/
    '''
    # Convert the argparse namespace to a string the tedious way
    data_type, dl_func = get_data_type(args)
    
    # Check the working directory is valid
    configpath = Path(args.configpath).resolve()
    if not configpath.exists():
        raise FileNotFoundError(f"Input config {args.configpath} does not exist.")
    if configpath.is_dir():
        workpath = configpath.parent
        # Find all .xml config files in the directory. Bad configs will cause the script
        # to choke.
        config_files = list(configpath.glob("*.xml"))
    else:
        # Is a file, workpath will be two levels up
        workpath = configpath.parent.parent
        config_files = [configpath]

    # If there are no empty tiles, copy them at this point. This should be done by build_mrfgen.
    copy_empty_tiles(workpath)

    if not args.no_download:
        # The product is considered a different layer if any parameter
        # other than datetime varies between configs.
        datetimes = list()
        bboxes = list()
        for cfg in config_files:
            d, b = parse_config(cfg)
            datetimes.append(d)
            bboxes.append(b) 
        for dt, bb in zip(datetimes, bboxes):
            dl_func(
                dt,
                bb,
                args.zoom_level,
                workpath
            )
    
    mrfgen_ctr = find_mrfgen_container(args.container_tag)
    print(f"Using {mrfgen_ctr.name} ({mrfgen_ctr.short_id}) container for running mrfgen...")

    '''
    # Detect the image tag, image_id is just used for verification purposes
    image_tag, image_id = detect_image_tag(args.image_tag)
    if image_tag == "":
        print("Unable to find an mrfgen (onearth-tools) image to use for run-mrfgen!")
        print("Run 'docker images' on the command line to check available images. Remember,")
        print("'build-mrfgen' must be run first before this script.")
    else:
        print(f"Using {image_tag} ({image_id}) image for running mrfgen...")
    '''

    for cfg in config_files:
        exec_mrfgen_container(mrfgen_ctr, cfg)
        copy_mrf_artifacts(workpath, args.bucket)
    return


def setup_cli() -> argparse.ArgumentParser:
    '''
    Sets up the CLI with arguments for running mrfgen.

    :return: An argparse.ArgumentParser instance.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "configpath",
        help="Directory containing one or more MRFs to be generated. One will be" + \
             " created for each .xml in the directory. Alternatively, give the full" + \
             " path to only generate an MRF from a specific .xml config. The parent of" + \
             " this directory is assumed to be the mrfgen workdir."
    )
    parser.add_argument(
        "-z",
        "--zoom-level",
        type=int,
        default=3,
        help="Specify the zoom level of the product. This is not specified in the MRF" + \
             "config but rather is a property used when downloading the data."
    )

    # Data type argument group. Also required for data download.
    data_type = parser.add_mutually_exclusive_group(required=True)
    data_type.add_argument(
        "--omi",
        action="store_true",
        help="Create an MRF comprised of data from the OMI NO2 dataset."
    )
    data_type.add_argument(
        "--hls",
        action="store_true",
        help="Create an MRF comprised of data from the HLS dataset."
    )
    data_type.add_argument(
        "--geos-cf",
        action="store_true",
        help="Create an MRF comprised of data from the GEOS-CF netCDF dataset."
    )

    parser.add_argument(
        "-b",
        "--bucket",
        default="",
        help="Specify the S3 bucket to upload your completed MRFs. The layer name and directories" + \
             " are handled automatically."
    )
    #parser.add_argument(
    #    "-l",
    #    "--layer",
    #    help="Manually specify the layer name. This is helpful if your config files do not specify" + \
    #         " the layer name or you need to change them after the fact. MRFs will be renamed."
    #)
    parser.add_argument(
        "-t",
        "--container-tag",
        default="",
        help="Manually specify the container tag to use for mrfgen. This script will attempt to" + \
             " auto-detect the mrfgen-{version} container in your environment."
    )
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Don't download the tiles for the MRF. Only use this option if the tiles have" + \
             " already been downloaded or have been sourced externally."
    )
    return parser


def cli() -> None:
    '''
    Command line interface (CLI) entry point function. Calls run_mrfgen.
    '''
    parser = setup_cli()
    args = parser.parse_args()
    run_mrfgen(args)
    return


if __name__ == '__main__':
    cli()