#!/usr/bin/env python3
import argparse
from pathlib import Path

from mrf_app.util import upload_files

def cli() -> None:
    '''
    Command line interface (CLI) entry point function. Calls run_mrfgen.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "archivepath",
        help="Directory containing generated MRFs. If the directory structure containing the MRFs" + \
             " does not match {layer}/{year}, then the S3 key will be guessed from the file name."
    )
    parser.add_argument(
        "bucket",
        help="S3 bucket to upload the files."
    )
    args = parser.parse_args()
    archivepath = Path(args.archivepath).resolve()
    upload_files(archivepath, args.bucket)

if __name__ == '__main__':
    cli()