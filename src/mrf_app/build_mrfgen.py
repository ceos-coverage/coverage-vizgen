#!/usr/bin/env python3
import argparse
import docker
from pathlib import Path, PurePath
import platform
import subprocess
from mrf_app.util import copy_empty_tiles


def prep_working_directories(
        workdir: Path) -> None:
    '''
    Given a top level directory, create a set of working directories inside
    that are used by this script to place intermediates and outputs.

    :param workdir: Top-level directory (as a string) to use for intermediates and outputs.
    :return: None. 9 empty directories are created as a side effect.
    '''
    workdir.mkdir(
        parents=True,
        exist_ok=True
    )
    required_dirs = [
        "archive",
        "cache",
        "colormap",
        "config",
        "data",
        "empty",
        "log",
        "output",
        "work"
    ]
    for d in required_dirs:
        new_dir = workdir / d
        new_dir.mkdir(exist_ok=True)

    # Copy empty tiles to empty/ directory in the working directory.
    copy_empty_tiles(workdir)

    return


def clone_onearth_repo(
        onearth_path: Path) -> Path:
    '''
    Clone the onearth repo to the given path, using the current working
    directory as a default if not specified.

    :param onearth_path: Path to the onearth source code.
    :return: Path to the onearth source code, newly cloned if it was not found.
    '''
    # Downloads the main branch of the repository by default
    repo_url = "https://github.com/nasa-gibs/onearth.git"

    if not onearth_path.exists():
        onearth_path = Path.cwd() / "onearth"
    else:
        if onearth_path.name != "onearth":
            onearth_path = onearth_path / "onearth"

    if not onearth_path.exists():
        try:
            subprocess.run(["git", "clone", repo_url, str(onearth_path)], check=True)
            print(f"Cloned 'onearth' repository into {str(onearth_path)}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to clone 'onearth' repository: {e}")
    else:
        print(f"Found an onearth installation at {onearth_path}")
    return onearth_path


def get_onearth_version(onearth_path: Path) -> str:
    '''
    Source the version.sh script in the onearth repo's root directory to
    get the version number of onearth for this build.

    :param onearth_path: Path to the onearth source code.
    :return: Version number of onearth as a string.
    '''
    version_script = onearth_path / "version.sh"
    command = f"source {str(version_script)} && echo $ONEARTH_VERSION"
    try:
        result = subprocess.run(
            ['bash', '-c', command],
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        onearth_version = result.stdout.strip()
        return onearth_version
    except subprocess.CalledProcessError as e:
        print(f"Failed to source 'version.sh' in onearth repository: {e}")
        return ""
    

def build_onearth_tools_native(
        onearth_path: Path,
        nocache: bool) -> str:
    '''
    Builds the onearth-tools docker image based on the onearth source
    specified in the onearth_path argument. Uses native Python. The output
    of this is clunky, so this function is deprecated.

    :param onearth_path: Path to the onearth source code.
    :param nocache: Pass the --nocache argument to docker.
    :return: A string containing the new image tag. An onearth-tools image will
             be built as a side effect.
    '''
    client = docker.APIClient(base_url="unix://var/run/docker.sock")

    tools_dockerfile = onearth_path / "docker/tools/Dockerfile"

    # Define build arguments
    onearth_version = get_onearth_version(onearth_path)
    build_args = {
        "ONEARTH_VERSION": onearth_version
    }
    # TO DO: determine if this should only be done on MacOS or if it can be
    # the default across all host architectures.
    platform_str = "linux/amd64" # Image is x86_64

    # Build the image
    print(f"Building onearth-tools image for version: {onearth_version}")
    image_id = ""
    with open(tools_dockerfile, "rb") as docker_io:
        response = client.build(
            fileobj=docker_io,
            tag=f"mrfgen:{onearth_version}",
            buildargs=build_args,
            platform=platform_str,
            nocache=nocache,
            rm=True,
            decode=True
        )
        for chunk in response:
            if "stream" in chunk:
                print(chunk["stream"].strip())
                if "Successfully built" in chunk["stream"]:
                    image_id = chunk["stream"].split()[-1]
            elif "error" in chunk:
                print(f"Error: {chunk['error']}")
    if image_id != "":
        print(f"Successfully built image with ID: {image_id}")
        return image_id
    else:
        print("Failed to build onearth-tools image.")
        return ""


def build_onearth_tools(
        onearth_path: Path,
        nocache: bool) -> str:
    '''
    Builds the onearth-tools docker image based on the onearth source
    specified in the onearth_path argument. Uses a subprocess.

    :param onearth_path: Path to the onearth source code.
    :param nocache: Pass the --nocache to docker.
    :return: A string containing the new image tag. An onearth-tools image will
             be built as a side effect.
    '''
    '''
    The ideal build command should be like this:
    docker build \
        --no-cache \
        --platform=linux/amd64 \
        --build-arg ONEARTH_VERSION=$ONEARTH_VERSION \
        -f ./docker/tools/Dockerfile \
        -t mrf-app \
        .
    '''
    command_args = ["docker", "build"]

    # The no-cache should come first, it is an optional flag.
    if nocache:
        command_args.append(
            "--no-cache"
        )

    # Only specify the platform argument on arm systems.
    host_arch = platform.machine().lower()
    if host_arch == "arm64" or host_arch == "aarch64":
        command_args.append(
            "--platform=linux/amd64"
        )

    # Specify a build argument with the onearth version.
    onearth_version = get_onearth_version(onearth_path)
    command_args.extend(
        ["--build-arg", f"ONEARTH_VERSION={onearth_version}"]
    )

    # Specify the onearth tools dockerfile
    tools_dockerfile = onearth_path / "docker/tools/Dockerfile"
    command_args.extend(
        ["-f", f"{str(tools_dockerfile)}"]
    )

    # Add a tag
    image_tag = f"mrfgen:{onearth_version}"
    command_args.extend(
        ["-t", image_tag]
    )

    command_args.append(str(onearth_path))

    # Build the image
    print(f"Building onearth-tools image for version: {onearth_version}")
    print(f"Command:\n\n{' '.join(command_args)}")
    try:
        subprocess.run(command_args, check=True)
        print("Successfully built onearth-tools image.")
        return image_tag
    except subprocess.CalledProcessError as e:
        print(f"Failed to build onearth-tools image: {e}")
        return ""


def run_container(
        workpath: Path,
        image_tag: str) -> None:
    '''
    Run the container indefinitely after building. mrfgen commands will be sent
    via exec, thus using the same container ID. This handles mounting the volumes
    ahead of time so that no input is required to run-mrfgen.

    :param workpath: Path to the directories used by mrfgen.
    :param image_tag: A string specifying the image name to start the container.
    :return: None. A new container instance will be started.
    '''
    client = docker.from_env()
    volumes = {
        str(workpath): {"bind": "/mrfgen", "mode": "rw"},
        str(PurePath(__file__).parent): {"bind": "/scripts", "mode": "rw"}
    }
    restarts = {
        "Name": "on-failure",
        "MaximumRetryCount": 5
    }
    # Idle the container until mrfgen is called via exec
    ctr_tag = f"mrfgen-{image_tag.split(':')[1]}"
    container = client.containers.run(
        image_tag, 
        "tail -f /dev/null",
        name=ctr_tag,
        volumes=volumes,
        restart_policy=restarts,
        detach=True
    )
    print(f"A new container called {ctr_tag} is now running and ready to use mrfgen.")
    return


def build_mrfgen(args: argparse.Namespace) -> None:
    '''
    Run all build and setup steps for creating the standalone mrfgen app.

    :param args: The argparser namespace from the cli.
    :return: None. An onearth-tools image is built and working directories are
             created as side effects.
    '''
    workdir = Path(args.workdir).resolve()
    prep_working_directories(workdir)
    path_arg = Path.cwd()
    if args.onearth_path is not None:
        path_arg = Path(args.onearth_path).resolve()    
    onearth_path = clone_onearth_repo(path_arg)
    #image_tag = build_onearth_tools(onearth_path, args.nocache)
    image_tag = "mrfgen:2.7.9"
    run_container(workdir, image_tag)
    return


def setup_cli() -> argparse.ArgumentParser:
    '''
    Sets up the CLI with arguments for building mrfgen.

    :return: An argparse.ArgumentParser instance.
    '''
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-w",
        "--workdir",
        default=Path.cwd(),
        help="Working directory for intermediary and output products."
    )
    parser.add_argument(
        "--onearth-path",
        help="Path to an existing clone of the onearth repository. This script will clone a copy if none exists locally."
    )
    parser.add_argument(
        "--nocache",
        action="store_true",
        help="Do not use the cached version of the image. Rebuild the image from scratch.")
    return parser


def cli() -> None:
    '''
    Command line interface (CLI) entry point function. Calls build_mrfgen.
    '''
    parser = setup_cli()
    args = parser.parse_args()
    build_mrfgen(args)
    return


if __name__ == '__main__':
    cli()
