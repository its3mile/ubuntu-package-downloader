from pathlib import Path
from launchpadlib.launchpad import Launchpad
from launchpadlib.uris import service_roots
from loguru import logger
from typing import Optional, Annotated, Self
from debian.debfile import DebFile, DebControl
from debian.deb822 import Deb822
from functools import reduce
import operator


class UbuntuPackageDownloader:
    def __init__(
        self,
        launchpad_consumer_name: str,
        launchpad_service_root: str,
        launchpad_version: str,
        launchpad_distribution: str,
    ) -> Self:
        self._lp_consumer_name = launchpad_consumer_name
        self._lp_service_root = launchpad_service_root
        self._lp_version = launchpad_version
        self._lp_distribution = launchpad_distribution
        self.lp = self._login_launchpad(
            self._lp_consumer_name, self._lp_service_root, self._lp_version
        )
        self.distribution = self._configure_distribution(self._lp_distribution)
        self.archive = self._configure_archive()
        self.__recursion_limit = 1

    @property
    def recursion_limit(self) -> int:
        """Get maximum recursion depth for dependency downloading"""
        return self.__recursion_limit

    @recursion_limit.setter
    def recursion_limit(self, depth: int):
        """Set maximum recursion depth for dependency downloading"""
        if depth < 0:
            raise ValueError("Recursion depth cannot be negative")
        self.__recursion_limit = depth

    def _login_launchpad(
        self, lp_consumer_name: str, lp_service_root: str, lp_version: str
    ) -> Launchpad:
        """Login anonymously to launchpad"""

        msg = f"Logging in to Launchpad as anonymous user {lp_consumer_name}"
        logger.debug(msg)
        return Launchpad.login_anonymously(
            lp_consumer_name,
            service_root=service_roots[lp_service_root],
            version=lp_version,
        )

    def _configure_distribution(
        self,
        lp_distribution: str,
    ):
        """
        Select ubuntu distribution
        Requires Launchpad API class to be set.
        """

        msg = f"Selecting {lp_distribution} distribution"
        logger.debug(msg)
        return self.lp.distributions[lp_distribution]

    def _configure_archive(self):
        """Select main archive"""

        msg = f"Selecting main archive"
        logger.debug(msg)
        return self.distribution.main_archive

    def identify_package_dependencies(self, debian_binary: Path) -> list[str]:
        """Parse debian binary file to extract dependencies"""

        if not debian_binary.exists():
            msg = f"Debian binary file {debian_binary} does not exist"
            logger.error(msg)
            return []

        # load the debian file binary (this is muiltiple tar.gz's tarred together)
        deb_file = DebFile(debian_binary)

        # get the control archive from the deb file
        control_archive: DebControl = deb_file.control

        # read the control file data
        control_file_data = control_archive.get_content("control")

        # parse the control file data
        control_dict = Deb822(control_file_data)

        # get the dependencies string
        # this is a ill formatted sentence of the form 'libc6 (>= 2.34), libx11-6, libxmu6 (>= 2:1.1.3)'
        # additionally this field is optional https://www.debian.org/doc/debian-policy/ch-relationships.html#s-binarydeps
        dependencies_str = control_dict.get("Depends", "")
        logger.debug(f"Raw dependencies string: {dependencies_str}")

        # extract dependency names (without version constraints)
        dependency_list = [
            dependency.strip() for dependency in dependencies_str.split(",")
        ]
        dependencies_list = [
            dependency.split(" ")[0].strip() for dependency in dependency_list
        ]

        return dependencies_list

    def download_package_binary(self, url: str) -> Path:
        """Download binary file from URL"""

        binary_filename = Path(Path(url).name)
        msg = f"Downloading {url} to {binary_filename}."
        logger.debug(msg)

        if binary_filename.exists():
            msg = f"{binary_filename} already exists. Skipping re-download."
            logger.warning(msg)
        else:
            binary_filename.write_bytes(self.lp._browser.get(url))
            msg = f"Sucessfully downloaded {url} to {binary_filename}."
            logger.debug(msg)

        return binary_filename

    def download(
        self,
        package_name: str,
        package_version: str,
        distribution_series: str,
        architecture: str,
        with_dependencies: bool,
    ) -> Annotated[
        Optional[list[str]],
        "List of downloaded package filenames or None if not found or none downloaded",
    ]:
        # get the binary publishing history for the package
        msg = f"Fetching binary publishing history for {package_name}@{package_version} package"
        logger.debug(msg)
        lp_series = self.distribution.getSeries(name_or_version=distribution_series)
        lp_arch_series = lp_series.getDistroArchSeries(archtag=architecture)
        binary_publishing_histories = self.archive.getPublishedBinaries(
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
            binary_build = self.lp.load(binary_build_link)
            msg = f"Found binary package {package_name} {lp_arch_series.architecture_tag} version {package_version} in {lp_arch_series.display_name} build."
            logger.debug(msg)
        except ValueError:
            msg = f"Could not load binary build link {binary_build_link}."
            logger.error(msg)
            return None

        # download package binary from their urls
        # a package may have multiple binary files
        msg = f"Downloading package {package_name} version {package_version} for {lp_series.name} {binary_build.arch_tag}."
        logger.debug(msg)
        downloaded_binary_build_filenames = [
            self.download_package_binary(package_binary_url)
            for package_binary_url in binary_publishing_history.binaryFileUrls()
        ]

        # parse the deb file to get its dependencies
        # in order to determine dependencies, the file must be downloaded first, meanting this is a serial process
        dependencies = [
            self.identify_package_dependencies(d)
            for d in downloaded_binary_build_filenames
        ]
        dependencies = reduce(operator.concat, dependencies)
        dependencies = set(dependencies)

        # check whether to download dependencies
        if with_dependencies:
            # check whether maximum recursion depth reached
            if 0 >= self.__recursion_limit:
                msg = f"Maximum dependency recursion depth reached. Not downloading dependencies of {package_name}."
                logger.debug(msg)
            else:
                # recursively download each dependency
                for dependency in dependencies:
                    msg = f"Recursively downloading dependency {dependency} of {package_name}."
                    logger.debug(msg)

                    # decrease recursion depth
                    self.__recursion_limit -= 1

                    # call main function to download dependency
                    downloaded_dependency_binary_build_filenames = self.download(
                        dependency,
                        "latest",
                        distribution_series,
                        architecture,
                        True,
                    )

                    # append any downloaded dependency filenames to main list
                    downloaded_binary_build_filenames.extend(
                        downloaded_dependency_binary_build_filenames
                    ) if downloaded_dependency_binary_build_filenames is not None else None

                    # restore recursion depth
                    self.__recursion_limit += 1

        # return list of downloaded binary build filenames or None
        return (
            downloaded_binary_build_filenames
            if downloaded_binary_build_filenames
            else None
        )
