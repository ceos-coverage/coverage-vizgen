
import boto3
from pathlib import Path, PurePath
import shutil
from typing import Optional


def copy_empty_tiles(
        workdir: Path) -> None:
    # Copy empty tiles to empty/ directory in the working directory.
    script_dir = PurePath(__file__).parent
    empty_tile_dir = Path(script_dir.parent.parent.joinpath("resources/empty_tiles"))
    # All files in the empty tiles directory
    empty_tiles = list(empty_tile_dir.glob("*"))
    # Copy the images to the empty directory in workdir
    for et in empty_tiles:
        shutil.copy(et, str(workdir.joinpath("empty/")))
    return

def create_layer_archive(
        workpath: Path,
        layer: str,
        year: str) -> Path:
    # Each layer will also have a year directory within it, but those
    # are created in copy_mrf_artifacts
    layerpath = workpath / "archive" / layer / year
    layerpath.mkdir(
        exist_ok=True,
        parents=True
    )
    return layerpath


def get_s3_key(
        filepath: Path,
        proj: Optional[str] = "epsg4326") -> str:
    layerdir = filepath.parents[1].name
    yeardir = filepath.parents[0].name
    return "/".join([proj, layerdir, yeardir, filepath.name])


def upload_files(
        archivepath: Path,
        bucket: str,
        proj: Optional[str] = "epsg4326") -> None:
    s3 = boto3.client("s3")

    for filepath in archivepath.iterdir():
        if filepath.is_file():
            s3_key = get_s3_key(filepath, proj)
            # Upload the file to the specified S3 bucket
            s3.upload_file(
                Filename=str(filepath),
                Bucket=bucket,
                Key=s3_key
            )
            print(f"Uploaded {filepath} to s3://{bucket}/{s3_key}")
    return
