import argparse
import sys
from pathlib import Path
from uuid import uuid4
from launchpadlib.launchpad import Launchpad
from launchpadlib.uris import service_roots
from pydantic import Field
from loguru import logger
from pydantic_settings import SettingsConfigDict, BaseSettings
from typing import Optional, Annotated
from debian.debfile import DebFile, DebControl
from debian.deb822 import Deb822


# global variable to track recursion depth
dependency_recursion_depth: int = 1


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        pyproject_toml_depth=2,
        pyproject_toml_table_header=("tool", "settings"),
    )
    launchpad_consumer_name: str = Field(frozen=True, default=str(uuid4()))
    launchpad_service_root: str = Field(frozen=True, default="production")
    launchpad_version: str = Field(frozen=True, default="devel")
    launchpad_distribution: str = Field(frozen=True, default="ubuntu")


def main(
    package_name: str,
    package_version: str,
    distribution_series: str,
    architecture: str,
    with_dependencies: bool,
    settings: Settings,
) -> Annotated[
    Optional[list[str]],
    "List of downloaded package filenames or None if not found or none downloaded",
]:
    # login anonymously to launchpad
    msg = (
        f"Logging in to Launchpad as anonymous user {settings.launchpad_consumer_name}"
    )
    logger.info(msg)
    lp = Launchpad.login_anonymously(
        settings.launchpad_consumer_name,
        service_root=service_roots[settings.launchpad_service_root],
        version=settings.launchpad_version,
    )

    # select ubuntu distribution and main archive
    msg = f"Selecting main archive of {settings.launchpad_distribution} distribution"
    logger.info(msg)
    lp_distribution = lp.distributions[settings.launchpad_distribution]
    archive = lp_distribution.main_archive

    # get the binary publishing history for the package
    msg = f"Fetching binary publishing history for {package_name}@{package_version} package"
    logger.info(msg)
    lp_series = lp_distribution.getSeries(name_or_version=distribution_series)
    lp_arch_series = lp_series.getDistroArchSeries(archtag=architecture)
    binary_publishing_histories = archive.getPublishedBinaries(
        exact_match=True,
        version=None if package_version == "latest" else package_version,
        binary_name=package_name,
        order_by_date=True,
        distro_arch_series=lp_arch_series,
    )

    if not binary_publishing_histories:
        msg = f"No binary publishing history found for {package_name} {package_version} in {lp_series.name} {lp_arch_series.architecture_tag}."
        logger.error(msg)
        return None

    # select latest result (though there should be only one with exact_match=True)
    binary_publishing_history = binary_publishing_histories[0]
    binary_build_link = binary_publishing_history.build_link
    try:
        binary_build = lp.load(binary_build_link)
        msg = f"Found binary package {package_name} {lp_arch_series.architecture_tag} version {package_version} in {lp_arch_series.display_name} build."
        logger.info(msg)
    except ValueError:
        msg = f"Could not load binary build link {binary_build_link}."
        logger.error(msg)
        return None

    msg = f"Downloading package {package_name} version {package_version} for {lp_series.name} {binary_build.arch_tag}."
    logger.info(msg)

    # a package may have multiple binary files
    downloaded_binary_build_filenames = []
    for binary_build_url in binary_publishing_history.binaryFileUrls():
        # get the filename from the url
        uri = Path(binary_build_url)
        binary_build_filename = Path(uri.name)
        msg = f"Downloading {binary_build_url} to {binary_build_filename}."
        logger.info(msg)

        # skip if file already exists
        if binary_build_filename.exists():
            msg = f"{binary_build_filename} already exists. Skipping re-download."
            logger.warning(msg)
        else:
            # write the binary file to disk
            binary_build_filename.write_bytes(lp._browser.get(binary_build_url))
            msg = (
                f"Sucessfully downloaded {binary_build_url} to {binary_build_filename}."
            )
            logger.info(msg)

        # append to list of downloaded filenames (even if skipped)
        downloaded_binary_build_filenames.append(str(binary_build_filename))

    # parse the deb file to get its dependencies
    # in order to determine dependencies, the file must be downloaded first, meanting this is a serial process
    dependencies_list = []
    for binary_build_filename in downloaded_binary_build_filenames:
        # load the debian file binary (this is muiltiple tar.gz's tarred together)
        deb_file = DebFile(binary_build_filename)

        # get the control archive from the deb file
        control_archive: DebControl = deb_file.control

        # read the control file data
        control_file_data = control_archive.get_content("control")

        # parse the control file data
        control_dict = Deb822(control_file_data)

        # get the dependencies string, this is a ill formatted sentence of the form 'libc6 (>= 2.34), libx11-6, libxmu6 (>= 2:1.1.3)'
        dependencies_str = control_dict.get("Depends", "")
        if not dependencies_str:
            continue

        # extract dependency names (without version constraints), latest will always be used
        logger.debug(f"Raw dependencies string: {dependencies_str}")
        dependency_list = [
            dependency.strip() for dependency in dependencies_str.split(",")
        ]
        dependencies_list = [
            dependency.split(" ")[0].strip() for dependency in dependency_list
        ]

    # check wherether to download dependencies
    if not with_dependencies:
        msg = f"Dependency download not specified for {package_name}. Note that dependencies are: {dependencies_list}."
        logger.info(msg)
    else:
        # check whether maximum recursion depth reached
        global dependency_recursion_depth
        if 0 >= dependency_recursion_depth:
            msg = f"Maximum dependency recursion depth reached. Not downloading dependencies of {package_name}."
            logger.warning(msg)
        else:
            # recursively download each dependency
            for dependency in dependencies_list:
                msg = f"Recursively downloading dependency {dependency} of {package_name}."
                logger.info(msg)

                # decrease recursion depth
                dependency_recursion_depth -= 1

                # call main function to download dependency
                downloaded_dependency_binary_build_filenames = main(
                    dependency,
                    "latest",
                    distribution_series,
                    architecture,
                    True,
                    settings,
                )

                # append any downloaded dependency filenames to main list
                downloaded_binary_build_filenames.extend(
                    downloaded_dependency_binary_build_filenames
                ) if downloaded_dependency_binary_build_filenames is not None else None

                # restore recursion depth
                dependency_recursion_depth += 1

    # return list of downloaded binary build filenames or None
    return (
        downloaded_binary_build_filenames if downloaded_binary_build_filenames else None
    )


if __name__ == "__main__":
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
        help="The edition of the package to download",
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
        default=dependency_recursion_depth,
        required=(
            "-w" in sys.argv and "--depth" in sys.argv
        ),  # only required if -w specified, and user specified it, so that default can be used
        help="Set the dependency recursion depth",
    )
    # parse arguments
    args = parser.parse_args()

    # load settings
    settings = Settings()

    # set global recursion depth
    dependency_recursion_depth = args.depth

    # call main function
    main(
        args.name,
        args.package_version,
        args.distribution_series,
        args.architecture,
        args.with_dependencies,
        settings,
    )
