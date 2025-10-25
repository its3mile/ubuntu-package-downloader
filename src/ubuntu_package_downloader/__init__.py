import argparse
import sys

from .config import Settings
from .ubuntu_package_downloader import UbuntuPackageDownloader


def main():
    """
    Process command line arguments and call ubuntu_package_downloader function
    """
    parser = argparse.ArgumentParser(
        prog="ubuntu-package-downloader", description="Download Ubuntu packages easily"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="ubuntu-package-downloader 1.0.0",  # todo: make dynamic
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
        help="Specify the architecutre of the package to download",
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
        help="Set the dependency recursion depth",
    )
    # parse arguments
    args = parser.parse_args()

    # load settings
    settings = Settings()

    # get UbuntuPackageDownloader instance
    upd = UbuntuPackageDownloader(
        settings.launchpad_consumer_name,
        settings.launchpad_service_root,
        settings.launchpad_version,
        settings.launchpad_distribution,
    )

    # set recursion limit
    upd.recursion_limit = args.depth

    return upd.download(
        package_name=args.name,
        package_version=args.package_version,
        distribution_series=args.distribution_series,
        architecture=args.architecture,
        with_dependencies=args.with_dependencies,
    )
