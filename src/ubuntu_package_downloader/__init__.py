import argparse
import sys

from .config import Settings
from .ubuntu_package_downloader import UbuntuPackageDownloader

SUCCESS = 0
ERROR = 1

def main():
    """
    Process command line arguments and call ubuntu_package_downloader function
    """
    # load settings
    settings = Settings()

    parser = argparse.ArgumentParser(
        prog=settings.project.name, description=settings.project.description
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{settings.project.name} {settings.project.version}",
    )
    parser.add_argument("name", type=str, help="Package to download")
    parser.add_argument(
        "-p",
        "--package-version",
        type=str,
        help="Specify the version of the package to download",
        default="latest",
    )
    parser.add_argument(
        "-d",
        "--distribution-series",
        type=str,
        help="The edition of the package to download i.e., 24.04, 23.10, focal, noble, etc.",
        default="24.04",  # default to latest LTS at time of writing
    )
    parser.add_argument(
        "-a",
        "--architecture",
        type=str,
        help="Specify the architecture of the package to download",
        default="amd64",
    )
    parser.add_argument(
        "-w",
        "--with-dependencies",
        action="store_true",
        help="Recursively download dependencies",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=1,
        required=(
            "-w" in sys.argv and "--depth" in sys.argv
        ),  # only required if -w specified, and user specified it, so that default can be used
        help="Set the dependency recursion depth, defaults to 1",
    )
    # parse arguments
    args = parser.parse_args()

    # get UbuntuPackageDownloader instance
    upd = UbuntuPackageDownloader(
        settings.launchpad.consumer_name,
        settings.launchpad.service_root,
        settings.launchpad.version,
        settings.launchpad.distribution,
    )

    # set recursion limit
    upd.recursion_limit = args.depth

    return sys.exit(SUCCESS) if upd.download(
        package_name=args.name,
        package_version=args.package_version,
        distribution_series=args.distribution_series,
        architecture=args.architecture,
        with_dependencies=args.with_dependencies,
    ) else sys.exit(ERROR)
