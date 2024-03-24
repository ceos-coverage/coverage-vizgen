
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import List

class VedaArgs:

    '''
    Struct containing endpoint information for accessing
    the VEDA API and fulfilling a data download request.
    '''
    # Defaults
    server: str = "https://staging-raster.delta-backend.com"
    data_type: str = "omi"
    collection_value: List[str] = ["OMI_trno2-COG"]
    asset_string: str = "assets=cog_default"
    #rescale: str = "rescale=0,3000000000000000"
    #colormap_name: str = "colormap_name=reds"
    # Format is tif by default, return_mask=False makes it so that
    # the file is 1-banded for compatibility with mrfgen.
    return_mask: bool = "return_mask=false"
    formats: str = "format=tif"
    # User or API-submitted values
    datetime: str = ""
    data_path: Path = Path.cwd()
    bbox: List[int] = []
    zoom_level: int = 0
    search_id: str = ""


def get_date_str(
        dt_str: str) -> str:
    '''
    Take the input datetime range string query used in the VEDA API call
    and convert it into a directory name where data will be stored for
    the mrf generation.

    Converts:
    YYYY-mm-ddTHH:MM:SSZ/YYYY-mm-ddTHH:MM:SSZ -> YYYYmmdd

    :param dt_str: The datetime string used in the VEDA API query
    :return: 
    '''
    # Take the start datetime, which is / separated from the end dt
    first_dt = dt_str.split("/")[0]
    # Date is to the left of T in the string
    date = first_dt.split("T")[0]
    # Remove dashes from date string
    return date.replace("-", "")


def get_veda_search_id(
        veda_args: VedaArgs) -> str:
    '''
    Get the search id from the VEDA API by posting a mosaic register
    request to the server. This search id is used to download tiles
    from the service.

    :param veda_args: A VedaArgs struct with the api endpoint information
        populated with the correct information.
    :return: A string containing the search ID. Put into the VedaArgs instance.
    '''
    search_json = {
        "collections": veda_args.collection_value,
        "bbox": veda_args.bbox,
        "datetime": veda_args.datetime,
        "filter-lang": "cql-json",
        "replace": veda_args.asset_string
    }

    response = requests.post(
        f"{veda_args.server}/mosaic/register",
        json=search_json,
    ).json()

    print(json.dumps(response, indent=2))

    return response.get("searchid")


def download_veda_tile(
        veda_args: VedaArgs,
        tilex: int,
        tiley: int,
        work_dir: str) -> None:
    # Send a REST query to get the tile with the specified parameters
    tile_url = veda_args.server + \
               "/mosaic/" + \
               veda_args.search_id + \
               "/tiles/WGS1984Quad/" + \
               str(veda_args.zoom_level) + "/" + \
               f"{tilex}/{tiley}" + \
               f"?{veda_args.asset_string}" + \
               f"&{veda_args.formats}" + \
               f"&{veda_args.return_mask}" # + \
               #f"&{veda_args.rescale}" + \
               #f"&{veda_args.colormap_name}"
    session = requests.Session()
    retry = Retry(connect=3, backoff_factor=0.5)
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    response = session.get(tile_url)
    if response.status_code == 200:
        with open(f"{veda_args.data_path}/x{tilex}y{tiley}.tif", "wb") as file:
            file.write(response.content)
        print(f"Downloaded x{tilex}y{tiley}.tif")
    else:
        print(f"Failed to download tile {tilex}, {tiley}, Response: {response.status_code}, {response.content}")
    return
    

def veda_download(
        veda_args: VedaArgs,
        work_dir: str) -> None:
    veda_args.search_id = get_veda_search_id(veda_args)
    
    tilex_range = 2**(veda_args.zoom_level+1)
    tiley_range = 2**(veda_args.zoom_level)

    # Download tiles at MAX SPEED, 10 at a time!
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for tilex in range(tilex_range):
            for tiley in range(tiley_range):
                futures.append(
                    executor.submit(
                        download_veda_tile,
                        veda_args,
                        tilex,
                        tiley,
                        work_dir
                    )
                )

        for future in as_completed(futures):
            future.result() # Handle results or failures here
    return


def omi_download(
        datetime: str,
        bbox: List[int],
        zoom_level: int,
        work_dir: str) -> None:
    veda_args = VedaArgs()
    veda_args.datetime = datetime
    veda_args.bbox = bbox

    # Determine the path where the tiles will be downloaded
    date_str = get_date_str(datetime)
    veda_args.data_path = Path(
        f"{work_dir}/data/{veda_args.data_type}/{date_str}"
    ).resolve()
    
    # Check that the path we are trying to download data to is not a file.
    # If the path does not exist, make a new directory.
    if veda_args.data_path.exists() and veda_args.data_path.is_file():
        raise NotADirectoryError(f"Trying to download data to {veda_args.data_path} but is a file.")
    veda_args.data_path.mkdir(exist_ok=True, parents=True)
    
    # Based on my understanding of exponentials, 
    # this value should not be allowed to be too large
    if zoom_level <= 0 or zoom_level >= 8:
        raise ValueError(f"Zoom level is out of acceptable range: {zoom_level}")
    veda_args.zoom_level = zoom_level
    veda_download(veda_args, work_dir)
    return


def hls_download():
    raise NotImplementedError


def geoscf_download():
    # Find data here: https://portal.nccs.nasa.gov/datashare/gmao/geos-cf/v1/
    raise NotImplementedError