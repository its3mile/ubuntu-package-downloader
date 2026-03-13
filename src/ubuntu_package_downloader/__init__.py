import sys

import click
from loguru import logger

from .config import Settings
from .ubuntu_package_downloader import UbuntuPackageDownloader

SUCCESS = 0
ERROR = 1


@click.command("download")
@click.argument("name")
@click.option(
    "-p",
    "--package-version",
    default="latest",
    help="Specify the version of the package to download",
)
@click.option(
    "-a",
    "--architecture",
    default="amd64",
    help="Specify the architecture of the package to download",
)
@click.option(
    "-d",
    "--distribution-series",
    default="24.04",
    help="The edition of the package to download i.e., 24.04, 23.10, focal, noble, etc.",
)  # default to latest LTS at time of writing
@click.option("--depth", default=0, type=int, help="Recursion depth")
@click.option(
    "--verbose",
    is_flag=True,
    help="Enable verbose logging, which will print more detailed logs to the console",
)
def main(
    name: str,
    package_version: str,
    architecture: str,
    distribution_series: str,
    depth: int,
    verbose: bool,
):
    """
    Ubuntu Package Downloader (UPD) is a command-line utility that allows users to download packages from the Ubuntu repositories, including their dependencies. It provides options to specify the package version, architecture, distribution series, and whether to include dependencies in the download process. The tool is designed to be flexible and user-friendly, making it easier for users to manage their package downloads effectively.
    """
    # load settings
    settings = Settings()

    # replace default logger with new logger with level based on verbose flag
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "INFO")

    # get UbuntuPackageDownloader instance
    upd = UbuntuPackageDownloader(
        settings.launchpad.consumer_name,
        settings.launchpad.service_root,
        settings.launchpad.version,
        settings.launchpad.distribution,
    )

    # set recursion limit
    upd.recursion_limit = depth

    return (
        sys.exit(SUCCESS)
        if upd.download(
            package_name=name,
            package_version=package_version,
            distribution_series=distribution_series,
            architecture=architecture,
            with_dependencies=True if depth > 0 else False,
        )
        else sys.exit(ERROR)
    )
