# Ubuntu Package Downloader

## Overview

Ubuntu Package Downloader is a small CLI utility to fetch Debian package binaries directly from Launchpad using their official SDK/API.

It can download package .deb files and optionally recursively fetch their package dependencies from the selected Ubuntu archive.

This is useful if working in on a ubuntu host in a non-internet connected environment. 

## Features

- Download published binary .deb files for a given package/version/series/arch.
- Optionally resolve and recursively download package dependencies.
- Configurable recursion depth for dependency traversal.
- Uses Launchpad APIs via launchpadlib.

## Usage

Simply specify the package to download:

```
ubuntu-package-downloader xclip
```

This will download the latest version of the xclip (amd64) debian (.deb) package from the Ubuntu main archive, for series 24.04 (noble), to the current working directory.

To download a package and its immediate dependencies:

```
ubuntu-package-downloader xclip -w
```

To download a package, with its dependencies, and the dependencies dependencies:

```
ubuntu-package-downloader xclip -w --depth 2
```

You can see where this is going...

Specific package versions, architectures, series, and whether the packages dependencies should be downloaded can also be specified. for this see the tool help:

```
ubuntu-package-downloader --help
```

## Requirements

- Python >= 3.13 (see [pyproject.toml](pyproject.toml) for declared runtime and dependencies).
- This project aims to keep a minimal dependency set. Dependencies are listed in [pyproject.toml](pyproject.toml).

## Install (developer)

This project uses `uv` to manage the installation. 

Simply running `uv sync` will configure the project for development. 

Debugging is as simple as using the provided VSCode launch configuration.

Installing it as a package for local testing is as simple as running `uv tool install .` or `uv tool install . -e`. where it can then be executed simply by its name `ubuntu-package-downloader`, if the `uv` executable tool directory is on the 'PATH', hint `uv tool update-shell`.

Uninstall the local package is as simple as running `uv tool uninstall ubuntu-package-downloader`.

# Credit

This project is essentially a refactor of https://github.com/canonical/ubuntu-package-download, canonical's first party tool. Credit to Canonical and authors. This tool extends the same license.

So why does this tool exist? 

While the core functionality of downloading debian packages directly from launchpad remains the same, the extended feature set differs, notably:
 - This tool allows for downloading of the latest version, without an explicit need to find it manually from some other source e.g., https://packages.ubuntu.com
 - This tool allows for the download of dependencies of the package as well, so you aren't lost in an endless loop of trying to install packages with missing dependencies.
 - Canonical's tool provides a fallback mechanism, to download versions from older suites.

 The feature set of this tool better suites the use case of downloading packages for use in non-internet connected environments, where it is important for packages to always be up to date, in support of rapid patching.
